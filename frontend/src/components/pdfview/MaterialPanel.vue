<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import { useBPStore } from '@/stores/bpstore';
import { getFontsList, getFontValueByName, loadCustomFonts } from '@/utils/fontLoader';
import { open } from '@tauri-apps/plugin-dialog';
import { readFile, writeFile, exists, mkdir, readDir, remove } from '@tauri-apps/plugin-fs';
import { convertFileSrc } from '@tauri-apps/api/core';

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
  { title: '图标', value: 'icon', icon: 'mdi-shape-outline' },
];

const selectedImageType = ref<'signature' | 'seal' | null>(null);
const selectedImageIndex = ref<number | null>(null);

const selectedField = ref<string | null>(null);

const size = ref(120);
const fontFamily = ref('微软雅黑');
const fontOptions = ref<Font[]>([]);
const fontDisplayNames = ref<string[]>([]);

const opacity = ref(1);
const color = ref('#000000');
const colorMenu = ref(false);

const iconChar = ref('✓');
const iconGroup = ref('marks');
const iconGroups = [
  {
    value: 'marks',
    label: '复选框',
    icons: [
      { char: '☐', label: '空方框' },
      { char: '☑', label: '勾选方框' },
      { char: '☒', label: '叉选方框' },
      { char: '✓', label: '对勾' },
      { char: '✗', label: '叉号' },
      { char: '✔', label: '粗对勾' },
      { char: '✘', label: '粗叉号' },
      { char: '●', label: '实心圆' },
    ],
  },
  {
    value: 'stars',
    label: '星形',
    icons: [
      { char: '★', label: '实心星' },
      { char: '☆', label: '空心星' },
      { char: '✦', label: '四角星' },
      { char: '✧', label: '空心四角' },
      { char: '◆', label: '实心菱形' },
      { char: '◇', label: '空心菱形' },
      { char: '■', label: '实心方块' },
      { char: '□', label: '空心方块' },
    ],
  },
  {
    value: 'arrows',
    label: '箭头',
    icons: [
      { char: '→', label: '右箭头' },
      { char: '←', label: '左箭头' },
      { char: '↑', label: '上箭头' },
      { char: '↓', label: '下箭头' },
      { char: '↔', label: '左右箭头' },
      { char: '↕', label: '上下箭头' },
      { char: '▶', label: '右三角' },
      { char: '◀', label: '左三角' },
    ],
  },
  {
    value: 'shapes',
    label: '图形',
    icons: [
      { char: '▲', label: '实心三角' },
      { char: '△', label: '空心三角' },
      { char: '▼', label: '倒三角' },
      { char: '▽', label: '空心倒三角' },
      { char: '○', label: '空心圆' },
      { char: '♥', label: '红心' },
      { char: '♦', label: '方块' },
      { char: '♣', label: '梅花' },
    ],
  },
  {
    value: 'office',
    label: '办公',
    icons: [
      { char: '☎', label: '电话' },
      { char: '✉', label: '信封' },
      { char: '✎', label: '铅笔' },
      { char: '⌂', label: '房子' },
      { char: '⌘', label: '命令键' },
      { char: '⏎', label: '回车' },
      { char: '⌫', label: '退格' },
      { char: '☺', label: '笑脸' },
    ],
  },
  {
    value: 'info',
    label: '提示',
    icons: [
      { char: '⚡', label: '闪电' },
      { char: '⚠', label: '警告' },
      { char: 'ℹ', label: '信息' },
      { char: '©', label: '版权' },
      { char: '®', label: '注册商标' },
      { char: '™', label: '商标' },
      { char: '♻', label: '回收' },
      { char: '☹', label: '哭脸' },
    ],
  },
  {
    value: 'math',
    label: '数学',
    icons: [
      { char: '≤', label: '小于等于' },
      { char: '≥', label: '大于等于' },
      { char: '±', label: '正负号' },
      { char: '×', label: '乘号' },
      { char: '÷', label: '除号' },
      { char: '√', label: '根号' },
      { char: '∞', label: '无穷' },
      { char: '∑', label: '求和' },
    ],
  },
  {
    value: 'weather',
    label: '天气',
    icons: [
      { char: '☀', label: '太阳' },
      { char: '☁', label: '云' },
      { char: '☂', label: '雨伞' },
      { char: '❄', label: '雪花' },
      { char: '♪', label: '音符' },
      { char: '♫', label: '双音符' },
      { char: '≠', label: '不等号' },
      { char: '≈', label: '约等于' },
    ],
  },
];

