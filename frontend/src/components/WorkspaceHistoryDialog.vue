<template>
  <v-dialog
    :model-value="modelValue"
    max-width="580"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <v-card rounded="xl" elevation="8" class="revision-dialog">
      <v-card-item>
        <div class="d-flex align-center">
          <v-icon color="primary" size="24" class="mr-2">mdi-history</v-icon>
          <v-card-title class="pa-0">项目历史</v-card-title>
          <v-spacer />
          <v-btn
            icon
            size="small"
            variant="text"
            color="grey-darken-1"
            :loading="loading"
            @click="load"
          >
            <v-icon size="18">mdi-refresh</v-icon>
            <v-tooltip activator="parent" location="top">刷新</v-tooltip>
          </v-btn>
          <v-btn icon size="small" variant="text" color="grey-darken-1" @click="close">
            <v-icon size="18">mdi-close</v-icon>
          </v-btn>
        </div>
        <v-card-subtitle class="pa-0 mt-1 revision-subtitle">
          {{ projectTitle || '当前项目' }}
          <template v-if="revisions.length > 0"> · 共 {{ revisions.length }} 个版本</template>
        </v-card-subtitle>
      </v-card-item>

      <v-card-text class="revision-body">
        <div v-if="loading && revisions.length === 0" class="revision-state">
          <v-progress-circular indeterminate size="24" color="primary" />
          <span>正在读取历史版本…</span>
        </div>

        <div v-else-if="revisions.length === 0" class="revision-state">
          <v-icon size="38" color="#cbd5e1">mdi-history</v-icon>
          <span>暂无历史版本</span>
          <span class="revision-state-hint">再次保存同一项目后，旧进度会自动收进这里</span>
        </div>

        <div v-else class="revision-list">
          <div
            v-for="(rev, idx) in revisions"
            :key="revisionKey(rev)"
            class="revision-row"
            :class="{ 'revision-row--current': idx === 0 }"
            @click="viewSnapshot(rev)"
          >
            <div class="revision-main">
              <div class="revision-title-row">
                <v-chip
                  v-if="idx === 0"
                  size="x-small"
                  color="primary"
                  variant="flat"
                  class="revision-badge"
                >当前</v-chip>
                <span class="revision-title" :title="rev.title">{{ rev.title }}</span>
                <v-chip
                  size="x-small"
                  variant="tonal"
                  :color="rev.templateType === 'pdf' ? 'primary' : 'teal'"
                >
                  {{ rev.templateType === 'pdf' ? 'PDF' : 'DOCX' }}
                </v-chip>
              </div>
              <div class="revision-meta">
                <span>
                  <v-icon size="12" class="mr-1">mdi-clock-outline</v-icon>
                  {{ formatTime(rev.savedAt) }}
                </span>
                <span v-if="rev.templateType === 'pdf'">{{ rev.iconList.length }} 个标注</span>
                <span v-else>{{ rev.loopBlocks.length }} 个循环块</span>
              </div>
            </div>

            <div class="revision-actions" @click.stop>
              <v-btn
                size="small"
                variant="text"
                color="grey-darken-1"
                rounded="lg"
                @click="viewSnapshot(rev)"
              >
                <v-icon start size="14">mdi-eye-outline</v-icon>
                查看
              </v-btn>
              <v-btn
                v-if="idx !== 0"
                size="small"
                variant="tonal"
                color="primary"
                rounded="lg"
                :loading="restoringKey === revisionKey(rev)"
                @click="emit('restore', rev)"
              >
                <v-icon start size="14">mdi-restore</v-icon>
                恢复
              </v-btn>
              <span v-else class="revision-current-text">当前版本</span>
            </div>
          </div>
        </div>
      </v-card-text>
    </v-card>
  </v-dialog>

  <!-- 查看某个版本当时保存下来的快照 -->
  <WorkspaceSnapshotPreview v-if="previewSnapshot" v-model="previewOpen" :snapshot="previewSnapshot" />
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type { WorkspaceSnapshot } from '@/types/workspace'
import { listWorkspaceRevisions, revisionKey } from '@/utils/workspace'
import WorkspaceSnapshotPreview from '@/components/WorkspaceSnapshotPreview.vue'

const props = defineProps<{
  modelValue: boolean
  dataPath: string
  projectId: string
  projectTitle?: string
  /** 正在恢复的版本标识，用于按钮 loading；由父组件控制 */
  restoringKey?: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'restore', snapshot: WorkspaceSnapshot): void
}>()

const revisions = ref<WorkspaceSnapshot[]>([])
const loading = ref(false)
const previewOpen = ref(false)
const previewSnapshot = ref<WorkspaceSnapshot | null>(null)

function viewSnapshot(snapshot: WorkspaceSnapshot) {
  previewSnapshot.value = snapshot
  previewOpen.value = true
}

function close() {
  emit('update:modelValue', false)
}

function formatTime(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

async function load() {
  if (!props.dataPath || !props.projectId) {
    revisions.value = []
    return
  }
  loading.value = true
  try {
    revisions.value = await listWorkspaceRevisions(props.dataPath, props.projectId)
  } catch (error) {
    console.error('读取历史版本失败:', error)
    revisions.value = []
  } finally {
    loading.value = false
  }
}

// 打开弹窗或切换项目时重新扫描
watch(
  () => [props.modelValue, props.dataPath, props.projectId] as const,
  ([open]) => {
    if (open) load()
  },
  { immediate: true },
)

defineExpose({ load })
</script>

<style scoped>
.revision-subtitle {
  font-size: 0.76rem !important;
  color: rgb(100, 116, 139) !important;
  min-height: 0;
}

.revision-body {
  max-height: 60vh;
  overflow-y: auto;
  padding-top: 8px !important;
}

.revision-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 150px;
  font-size: 0.8rem;
  color: #94a3b8;
}

.revision-state-hint {
  font-size: 0.72rem;
}

.revision-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.revision-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid rgba(0, 0, 0, 0.07);
  border-radius: 12px;
  cursor: pointer;
  transition: border-color 0.15s ease, background-color 0.15s ease;
}

.revision-row:hover {
  border-color: rgba(24, 103, 192, 0.35);
  background: rgba(24, 103, 192, 0.03);
}

.revision-row--current {
  border-color: rgba(24, 103, 192, 0.4);
  background: rgba(24, 103, 192, 0.05);
}

.revision-main {
  flex: 1;
  min-width: 0;
}

.revision-title-row {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.revision-title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.84rem;
  font-weight: 600;
  color: rgb(15, 23, 42);
}

.revision-badge {
  flex: none;
}

.revision-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 4px;
  font-size: 0.72rem;
  color: rgb(100, 116, 139);
}

.revision-meta span {
  display: inline-flex;
  align-items: center;
}

.revision-current-text {
  flex: none;
  font-size: 0.72rem;
  color: rgb(100, 116, 139);
}

.revision-actions {
  flex: none;
  display: flex;
  align-items: center;
  gap: 4px;
}
</style>
