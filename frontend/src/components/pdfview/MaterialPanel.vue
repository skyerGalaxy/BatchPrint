<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useBPStore } from '@/stores/bpstore';
import { getFontsList, getFontValueByName } from '@/utils/fontLoader';

interface Font {
  name: string;
  value: string;
  type: 'system' | 'custom';
  file?: string;
  url?: string;
}

const emits = defineEmits(['select_option']);

const bpStore = useBPStore();

const activeNav = ref('table');
const navItems = [
  { title: '表格', value: 'table', icon: 'mdi-table' },
  { title: '签字', value: 'signature', icon: 'mdi-draw-pen' },
  { title: '印章', value: 'seal', icon: 'mdi-seal-variant' },
];

const selectedImageType = ref<'signature' | 'seal' | null>(null);
const selectedImageIndex = ref<number | null>(null);

const selectedField = ref<string | null>(null);

const size = ref(120);
const fontFamily = ref('微软雅黑');
const fontOptions = ref<Font[]>([]);
const fontDisplayNames = ref<string[]>([]);

onMounted(async () => {
  try {
    fontOptions.value = await getFontsList();
    fontDisplayNames.value = fontOptions.value.map(f => f.name);
    if (fontOptions.value.length > 0) {
      fontFamily.value = fontOptions.value[0].value;
    }
  } catch (error) {
    console.error('加载字体列表失败:', error);
    fontOptions.value = [
      { name: '微软雅黑', value: '微软雅黑', type: 'system' },
      { name: '宋体', value: '宋体', type: 'system' },
      { name: '黑体', value: '黑体', type: 'system' },
      { name: 'Arial', value: 'Arial', type: 'system' },
      { name: 'Times New Roman', value: 'Times New Roman', type: 'system' },
    ];
    fontDisplayNames.value = fontOptions.value.map(f => f.name);
    fontFamily.value = fontOptions.value[0].value;
  }
});


function selectImage(type: 'signature' | 'seal', index: number) {
  selectedImageType.value = type;
  selectedImageIndex.value = index;
  const list = type === 'signature' ? bpStore.imageList_signature : bpStore.imageList_seal;
  emits('select_option', {
    type: 'image',
    src: list[index] ?? ''
  });
}

async function selectField(fieldName: string | null = null) {
  let fontValue = fontFamily.value;
  if (fontDisplayNames.value.includes(fontFamily.value)) {
    fontValue = await getFontValueByName(fontFamily.value);
  }

  emits('select_option', {
    type: 'field',
    fieldName: fieldName ?? selectedField.value ?? '',
    fontFamily: fontValue,
    size: size.value
  });
}
</script>

<template>
  <div class="material-panel">
    <div class="mp-nav">
      <v-list density="compact" nav class="mp-nav-list">
        <v-list-item
          v-for="item in navItems"
          :key="item.value"
          :prepend-icon="item.icon"
          :title="item.title"
          :active="activeNav === item.value"
          @click="activeNav = item.value"
          class="mp-nav-item"
          rounded="pill"
        />
      </v-list>
    </div>

    <div class="mp-content">
      <div v-if="activeNav === 'table'" class="mp-table-panel">
        <div class="mp-table-left">
          <div class="section-label">选择字段</div>
          <v-radio-group
            @update:model-value="(value: string | null) => selectField(value)"
            v-model="selectedField"
            hide-details
            class="mp-radio-group"
          >
            <v-radio
              v-for="item in bpStore.fieldNames"
              :key="item"
              :label="item"
              :value="item"
              density="compact"
            />
          </v-radio-group>
        </div>

        <v-divider vertical />

        <div class="mp-table-right">
          <div class="section-label">样式</div>
          <div class="mp-ctrl-row">
            <span class="mp-ctrl-label">字体</span>
            <v-select
              v-model="fontFamily"
              :items="fontOptions"
              item-title="name"
              item-value="value"
              density="compact"
              variant="plain"
              hide-details
              @update:model-value="() => selectField()"
            />
          </div>
          <div class="mp-ctrl-row">
            <span class="mp-ctrl-label">字号</span>
            <v-text-field
              v-model.number="size"
              type="number"
              density="compact"
              variant="plain"
              hide-details
              :min="16"
              :max="200"
              @update:model-value="() => selectField()"
            />
          </div>
          <div class="mp-preview-box">
            <span class="mp-preview-label">预览</span>
            <span class="mp-preview-text" :style="{ fontFamily: fontFamily, fontSize: Math.min(size, 32) + 'px', color: '#1f1f1f' }">预览文字</span>
          </div>
        </div>
      </div>

      <div v-else-if="activeNav === 'signature'" class="mp-image-panel">
        <div v-if="bpStore.imageList_signature.length === 0" class="mp-empty">
          <v-icon size="40" color="grey-lighten-1">mdi-image-off-outline</v-icon>
          <p>暂无签名，请先在素材库中添加</p>
        </div>
        <div v-else class="mp-image-grid">
          <div
            v-for="(imgSrc, index) in bpStore.imageList_signature"
            :key="index"
            class="mp-image-item"
            :class="{ 'is-selected': selectedImageType === 'signature' && selectedImageIndex === index }"
            @click="selectImage('signature', index)"
          >
            <v-img :src="imgSrc" aspect-ratio="1" cover class="mp-image-thumb" />
            <v-icon v-if="selectedImageType === 'signature' && selectedImageIndex === index" class="mp-check-icon" color="primary" size="20">mdi-check-circle</v-icon>
          </div>
        </div>
      </div>

      <div v-else-if="activeNav === 'seal'" class="mp-image-panel">
        <div v-if="bpStore.imageList_seal.length === 0" class="mp-empty">
          <v-icon size="40" color="grey-lighten-1">mdi-image-off-outline</v-icon>
          <p>暂无印章，请先在素材库中添加</p>
        </div>
        <div v-else class="mp-image-grid">
          <div
            v-for="(imgSrc, index) in bpStore.imageList_seal"
            :key="index"
            class="mp-image-item"
            :class="{ 'is-selected': selectedImageType === 'seal' && selectedImageIndex === index }"
            @click="selectImage('seal', index)"
          >
            <v-img :src="imgSrc" aspect-ratio="1" cover class="mp-image-thumb" />
            <v-icon v-if="selectedImageType === 'seal' && selectedImageIndex === index" class="mp-check-icon" color="primary" size="20">mdi-check-circle</v-icon>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ===== layout ===== */