onMounted(async () => {
  await loadFonts();
  if (bpStore.dataPath) {
    await refreshImageLists();
  }
});

watch(() => bpStore.dataPath, async (newPath) => {
  if (newPath) {
    await loadFonts();
    await refreshImageLists();
  }
});

async function loadFonts() {
  try {
    await loadCustomFonts(bpStore.dataPath);
    fontOptions.value = await getFontsList(bpStore.dataPath);
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
}


function selectImage(type: 'signature' | 'seal', index: number) {
  selectedImageType.value = type;
  selectedImageIndex.value = index;
  const list = type === 'signature' ? bpStore.imageList_signature : bpStore.imageList_seal;
  emits('select_option', {
    type: 'image',
    src: list[index] ?? '',
    size: size.value,
  });
}

function applyImageSize(val: number) {
  imageSizeCustom.value = false;
  size.value = val;
  emitImageSize();
}

function emitImageSize() {
  if (selectedImageType.value && selectedImageIndex.value !== null) {
    const list = selectedImageType.value === 'signature' ? bpStore.imageList_signature : bpStore.imageList_seal;
    emits('select_option', {
      type: 'image',
      src: list[selectedImageIndex.value] ?? '',
      size: size.value,
    });
  }
}

function onCustomSizeInput() {
  imageSizeCustom.value = true;
  emitImageSize();
}

async function selectField(fieldName: string | null = null) {
  const actualFieldName = fieldName ?? selectedField.value;
  if (!actualFieldName) return;

  let fontValue = fontFamily.value;
  if (fontDisplayNames.value.includes(fontFamily.value)) {
    fontValue = await getFontValueByName(fontFamily.value, bpStore.dataPath);
  }

  emits('select_option', {
    type: 'field',
    fieldName: actualFieldName,
    fontFamily: fontValue,
    size: size.value
  });
}

function selectIcon(char: string) {
  iconChar.value = char;
  emits('select_option', {
    type: 'icon',
    icon: char,
    color: color.value,
    opacity: opacity.value,
    size: size.value,
  });
}

const imageSizePresets = [80, 120, 150, 200];
const imageSizeCustom = ref(false);
const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'];

async function loadImagesFromDir(dirPath: string): Promise<string[]> {
  try {
    if (!await exists(dirPath)) return [];
    const files = await readDir(dirPath);
    return files
      .filter(file => file.isFile)
      .map(file => file.name)
      .filter(name => imageExtensions.some(ext => name.toLowerCase().endsWith(ext)))
      .map(name => convertFileSrc(`${dirPath}/${name}`));
  } catch (error) {
    console.error(`无法读取图片目录 ${dirPath}:`, error);
    return [];
  }
}

async function refreshImageLists() {
  if (!bpStore.dataPath) return;
  const [sig, seal] = await Promise.all([
    loadImagesFromDir(`${bpStore.dataPath}/signImg`),
    loadImagesFromDir(`${bpStore.dataPath}/sealImg`),
  ]);
  bpStore.imageList_signature = sig;
  bpStore.imageList_seal = seal;
}

async function addImage(type: 'signature' | 'seal') {
  try {
    const selected = await open({
      multiple: true,
      filters: [{ name: '图片', extensions: ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp'] }],
    });
    if (!selected) return;

    const files = Array.isArray(selected) ? selected : [selected];
    const subDir = type === 'signature' ? 'signImg' : 'sealImg';
    const targetDir = `${bpStore.dataPath}/${subDir}`;

    if (!await exists(targetDir)) {
      await mkdir(targetDir, { recursive: true });
    }

    for (const filePath of files) {
      const fileData = await readFile(filePath);
      const fileName = filePath.split('\\').pop() || filePath.split('/').pop() || 'image';
      let targetPath = `${targetDir}/${fileName}`;
      if (await exists(targetPath)) {
        const timestamp = Date.now();
        const dotIndex = fileName.lastIndexOf('.');
        if (dotIndex > 0) {
          targetPath = `${targetDir}/${fileName.substring(0, dotIndex)}_${timestamp}${fileName.substring(dotIndex)}`;
        } else {
          targetPath = `${targetDir}/${fileName}_${timestamp}`;
        }
      }
      await writeFile(targetPath, fileData);
    }

    await refreshImageLists();
  } catch (error) {
    console.error('上传图片失败:', error);
  }
}

async function deleteImage(type: 'signature' | 'seal', index: number) {
  try {
    const subDir = type === 'signature' ? 'signImg' : 'sealImg';
    const dirPath = `${bpStore.dataPath}/${subDir}`;
    const files = await readDir(dirPath);
    const entries = files
      .filter(f => f.isFile && imageExtensions.some(ext => f.name.toLowerCase().endsWith(ext)));
    if (index >= 0 && index < entries.length) {
      await remove(`${dirPath}/${entries[index].name}`);
      if (selectedImageType.value === type && selectedImageIndex.value === index) {
        selectedImageType.value = null;
        selectedImageIndex.value = null;
      }
      await refreshImageLists();
    }
  } catch (error) {
    console.error('删除图片失败:', error);
  }
}
</script>

<template>
  <div class="material-panel">
    <div class="mp-sidebar">
      <div
        v-for="item in navItems"
        :key="item.value"
        class="mp-sidebar-item"
        :class="{ active: activeNav === item.value }"
        @click="activeNav = item.value"
      >
        <v-icon :icon="item.icon" size="20" class="mp-sidebar-icon" />
        <span class="mp-sidebar-label">{{ item.title }}</span>
      </div>
    </div>

    <div class="mp-main">
      <div v-if="activeNav === 'table'" class="mp-table-panel">
        <div class="mp-table-left">
          <div class="bento-section-label">
            <v-icon size="14" class="section-label-icon">mdi-form-select</v-icon>
            选择字段
          </div>
          <div class="mp-field-list">
            <div
              v-for="item in bpStore.fieldNames"
              :key="item"
              class="mp-field-chip"
              :class="{ selected: selectedField === item }"
              @click="selectedField = item; selectField(item)"
            >
              <span class="field-chip-text">{{ item }}</span>
              <v-icon v-if="selectedField === item" size="16" class="field-chip-check">mdi-check-circle</v-icon>
            </div>
          </div>
        </div>

        <div class="mp-divider"></div>

        <div class="mp-table-right">
          <div class="bento-section-label">
            <v-icon size="14" class="section-label-icon">mdi-palette-outline</v-icon>
            样式
          </div>
          <div class="style-card">
            <div class="mp-ctrl-row">
              <v-icon size="16" color="#94a3b8">mdi-format-font</v-icon>
              <v-select
                v-model="fontFamily"
                :items="fontOptions"
                item-title="name"
                item-value="value"
                density="compact"
                variant="outlined"
                hide-details
                class="bento-select"
                @update:model-value="() => selectField()"
              />
            </div>
          </div>
          <div class="mp-preview-box">
            <span class="mp-preview-label">预览</span>
            <span
              class="mp-preview-text"
              :style="{
                fontFamily: fontFamily,
                fontSize: Math.min(size, 28) + 'px'
              }"
            >预览文字</span>
          </div>
        </div>
      </div>

      <div v-else-if="activeNav === 'signature'" class="mp-image-panel">
        <div class="mp-image-grid">
          <div class="mp-image-wrap" v-for="(imgSrc, index) in bpStore.imageList_signature" :key="index">
            <div
              class="mp-image-card"
              :class="{ selected: selectedImageType === 'signature' && selectedImageIndex === index }"
              @click="selectImage('signature', index)"
            >
              <img :src="imgSrc" />
              <div class="mp-delete-btn" @click.stop="deleteImage('signature', index)" title="删除">
                <v-icon size="12">mdi-close</v-icon>
              </div>
              <div v-if="selectedImageType === 'signature' && selectedImageIndex === index" class="mp-check-badge">
                <v-icon size="14" color="#fff">mdi-check</v-icon>
              </div>
            </div>
          </div>
          <div class="mp-image-wrap">
            <div class="mp-image-card mp-add-card" @click="addImage('signature')">
              <v-icon size="28" color="#94a3b8">mdi-plus</v-icon>
            </div>
          </div>
        </div>

        <div class="mp-size-bar">
          <span class="mp-size-label">大小</span>
          <div class="mp-size-presets">
            <button
              v-for="preset in imageSizePresets"
              :key="preset"
              class="mp-size-chip"
              :class="{ active: !imageSizeCustom && size === preset }"
              @click="applyImageSize(preset)"
            >{{ preset }}</button>
          </div>
          <v-text-field
            v-model.number="size"
            type="number"
            density="compact"
            variant="outlined"
            hide-details
            :min="20"
            :max="400"
            class="mp-size-input"
            @update:model-value="onCustomSizeInput"
          />
        </div>
      </div>

      <div v-else-if="activeNav === 'seal'" class="mp-image-panel">
        <div class="mp-image-grid">
          <div class="mp-image-wrap" v-for="(imgSrc, index) in bpStore.imageList_seal" :key="index">
            <div
              class="mp-image-card"
              :class="{ selected: selectedImageType === 'seal' && selectedImageIndex === index }"
              @click="selectImage('seal', index)"
            >
              <img :src="imgSrc" />
              <div class="mp-delete-btn" @click.stop="deleteImage('seal', index)" title="删除">
                <v-icon size="12">mdi-close</v-icon>
              </div>
              <div v-if="selectedImageType === 'seal' && selectedImageIndex === index" class="mp-check-badge">
                <v-icon size="14" color="#fff">mdi-check</v-icon>
              </div>
            </div>
          </div>
          <div class="mp-image-wrap">
            <div class="mp-image-card mp-add-card" @click="addImage('seal')">
              <v-icon size="28" color="#94a3b8">mdi-plus</v-icon>
            </div>
          </div>
        </div>

        <div class="mp-size-bar">
          <span class="mp-size-label">大小</span>
          <div class="mp-size-presets">
            <button
              v-for="preset in imageSizePresets"
              :key="preset"
              class="mp-size-chip"
              :class="{ active: !imageSizeCustom && size === preset }"
              @click="applyImageSize(preset)"
            >{{ preset }}</button>
          </div>
          <v-text-field
            v-model.number="size"
            type="number"
            density="compact"
            variant="outlined"
            hide-details
            :min="20"
            :max="400"
            class="mp-size-input"
            @update:model-value="onCustomSizeInput"
          />
        </div>
      </div>

      <div v-else-if="activeNav === 'icon'" class="mp-icon-panel">
        <div class="mp-icon-groups">
          <v-chip-group v-model="iconGroup" selected-class="text-primary" column>
            <v-chip
              v-for="group in iconGroups"
              :key="group.value"
              :value="group.value"
              variant="tonal"
              size="small"
              filter
            >{{ group.label }}</v-chip>
          </v-chip-group>
        </div>

        <div class="mp-icon-grid">
          <div
            v-for="icon in (iconGroups.find(g => g.value === iconGroup) || iconGroups[0]).icons"
            :key="icon.char"
            class="mp-icon-cell"
            :class="{ selected: iconChar === icon.char }"
            @click="selectIcon(icon.char)"
          >
            <span
              class="mp-icon-char"
              :style="{ color: iconChar === icon.char ? color : '#334155' }"
            >{{ icon.char }}</span>
            <span class="mp-icon-label">{{ icon.label }}</span>
          </div>
        </div>

        <div class="mp-icon-controls">
          <div class="mp-ctrl-row">
            <v-icon size="16" color="#94a3b8">mdi-opacity</v-icon>
            <v-slider
              v-model="opacity"
              density="compact"
              hide-details
              :min="0.1"
              :max="1"
              :step="0.05"
              thumb-size="16"
              track-size="3"
              class="bento-slider"
              @update:model-value="() => selectIcon(iconChar)"
            />
          </div>
          <div class="mp-ctrl-row">
            <v-icon size="16" color="#94a3b8">mdi-palette</v-icon>
            <v-menu v-model="colorMenu" :close-on-content-click="false" offset="8">
              <template #activator="{ props: menuProps }">
                <div class="color-swatch" :style="{ background: color }" v-bind="menuProps"></div>
              </template>
              <v-color-picker
                v-model="color"
                mode="hex"
                hide-inputs
                @update:model-value="selectIcon(iconChar); colorMenu = false"
              />
            </v-menu>
            <span class="color-hex">{{ color }}</span>
          </div>
        </div>

        <div class="mp-preview-box">
          <span class="mp-preview-label">预览</span>
          <span
            class="mp-icon-preview"
            :style="{
              fontSize: Math.min(size, 48) + 'px',
              opacity: opacity,
              color: color
            }"
          >{{ iconChar }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ========= layout ========= */
.material-panel {
  display: grid;
  grid-template-columns: 56px 1fr;
  height: 100%;
  overflow: hidden;
  gap: 0;
}

/* ========= sidebar ========= */
.mp-sidebar {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 8px 4px;
  background: transparent;
  overflow-y: auto;
}

.mp-sidebar-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.18s ease;
  color: #94a3b8;
  gap: 2px;
}

.mp-sidebar-item:hover {
  background: rgba(79, 140, 255, 0.06);
  color: #4f8cff;
}

.mp-sidebar-item.active {
  background: linear-gradient(135deg, rgba(79,140,255,0.12), rgba(108,92,231,0.08));
  color: #4f8cff;
}

.mp-sidebar-icon {
  transition: transform 0.18s ease;
}

.mp-sidebar-item.active .mp-sidebar-icon {
  transform: scale(1.05);
}

.mp-sidebar-label {
  font-size: 10px;
  font-weight: 600;
  white-space: nowrap;
  line-height: 1;
}

/* ========= main ========= */
.mp-main {
  min-width: 0;
  padding: 8px 12px 8px 4px;
  overflow: hidden;
}

/* ========= table panel ========= */
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
  gap: 10px;
  overflow-y: auto;
}

