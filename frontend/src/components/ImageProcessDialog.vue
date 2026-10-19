<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import {
  defaultParams,
  loadPreset,
  processImage,
  resultWarning,
  savePreset,
  type ImageProcessKind,
  type ProcessParams,
  type ProcessResult,
} from '@/utils/imageProcess'

const props = defineProps({
  modelValue: { type: Boolean, required: true },
  file: { type: Object as () => File | null, default: null },
  kind: { type: String as () => ImageProcessKind, default: 'signature' },
  saving: { type: Boolean, default: false },
})

const emits = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'confirm', payload: { blob: Blob; ext: string; original: boolean }): void
}>()

const isSeal = computed(() => props.kind === 'seal')

const params = ref<ProcessParams>(defaultParams(props.kind))
const useOriginal = ref(false)
const busy = ref(false)
const error = ref('')
const warning = ref<string | null>(null)
const result = ref<ProcessResult | null>(null)
const previewUrl = ref('')
const originalUrl = ref('')

const canSave = computed(() => useOriginal.value || result.value !== null)

let timer: ReturnType<typeof setTimeout> | null = null
let runId = 0

function revoke(url: string) {
  if (url) URL.revokeObjectURL(url)
}

function cleanup() {
  if (timer) {
    clearTimeout(timer)
    timer = null
  }
  runId++
  revoke(previewUrl.value)
  revoke(originalUrl.value)
  previewUrl.value = ''
  originalUrl.value = ''
  result.value = null
  busy.value = false
}

function init() {
  if (!props.file) return
  cleanup()
  params.value = loadPreset(props.kind)
  useOriginal.value = false
  error.value = ''
  warning.value = null
  originalUrl.value = URL.createObjectURL(props.file)
  schedule(0)
}

function schedule(delay = 120) {
  if (timer) clearTimeout(timer)
  timer = setTimeout(run, delay)
}

async function run() {
  const file = props.file
  if (!file) return
  const id = ++runId
  busy.value = true
  // 让“处理中”先渲染出来，再做同步像素运算
  await new Promise((resolve) => setTimeout(resolve, 0))
  try {
    const res = await processImage(file, props.kind, params.value)
    if (id !== runId) return
    result.value = res
    warning.value = resultWarning(res.coverage)
    error.value = ''
    revoke(previewUrl.value)
    previewUrl.value = URL.createObjectURL(res.blob)
  } catch (err) {
    if (id !== runId) return
    result.value = null
    warning.value = null
    error.value = err instanceof Error ? err.message : '图片处理失败'
  } finally {
    if (id === runId) busy.value = false
  }
}

function fileExtension(name: string): string {
  const match = /\.([a-zA-Z0-9]+)$/.exec(name)
  const ext = (match?.[1] ?? 'png').toLowerCase()
  return ['png', 'jpg', 'jpeg', 'webp', 'bmp', 'gif'].includes(ext) ? ext : 'png'
}

function confirm() {
  if (!props.file || !canSave.value) return
  savePreset(props.kind, params.value)
  if (useOriginal.value || !result.value) {
    emits('confirm', { blob: props.file, ext: fileExtension(props.file.name), original: true })
  } else {
    emits('confirm', { blob: result.value.blob, ext: 'png', original: false })
  }
}

function cancel() {
  emits('update:modelValue', false)
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) init()
    else cleanup()
  },
)

watch(
  () => props.file,
  () => {
    if (props.modelValue) init()
  },
)

watch(
  params,
  () => {
    if (!props.modelValue || useOriginal.value) return
    schedule()
  },
  { deep: true },
)

watch(useOriginal, (value) => {
  if (!props.modelValue) return
  if (value) {
    error.value = ''
    warning.value = null
  } else {
    schedule(0)
  }
})

onBeforeUnmount(cleanup)
</script>