.material-panel {
  display: grid;
  grid-template-columns: auto 1fr;
  height: 100%;
  overflow: hidden;
}

.mp-nav {
  display: flex;
  flex-direction: column;
  padding: 8px 4px;
  background: rgb(248, 249, 250);
  overflow-y: auto;
}

.mp-nav-list { background: transparent; }

.mp-nav-item {
  height: 36px !important;
  min-height: 36px !important;
  margin-bottom: 4px !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  color: rgb(68, 71, 70) !important;
  padding: 0 10px !important;
  transition: background-color 0.15s ease;
}
.mp-nav-item:hover { background-color: rgba(0, 0, 0, 0.04); }

:deep(.mp-nav-item .v-list-item-title) {
  font-size: 13px !important;
  font-weight: 500 !important;
}
:deep(.mp-nav-item .v-list-item__prepend) {
  margin-inline-end: 10px !important;
}
:deep(.mp-nav-item--active) {
  background-color: rgb(219, 227, 241) !important;
  color: rgb(4, 30, 73) !important;
}

.mp-content {
  min-width: 0;
  padding: 12px;
  overflow: hidden;
}

/* ===== table panel ===== */
.mp-table-panel {
  height: 100%;
  display: flex;
}

.mp-table-left {
  flex: 1;
  min-width: 0;
  padding-right: 12px;
  overflow-y: auto;
}

.mp-table-right {
  width: 200px;
  flex-shrink: 0;
  padding-left: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* ===== right panel controls ===== */
.mp-ctrl-row {
  display: flex;
  align-items: center;
  gap: 0;
}

.mp-ctrl-label {
  flex-shrink: 0;
  width: 40px;
  font-size: 13px;
  color: rgb(68, 71, 70);
}

.mp-ctrl-row :deep(.v-input) {
  flex: 1;
  min-width: 0;
}

.mp-ctrl-row :deep(.v-field) {
  font-size: 13px;
}

.mp-ctrl-row :deep(.v-field__input) {
  min-height: auto;
  padding-top: 4px;
  padding-bottom: 4px;
}

/* ===== preview ===== */
.mp-preview-box {
  margin-top: auto;
  padding: 10px 12px;
  border: 1px solid rgba(0, 0, 0, 0.12);
  border-radius: 8px;
  background: rgb(248, 249, 250);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 72px;
  gap: 4px;
}

.mp-preview-label {
  font-size: 11px;
  color: rgb(148, 163, 184);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.mp-preview-text {
  max-width: 100%;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

/* ===== image panel ===== */
.mp-image-panel {
  height: 100%;
  overflow-y: auto;
}

.mp-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: rgb(148, 163, 184);
  font-size: 13px;
  gap: 8px;
}

.mp-image-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.mp-image-item {
  position: relative;
  cursor: pointer;
  border-radius: 8px;
  overflow: hidden;
  border: 2px solid transparent;
  opacity: 0.45;
  transition: opacity 0.15s, border-color 0.15s;
}
.mp-image-item.is-selected { opacity: 1; border-color: rgb(var(--v-theme-primary)); }
.mp-image-item:hover { opacity: 0.75; }
.mp-image-item.is-selected:hover { opacity: 1; }

.mp-check-icon {
  position: absolute;
  top: 4px;
  right: 4px;
  filter: drop-shadow(0 1px 2px rgba(255,255,255,0.8));
}

.mp-image-thumb { width: 100%; }

/* ===== shared ===== */
.section-label {
  font-size: 0.68rem;
  font-weight: 600;
  color: rgb(100, 116, 139);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 6px;
  flex-shrink: 0;
}

.mp-radio-group { width: 100%; }
</style>