.mp-divider {
  width: 1px;
  flex-shrink: 0;
  background: linear-gradient(180deg, transparent 0%, rgba(0,0,0,0.08) 20%, rgba(0,0,0,0.08) 80%, transparent 100%);
}

/* ========= field chips ========= */
.mp-field-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.mp-field-chip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 7px 12px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.16s ease;
  background: #f8fafc;
  border: 1px solid transparent;
}

.mp-field-chip:hover {
  background: #f1f5f9;
  border-color: rgba(79,140,255,0.2);
}

.mp-field-chip.selected {
  background: linear-gradient(135deg, rgba(79,140,255,0.08), rgba(108,92,231,0.05));
  border-color: rgba(79,140,255,0.35);
  box-shadow: 0 0 0 1px rgba(79,140,255,0.15);
}

.field-chip-text {
  font-size: 12.5px;
  font-weight: 500;
  color: #334155;
}

.mp-field-chip.selected .field-chip-text {
  color: #4f8cff;
  font-weight: 600;
}

.field-chip-check {
  color: #4f8cff;
  flex-shrink: 0;
}

/* ========= style card ========= */
.style-card {
  padding: 12px;
  border-radius: 12px;
  background: #f8fafc;
  border: 1px solid rgba(0,0,0,0.05);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* ========= right panel controls ========= */
.mp-ctrl-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mp-ctrl-row > .v-icon {
  flex-shrink: 0;
}

.mp-ctrl-row :deep(.v-input) {
  flex: 1;
  min-width: 0;
}

/* ========= color picker ========= */
.color-swatch {
  width: 26px;
  height: 26px;
  border-radius: 7px;
  border: 1.5px solid rgba(0,0,0,0.15);
  flex-shrink: 0;
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.15s;
}

.color-swatch:hover {
  transform: scale(1.1);
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}

.color-hex {
  font-size: 12px;
  font-weight: 500;
  color: #475569;
  font-family: 'SF Mono', 'Cascadia Code', monospace;
}

/* ========= slider ========= */
.bento-slider :deep(.v-slider-thumb) {
  color: #4f8cff;
}

.bento-slider :deep(.v-slider-track__fill) {
  background: #4f8cff;
}

.bento-slider :deep(.v-input__control) {
  min-height: 20px;
}

/* ========= preview ========= */
.mp-preview-box {
  padding: 14px 12px;
  border-radius: 12px;
  background: linear-gradient(135deg, #f8fafc 0%, #eef2ff 100%);
  border: 1px solid rgba(79,140,255,0.12);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 72px;
  gap: 6px;
}

.mp-preview-label {
  font-size: 10px;
  font-weight: 600;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.mp-preview-text {
  max-width: 100%;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

/* ========= image panel ========= */
.mp-image-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow: hidden;
}

.mp-image-panel .mp-image-grid {
  flex: 1;
  overflow-y: auto;
  padding-right: 4px;
}

.mp-image-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-content: flex-start;
}

.mp-image-wrap {
  width: calc((100% - 16px) / 3);
  position: relative;
}

.mp-image-wrap::before {
  content: '';
  display: block;
  padding-bottom: 100%;
}

.mp-image-card {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  cursor: pointer;
  border-radius: 12px;
  border: 2px solid transparent;
  opacity: 0.5;
  transition: opacity 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
  overflow: hidden;
  background: #f1f5f9;
}

.mp-image-card img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 10px;
}

.mp-image-card:hover {
  opacity: 0.8;
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}

.mp-image-card.selected {
  opacity: 1;
  border-color: #4f8cff;
  box-shadow: 0 0 0 3px rgba(79,140,255,0.2);
}

.mp-image-card.selected:hover {
  opacity: 1;
}

.mp-check-badge {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #4f8cff;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 6px rgba(79,140,255,0.4);
}

.mp-delete-btn {
  position: absolute;
  top: 4px;
  left: 4px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: rgba(239, 68, 68, 0.82);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.15s ease, transform 0.15s ease;
  cursor: pointer;
  z-index: 2;
}

.mp-image-card:hover .mp-delete-btn {
  opacity: 1;
}

.mp-delete-btn:hover {
  background: #ef4444;
  transform: scale(1.15);
}

.mp-add-card {
  opacity: 1;
  border: 2px dashed #cbd5e1;
  background: #f8fafc;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.mp-add-card:hover {
  border-color: #4f8cff;
  background: rgba(79, 140, 255, 0.04);
  opacity: 1;
  box-shadow: 0 4px 12px rgba(79, 140, 255, 0.1);
}

/* ========= image size bar ========= */
.mp-size-bar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 10px;
  background: #f8fafc;
  border: 1px solid rgba(0, 0, 0, 0.06);
}