<template>
  <v-dialog
    :model-value="modelValue"
    max-width="780"
    @update:model-value="emits('update:modelValue', $event)"
  >
    <v-card rounded="xl" elevation="8" class="ipc-card">
      <v-card-item class="ipc-head">
        <div class="ipc-title-row">
          <v-icon :color="isSeal ? '#c2410c' : '#0f766e'" size="22">
            {{ isSeal ? 'mdi-seal-variant' : 'mdi-draw-pen' }}
          </v-icon>
          <span class="ipc-title">{{ isSeal ? '处理印章图片' : '处理签字图片' }}</span>
          <span class="ipc-file">{{ file?.name }}</span>
        </div>
        <div class="ipc-sub">
          自动去除纸张底色与阴影，输出背景透明的 PNG，可直接拖到页面上使用。
        </div>
      </v-card-item>

      <v-card-text class="ipc-body">
        <div class="ipc-previews">
          <div class="ipc-preview">
            <div class="ipc-preview-label">原图</div>
            <div class="ipc-preview-stage">
              <img v-if="originalUrl" :src="originalUrl" alt="原图" />
            </div>
          </div>
          <div class="ipc-preview">
            <div class="ipc-preview-label">
              处理结果
              <span v-if="result && !useOriginal" class="ipc-meta">
                {{ result.width }} × {{ result.height }}
              </span>
            </div>
            <div class="ipc-preview-stage ipc-preview-stage--checker">
              <img v-if="useOriginal && originalUrl" :src="originalUrl" alt="原图" />
              <img v-else-if="previewUrl" :src="previewUrl" alt="处理结果" />
              <div v-if="busy" class="ipc-busy">处理中…</div>
            </div>
          </div>
        </div>

        <div v-if="error" class="ipc-alert ipc-alert--error">{{ error }}</div>
        <div v-else-if="warning && !useOriginal" class="ipc-alert ipc-alert--warn">{{ warning }}</div>

        <div class="ipc-controls" :class="{ 'ipc-controls--disabled': useOriginal }">
          <div v-if="isSeal" class="ipc-row">
            <span class="ipc-label">印章颜色</span>
            <v-btn-toggle
              v-model="params.mode"
              mandatory
              density="compact"
              class="ipc-toggle"
              :disabled="useOriginal"
            >
              <v-btn value="red" size="small">红色</v-btn>
              <v-btn value="blue" size="small">蓝色</v-btn>
            </v-btn-toggle>
          </div>

          <div class="ipc-row">
            <span class="ipc-label">去背景强度</span>
            <v-slider
              v-model="params.strength"
              :min="0"
              :max="100"
              :step="1"
              density="compact"
              hide-details
              :disabled="useOriginal"
              class="ipc-slider"
            />
            <span class="ipc-value">{{ params.strength }}</span>
          </div>

          <div class="ipc-row">
            <span class="ipc-label">笔画浓淡</span>
            <v-slider
              v-model="params.gamma"
              :min="0.6"
              :max="1.6"
              :step="0.05"
              density="compact"
              hide-details
              :disabled="useOriginal"
              class="ipc-slider"
            />
            <span class="ipc-value">{{ params.gamma.toFixed(2) }}</span>
          </div>

          <div class="ipc-row">
            <span class="ipc-label">质感做旧</span>
            <v-slider
              v-model="params.texture"
              :min="0"
              :max="100"
              :step="1"
              density="compact"
              hide-details
              :disabled="useOriginal"
              class="ipc-slider"
            />
            <span class="ipc-value">{{ params.texture }}</span>
          </div>

          <div v-if="isSeal" class="ipc-row ipc-row--switch">
            <v-switch
              v-model="params.colorize"
              label="统一印色"
              density="compact"
              hide-details
              color="#c2410c"
              :disabled="useOriginal"
            />
            <span class="ipc-hint">关闭后保留原始印泥浓淡</span>
          </div>

          <div class="ipc-note">质感做旧：模拟印泥浓淡不均与边缘毛糙，叠加到 PDF 后更接近真实盖章。</div>
        </div>

        <div class="ipc-row ipc-row--switch ipc-original">
          <v-switch
            v-model="useOriginal"
            label="使用原图（不做处理）"
            density="compact"
            hide-details
            color="#64748b"
          />
        </div>
      </v-card-text>

      <v-card-actions class="ipc-actions">
        <v-spacer />
        <v-btn variant="text" rounded="lg" :disabled="saving" @click="cancel">取消</v-btn>
        <v-btn
          variant="flat"
          rounded="lg"
          color="#4f8cff"
          :disabled="busy || saving || !!error || !canSave"
          :loading="saving"
          @click="confirm"
        >
          {{ useOriginal ? '保存原图' : '保存 PNG' }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<style scoped>
.ipc-card {
  display: flex;
  flex-direction: column;
}

.ipc-head {
  padding: 14px 18px 0;
}

.ipc-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ipc-title {
  font-size: 15px;
  font-weight: 700;
  color: #1e293b;
}

.ipc-file {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 11.5px;
  color: #94a3b8;
}

.ipc-sub {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.5;
  color: #64748b;
}

.ipc-body {
  padding: 12px 18px 4px !important;
}

.ipc-previews {
  display: flex;
  gap: 10px;
}

.ipc-preview {
  flex: 1;
  min-width: 0;
}

.ipc-preview-label {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 2px 5px;
  font-size: 12px;
  font-weight: 600;
  color: #475569;
}

.ipc-meta {
  font-size: 11px;
  font-weight: 500;
  color: #94a3b8;
}

.ipc-preview-stage {
  position: relative;
  height: 220px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: #f8fafc;
  overflow: hidden;
}

.ipc-preview-stage--checker {
  background-color: #fff;
  background-image:
    linear-gradient(45deg, #eef2f7 25%, transparent 25%, transparent 75%, #eef2f7 75%),
    linear-gradient(45deg, #eef2f7 25%, transparent 25%, transparent 75%, #eef2f7 75%);
  background-size: 16px 16px;
  background-position: 0 0, 8px 8px;
}

.ipc-preview-stage img {
  max-width: 92%;
  max-height: 92%;
  object-fit: contain;
}

.ipc-busy {
  position: absolute;
  inset: auto 8px 8px auto;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  color: #fff;
  background: rgba(15, 23, 42, 0.55);
}

.ipc-alert {
  margin-top: 10px;
  padding: 7px 10px;
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.5;
}

.ipc-alert--error {
  color: #b91c1c;
  background: rgba(239, 68, 68, 0.08);
}

.ipc-alert--warn {
  color: #b45309;
  background: rgba(245, 158, 11, 0.1);
}

.ipc-controls {
  margin-top: 12px;
}

.ipc-controls--disabled {
  opacity: 0.45;
}

.ipc-row {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 30px;
}

.ipc-row--switch {
  gap: 8px;
}

.ipc-label {
  flex: 0 0 82px;
  font-size: 12.5px;
  font-weight: 600;
  color: #475569;
}

.ipc-slider {
  flex: 1;
  min-width: 0;
}

.ipc-value {
  flex: 0 0 40px;
  text-align: right;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  color: #64748b;
}

.ipc-hint {
  font-size: 11.5px;
  color: #94a3b8;
}

.ipc-note {
  margin-top: 2px;
  font-size: 11.5px;
  line-height: 1.5;
  color: #94a3b8;
}

.ipc-toggle {
  border-radius: 8px;
  overflow: hidden;
  background: rgba(15, 23, 42, 0.04);
}

.ipc-original {
  margin-top: 6px;
  padding-top: 6px;
  border-top: 1px dashed rgba(15, 23, 42, 0.08);
}

.ipc-actions {
  padding: 10px 18px 14px;
}
</style>