.mp-size-label {
  font-size: 11px;
  font-weight: 600;
  color: #94a3b8;
  flex-shrink: 0;
}

.mp-size-presets {
  display: flex;
  gap: 4px;
  flex: 1;
}

.mp-size-chip {
  flex: 1;
  height: 28px;
  border: 1.5px solid #e2e8f0;
  background: #fff;
  border-radius: 14px;
  font-size: 12px;
  font-weight: 500;
  color: #64748b;
  cursor: pointer;
  transition: all 0.15s ease;
  padding: 0 6px;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.mp-size-chip:hover {
  border-color: #4f8cff;
  color: #4f8cff;
}

.mp-size-chip.active {
  background: linear-gradient(135deg, #4f8cff, #6366f1);
  border-color: #4f8cff;
  color: #fff;
  font-weight: 600;
  box-shadow: 0 1px 4px rgba(79, 140, 255, 0.3);
}

.mp-size-input {
  width: 64px;
  flex-shrink: 0;
}

.mp-size-input :deep(.v-field) {
  border-radius: 8px !important;
  border-color: #e2e8f0 !important;
}

.mp-size-input :deep(.v-field__input) {
  font-size: 12px !important;
  padding: 4px 8px !important;
  min-height: auto !important;
  text-align: center;
}

/* ========= shared ========= */
.bento-section-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 700;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 8px;
  flex-shrink: 0;
}

.section-label-icon {
  flex-shrink: 0;
}

/* ========= icon panel ========= */
.mp-icon-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow: hidden;
}

.mp-icon-groups {
  flex-shrink: 0;
  overflow-x: auto;
  padding-bottom: 2px;
}

.mp-icon-groups :deep(.v-slide-group__content) {
  gap: 4px;
}

.mp-icon-grid {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 6px;
  overflow-y: auto;
  padding-right: 4px;
}

.mp-icon-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  padding: 8px 4px 4px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.16s ease;
  border: 1.5px solid transparent;
  background: #f8fafc;
  min-height: 56px;
}

.mp-icon-cell:hover {
  background: #f1f5f9;
  border-color: rgba(79, 140, 255, 0.2);
}

.mp-icon-cell.selected {
  background: linear-gradient(135deg, rgba(79, 140, 255, 0.08), rgba(108, 92, 231, 0.05));
  border-color: rgba(79, 140, 255, 0.35);
  box-shadow: 0 0 0 1px rgba(79, 140, 255, 0.15);
}

.mp-icon-char {
  font-family: "Segoe UI Symbol", "Segoe UI Emoji", sans-serif;
  font-size: 22px;
  line-height: 1;
}

.mp-icon-label {
  font-size: 9px;
  color: #94a3b8;
  white-space: nowrap;
  line-height: 1;
}

.mp-icon-cell.selected .mp-icon-label {
  color: #4f8cff;
}

.mp-icon-controls {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 8px;
  border-radius: 10px;
  background: #f8fafc;
  border: 1px solid rgba(0, 0, 0, 0.05);
}

.mp-icon-preview {
  font-family: "Segoe UI Symbol", "Segoe UI Emoji", sans-serif;
  line-height: 1;
}

/* ========= select / textfield refinements ========= */
:deep(.bento-select .v-field) {
  border-radius: 8px !important;
  box-shadow: none !important;
  border-color: rgba(0,0,0,0.1) !important;
}

:deep(.bento-select .v-field:hover) {
  border-color: rgba(79,140,255,0.35) !important;
}

:deep(.bento-select .v-field--focused) {
  border-color: #4f8cff !important;
  box-shadow: 0 0 0 2px rgba(79,140,255,0.12) !important;
}

:deep(.bento-select .v-field__input) {
  font-size: 12.5px !important;
  padding: 6px 10px !important;
  min-height: auto !important;
}
</style>
