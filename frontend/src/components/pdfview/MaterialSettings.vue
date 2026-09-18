<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useBPStore } from '@/stores/bpstore';
import { getFontsList, loadCustomFonts } from '@/utils/fontLoader';
import type { IconOption, MaterialKind } from '@/types/icon';

export type { MaterialKind };

const props = defineProps<{
  kind: MaterialKind;
}>();

const option = defineModel<IconOption>('option', { required: true });

const bpStore = useBPStore();

interface Font {
  name: string;
  value: string;
  type: 'system' | 'custom';
  file?: string;
  url?: string;
}

const fontOptions = ref<Font[]>([]);

async function loadFonts() {
  try {
    await loadCustomFonts(bpStore.dataPath);
    fontOptions.value = await getFontsList(bpStore.dataPath);
  } catch (error) {
    console.error('加载字体列表失败:', error);
    fontOptions.value = [
      { name: '楷体', value: '楷体', type: 'system' },
      { name: '微软雅黑', value: '微软雅黑', type: 'system' },
      { name: '宋体', value: '宋体', type: 'system' },
      { name: '黑体', value: '黑体', type: 'system' },
      { name: 'Arial', value: 'Arial', type: 'system' },
      { name: 'Times New Roman', value: 'Times New Roman', type: 'system' },
    ];
  }
}

onMounted(loadFonts);
watch(() => bpStore.dataPath, loadFonts);
watch(() => bpStore.fontsVersion, loadFonts);

/* ========= 类型标记 ========= */
const isField = computed(() => props.kind === 'table');
const isSignature = computed(() => props.kind === 'signature');
const isSeal = computed(() => props.kind === 'seal');
const isIcon = computed(() => props.kind === 'icon');
const isText = computed(() => props.kind === 'text');

/* ========= 图片（签字 / 印章） ========= */
const imageList = computed(() =>
  props.kind === 'signature'
    ? bpStore.imageList_signature
    : bpStore.imageList_seal,
);

const sizePresets = [80, 120, 150, 200];

function pickImage(src: string) {
  option.value.src = src;
}

/* ========= 图片选择区折叠（默认折叠，未选图时自动展开） ========= */
const imagePickerOpen = ref(false);

watch(() => option.value.src, (src) => {
  if (!src) imagePickerOpen.value = true;
}, { immediate: true });

watch(() => props.kind, () => {
  imagePickerOpen.value = !option.value.src;
});

/* ========= 带默认值的模型（兼容旧数据缺省字段） ========= */
const sizeModel = computed({
  get: () => option.value.size ?? 120,
  set: (v: number) => { option.value.size = v; },
});

const opacityModel = computed({
  get: () => option.value.opacity ?? 1,
  set: (v: number) => { option.value.opacity = v; },
});

const fontWeightModel = computed({
  get: () => option.value.fontWeight ?? 400,
  set: (v: number) => { option.value.fontWeight = v; },
});

/** 圆角：0-50，短边尺寸的百分比 */
const cornerRadiusModel = computed({
  get: () => option.value.cornerRadius ?? 0,
  set: (v: number) => { option.value.cornerRadius = v; },
});

/** 印章锁定纵横比，缺省视为锁定 */
const sealKeepRatio = computed({
  get: () => option.value.keepRatio !== false,
  set: (v: boolean) => { option.value.keepRatio = v; },
});

/* ========= 预设图标 ========= */
const iconGroups = [
  {
    value: 'marks', label: '复选框',
    icons: [
      { char: '☐', label: '空方框' }, { char: '☑', label: '勾选方框' },
      { char: '☒', label: '叉选方框' }, { char: '✓', label: '对勾' },
      { char: '✗', label: '叉号' }, { char: '✔', label: '粗对勾' },
      { char: '✘', label: '粗叉号' }, { char: '●', label: '实心圆' },
    ],
  },
  {
    value: 'stars', label: '星形',
    icons: [
      { char: '★', label: '实心星' }, { char: '☆', label: '空心星' },
      { char: '✦', label: '四角星' }, { char: '✧', label: '空心四角' },
      { char: '◆', label: '实心菱形' }, { char: '◇', label: '空心菱形' },
      { char: '■', label: '实心方块' }, { char: '□', label: '空心方块' },
    ],
  },
  {
    value: 'arrows', label: '箭头',
    icons: [
      { char: '→', label: '右箭头' }, { char: '←', label: '左箭头' },
      { char: '↑', label: '上箭头' }, { char: '↓', label: '下箭头' },
      { char: '↔', label: '左右箭头' }, { char: '↕', label: '上下箭头' },
      { char: '▶', label: '右三角' }, { char: '◀', label: '左三角' },
    ],
  },
  {
    value: 'shapes', label: '图形',
    icons: [
      { char: '▲', label: '实心三角' }, { char: '△', label: '空心三角' },
      { char: '▼', label: '倒三角' }, { char: '▽', label: '空心倒三角' },
      { char: '○', label: '空心圆' }, { char: '♥', label: '红心' },
      { char: '♦', label: '方块' }, { char: '♣', label: '梅花' },
    ],
  },
  {
    value: 'office', label: '办公',
    icons: [
      { char: '☎', label: '电话' }, { char: '✉', label: '信封' },
      { char: '✎', label: '铅笔' }, { char: '⌂', label: '房子' },
      { char: '⌘', label: '命令键' }, { char: '⏎', label: '回车' },
      { char: '⌫', label: '退格' }, { char: '☺', label: '笑脸' },
    ],
  },
  {
    value: 'info', label: '提示',
    icons: [
      { char: '⚡', label: '闪电' }, { char: '⚠', label: '警告' },
      { char: 'ℹ', label: '信息' }, { char: '©', label: '版权' },
      { char: '®', label: '注册商标' }, { char: '™', label: '商标' },
      { char: '♻', label: '回收' }, { char: '☹', label: '哭脸' },
    ],
  },
  {
    value: 'math', label: '数学',
    icons: [
      { char: '≤', label: '小于等于' }, { char: '≥', label: '大于等于' },
      { char: '±', label: '正负号' }, { char: '×', label: '乘号' },
      { char: '÷', label: '除号' }, { char: '√', label: '根号' },
      { char: '∞', label: '无穷' }, { char: '∑', label: '求和' },
    ],
  },
  {
    value: 'weather', label: '天气',
    icons: [
      { char: '☀', label: '太阳' }, { char: '☁', label: '云' },
      { char: '☂', label: '雨伞' }, { char: '❄', label: '雪花' },
      { char: '♪', label: '音符' }, { char: '♫', label: '双音符' },
      { char: '≠', label: '不等号' }, { char: '≈', label: '约等于' },
    ],
  },
];

const activeIconGroup = ref('marks');
const colorMenu = ref(false);

/* ========= 预览 ========= */
const previewChar = computed(() => {
  if (isIcon.value) return option.value.icon || '✓';
  if (isText.value) return option.value.text || '预览文字';
  if (isField.value) {
    const idx = bpStore.fieldNames.indexOf(option.value.fieldName || '');
    const val = idx >= 0 ? bpStore.excelContent[0]?.[idx] : undefined;
    return val === undefined || val === null || val === ''
      ? (option.value.fieldName || '字段预览')
      : String(val);
  }
  return '';
});

const textStylePreview = computed(() => ({
  fontFamily: option.value.fontFamily,
  fontWeight: option.value.fontWeight,
  fontStyle: option.value.italic ? 'italic' : 'normal',
  color: option.value.color || '#000000',
  opacity: opacityModel.value,
  fontSize: Math.min(Math.floor(sizeModel.value * 0.22), 22) + 'px',
}));

const PREVIEW_BOX = 72;
const imagePreviewRadius = computed(() => `${Math.round((PREVIEW_BOX * cornerRadiusModel.value) / 100)}px`);
</script>

<template>
  <div class="ms-panel">
    <!-- ========= 字段 ========= -->
    <template v-if="isField">
      <div class="ms-section">
        <div class="ms-label"><v-icon size="13">mdi-form-select</v-icon>选择字段</div>
        <v-select
          v-model="option.fieldName"
          :items="bpStore.fieldNames"
          density="compact"
          variant="outlined"
          hide-details
          placeholder="选择 Excel 字段"
          class="ms-select"
        />
        <div v-if="bpStore.fieldNames.length === 0" class="ms-empty-inline">请先选择 Excel 文件</div>
      </div>

      <div class="ms-section">
        <div class="ms-label"><v-icon size="13">mdi-palette-outline</v-icon>文字样式</div>
        <div class="ms-style-card">
          <div class="ms-row">
            <v-icon size="15" color="#94a3b8">mdi-format-font</v-icon>
            <span class="ms-row-label">字体</span>
            <v-select
              v-model="option.fontFamily"
              :items="fontOptions"
              item-title="name"
              item-value="value"
              density="compact"
              variant="outlined"
              hide-details
              class="ms-select"
            />
          </div>

          <div class="ms-row">
            <v-icon size="15" color="#94a3b8">mdi-arrow-expand-all</v-icon>
            <span class="ms-row-label">大小</span>
            <v-text-field
              v-model.number="sizeModel"
              type="number"
              density="compact"
              variant="outlined"
              hide-details
              :min="20"
              :max="400"
              class="ms-size-input"
            />
            <v-slider
              v-model.number="sizeModel"
              density="compact"
              hide-details
              :min="20"
              :max="400"
              :step="2"
              thumb-size="14"
              track-size="3"
              color="primary"
              class="ms-slider"
            />
          </div>

          <div class="ms-row">
            <v-icon size="15" color="#94a3b8">mdi-format-bold</v-icon>
            <v-btn-toggle
              v-model="fontWeightModel"
              mandatory
              density="compact"
              variant="outlined"
              divided
              class="ms-weight"
            >
              <v-btn :value="400" size="x-small">常规</v-btn>
              <v-btn :value="700" size="x-small">粗体</v-btn>
            </v-btn-toggle>
            <v-icon size="15" color="#94a3b8">mdi-format-italic</v-icon>
            <v-btn
              size="x-small"
              icon="mdi-format-italic"
              :variant="option.italic ? 'tonal' : 'text'"
              :color="option.italic ? 'primary' : 'grey'"
              @click="option.italic = !option.italic"
            />
          </div>

          <div class="ms-row">
            <v-icon size="15" color="#94a3b8">mdi-palette</v-icon>
            <span class="ms-row-label">颜色</span>
            <v-menu v-model="colorMenu" :close-on-content-click="false" offset="8">
              <template #activator="{ props: menuProps }">
                <div class="ms-swatch" :style="{ background: option.color || '#000' }" v-bind="menuProps"></div>
              </template>
              <v-color-picker
                v-model="option.color"
                mode="hex"
                hide-inputs
                @update:model-value="colorMenu = false"
              />
            </v-menu>
            <span class="ms-hex">{{ option.color }}</span>
          </div>

          <div class="ms-row">
            <v-icon size="15" color="#94a3b8">mdi-opacity</v-icon>
            <span class="ms-row-label">透明度</span>
            <v-slider
              v-model="opacityModel"
              density="compact"
              hide-details
              :min="0.1"
              :max="1"
              :step="0.05"
              thumb-size="14"
              track-size="3"
              color="primary"
              class="ms-slider"
            />
            <span class="ms-op-value">{{ Math.round(opacityModel * 100) }}%</span>
          </div>
        </div>
      </div>

      <div class="ms-preview">
        <span class="ms-preview-label">预览</span>
        <span class="ms-preview-text" :style="textStylePreview">{{ previewChar }}</span>
      </div>
    </template>

    <!-- ========= 签字 ========= -->
    <template v-else-if="isSignature">
      <div class="ms-section" :class="{ 'ms-section--grow': imagePickerOpen }">
        <button type="button" class="ms-collapse-head" @click="imagePickerOpen = !imagePickerOpen">
          <v-icon size="13">mdi-draw-pen</v-icon>
          <span>选择签字</span>
          <span class="ms-collapse-badge" :class="{ ok: !!option.src }">{{ option.src ? '已选择' : '未选择' }}</span>
          <v-icon size="16" class="ms-collapse-chevron" :class="{ open: imagePickerOpen }">mdi-chevron-down</v-icon>
        </button>
        <template v-if="imagePickerOpen">
          <div v-if="imageList.length === 0" class="ms-empty-block">设置路径下暂无签字图片</div>
          <div v-else class="ms-image-grid">
          <button
            v-for="(img, idx) in imageList"
            :key="idx"
            type="button"
            class="ms-image-card"
            :class="{ selected: option.src === img }"
            @click="pickImage(img)"
          >
            <img :src="img" />
            <div v-if="option.src === img" class="ms-check-badge">
              <v-icon size="13" color="#fff">mdi-check</v-icon>
            </div>
          </button>
          </div>
        </template>
      </div>

      <div class="ms-section">
        <div class="ms-label"><v-icon size="13">mdi-image-edit-outline</v-icon>图片样式</div>
        <div class="ms-style-card">
          <div class="ms-size-presets">
            <button
              v-for="preset in sizePresets"
              :key="preset"
              type="button"
              class="ms-size-chip"
              :class="{ active: sizeModel === preset }"
              @click="sizeModel = preset"
            >{{ preset }}</button>
          </div>

          <div class="ms-row">
            <v-icon size="15" color="#94a3b8">mdi-rectangle-outline</v-icon>
            <span class="ms-row-label">圆角</span>
            <v-slider
              v-model.number="cornerRadiusModel"
              density="compact"
              hide-details
              :min="0"
              :max="50"
              :step="1"
              thumb-size="14"
              track-size="3"
              color="primary"
              class="ms-slider"
            />
            <span class="ms-op-value">{{ cornerRadiusModel }}%</span>
          </div>

          <div class="ms-row">
            <v-icon size="15" color="#94a3b8">mdi-arrow-expand-all</v-icon>
            <span class="ms-row-label">大小</span>
            <v-text-field
              v-model.number="sizeModel"
              type="number"
              density="compact"
              variant="outlined"
              hide-details
              :min="20"
              :max="400"
              class="ms-size-input"
            />
            <v-slider
              v-model.number="sizeModel"
              density="compact"
              hide-details
              :min="20"
              :max="400"
              :step="2"
              thumb-size="14"
              track-size="3"
              color="primary"
              class="ms-slider"
            />
          </div>

          <div class="ms-row">
            <v-icon size="15" color="#94a3b8">mdi-opacity</v-icon>
            <span class="ms-row-label">透明度</span>
            <v-slider
              v-model="opacityModel"
              density="compact"
              hide-details
              :min="0.1"
              :max="1"
              :step="0.05"
              thumb-size="14"
              track-size="3"
              color="primary"
              class="ms-slider"
            />
            <span class="ms-op-value">{{ Math.round(opacityModel * 100) }}%</span>
          </div>
        </div>
      </div>

      <div class="ms-preview">
        <span class="ms-preview-label">预览</span>
        <div class="ms-img-box" :style="{ borderRadius: imagePreviewRadius }">
          <img
            v-if="option.src"
            :src="option.src"
            :style="{ opacity: opacityModel, objectFit: 'contain' }"
          />
          <span v-else class="ms-img-empty">未选择图片</span>
        </div>
      </div>
    </template>

    <!-- ========= 印章 ========= -->
    <template v-else-if="isSeal">
      <div class="ms-section" :class="{ 'ms-section--grow': imagePickerOpen }">
        <button type="button" class="ms-collapse-head" @click="imagePickerOpen = !imagePickerOpen">
          <v-icon size="13">mdi-seal-variant</v-icon>
          <span>选择印章</span>
          <span class="ms-collapse-badge" :class="{ ok: !!option.src }">{{ option.src ? '已选择' : '未选择' }}</span>
          <v-icon size="16" class="ms-collapse-chevron" :class="{ open: imagePickerOpen }">mdi-chevron-down</v-icon>
        </button>
        <template v-if="imagePickerOpen">
          <div v-if="imageList.length === 0" class="ms-empty-block">设置路径下暂无印章图片</div>
          <div v-else class="ms-image-grid">
          <button
            v-for="(img, idx) in imageList"
            :key="idx"
            type="button"
            class="ms-image-card"
            :class="{ selected: option.src === img }"
            @click="pickImage(img)"
          >
            <img :src="img" />
            <div v-if="option.src === img" class="ms-check-badge">
              <v-icon size="13" color="#fff">mdi-check</v-icon>
            </div>
          </button>
          </div>
        </template>
      </div>

      <div class="ms-section">
        <div class="ms-label"><v-icon size="13">mdi-image-edit-outline</v-icon>图片样式</div>
        <div class="ms-style-card">
          <div class="ms-size-presets">
            <button
              v-for="preset in sizePresets"
              :key="preset"
              type="button"
              class="ms-size-chip"
              :class="{ active: sizeModel === preset }"
              @click="sizeModel = preset"
            >{{ preset }}</button>
          </div>

          <div class="ms-row">
            <v-icon size="15" color="#94a3b8">mdi-arrow-expand-all</v-icon>
            <span class="ms-row-label">大小</span>
            <v-text-field
              v-model.number="sizeModel"
              type="number"
              density="compact"
              variant="outlined"
              hide-details
              :min="20"
              :max="400"
              class="ms-size-input"
            />
            <v-slider
              v-model.number="sizeModel"
              density="compact"
              hide-details
              :min="20"
              :max="400"
              :step="2"
              thumb-size="14"
              track-size="3"
              color="primary"
              class="ms-slider"
            />
          </div>

          <div class="ms-row">
            <v-icon size="15" color="#94a3b8">mdi-lock-outline</v-icon>
            <span class="ms-row-label">锁定纵横比</span>
            <v-spacer />
            <v-switch
              v-model="sealKeepRatio"
              density="compact"
              hide-details
              color="primary"
              class="ms-switch"
            />
          </div>

          <div class="ms-row">
            <v-icon size="15" color="#94a3b8">mdi-rectangle-outline</v-icon>
            <span class="ms-row-label">圆角</span>
            <v-slider
              v-model.number="cornerRadiusModel"
              density="compact"
              hide-details
              :min="0"
              :max="50"
              :step="1"
              thumb-size="14"
              track-size="3"
              color="primary"
              class="ms-slider"
            />
            <span class="ms-op-value">{{ cornerRadiusModel }}%</span>
          </div>

          <div class="ms-row">
            <v-icon size="15" color="#94a3b8">mdi-opacity</v-icon>
            <span class="ms-row-label">透明度</span>
            <v-slider
              v-model="opacityModel"
              density="compact"
              hide-details
              :min="0.1"
              :max="1"
              :step="0.05"
              thumb-size="14"
              track-size="3"
              color="primary"
              class="ms-slider"
            />
            <span class="ms-op-value">{{ Math.round(opacityModel * 100) }}%</span>
          </div>
        </div>
      </div>

      <div class="ms-preview">
        <span class="ms-preview-label">预览</span>
        <div class="ms-img-box" :style="{ borderRadius: imagePreviewRadius }">
          <img
            v-if="option.src"
            :src="option.src"
            :style="{ opacity: opacityModel, objectFit: option.keepRatio === false ? 'fill' : 'contain' }"
          />
          <span v-else class="ms-img-empty">未选择图片</span>
        </div>
      </div>
    </template>

    <!-- ========= 图标 ========= -->
    <template v-else-if="isIcon">
      <div class="ms-section ms-section--grow">
        <div class="ms-label"><v-icon size="13">mdi-shape-outline</v-icon>选择图标</div>
        <v-chip-group v-model="activeIconGroup" selected-class="text-primary" column class="ms-group-chips">
          <v-chip
            v-for="g in iconGroups"
            :key="g.value"
            :value="g.value"
            variant="tonal"
            size="small"
            filter
          >{{ g.label }}</v-chip>
        </v-chip-group>
        <div class="ms-icon-grid">
          <button
            v-for="ic in (iconGroups.find(g => g.value === activeIconGroup) || iconGroups[0]).icons"
            :key="ic.char"
            type="button"
            class="ms-icon-cell"
            :class="{ selected: option.icon === ic.char }"
            :title="ic.label"
            @click="option.icon = ic.char"
          >
            <span class="ms-icon-char" :style="{ color: option.icon === ic.char ? (option.color || '#000') : '#334155' }">{{ ic.char }}</span>
          </button>
        </div>
      </div>

      <div class="ms-section">
        <div class="ms-label"><v-icon size="13">mdi-palette-outline</v-icon>样式</div>
        <div class="ms-style-card">
          <div class="ms-row">
            <v-icon size="15" color="#94a3b8">mdi-arrow-expand-all</v-icon>
            <span class="ms-row-label">大小</span>
            <v-text-field
              v-model.number="sizeModel"
              type="number"
              density="compact"
              variant="outlined"
              hide-details
              :min="20"
              :max="400"
              class="ms-size-input"
            />
            <v-slider
              v-model.number="sizeModel"
              density="compact"
              hide-details
              :min="20"
              :max="400"
              :step="2"
              thumb-size="14"
              track-size="3"
              color="primary"
              class="ms-slider"
            />
          </div>

          <div class="ms-row">
            <v-icon size="15" color="#94a3b8">mdi-palette</v-icon>
            <span class="ms-row-label">颜色</span>
            <v-menu v-model="colorMenu" :close-on-content-click="false" offset="8">
              <template #activator="{ props: menuProps }">
                <div class="ms-swatch" :style="{ background: option.color || '#000' }" v-bind="menuProps"></div>
              </template>
              <v-color-picker
                v-model="option.color"
                mode="hex"
                hide-inputs
                @update:model-value="colorMenu = false"
              />
            </v-menu>
            <span class="ms-hex">{{ option.color }}</span>
          </div>

          <div class="ms-row">
            <v-icon size="15" color="#94a3b8">mdi-opacity</v-icon>
            <span class="ms-row-label">透明度</span>
            <v-slider
              v-model="opacityModel"
              density="compact"
              hide-details
              :min="0.1"
              :max="1"
              :step="0.05"
              thumb-size="14"
              track-size="3"
              color="primary"
              class="ms-slider"
            />
            <span class="ms-op-value">{{ Math.round(opacityModel * 100) }}%</span>
          </div>
        </div>
      </div>

      <div class="ms-preview">
        <span class="ms-preview-label">预览</span>
        <span
          class="ms-preview-icon"
          :style="{ fontSize: '30px', color: option.color || '#000', opacity: opacityModel }"
        >{{ previewChar }}</span>
      </div>
    </template>

    <!-- ========= 文本 ========= -->
    <template v-else>
      <div class="ms-section">
        <div class="ms-label"><v-icon size="13">mdi-format-text</v-icon>文本内容</div>
        <v-textarea
          v-model="option.text"
          density="compact"
          variant="outlined"
          hide-details
          placeholder="输入自定义文本"
          rows="2"
          auto-grow
          class="ms-textarea"
        />
      </div>

      <div class="ms-section">
        <div class="ms-label"><v-icon size="13">mdi-palette-outline</v-icon>文字样式</div>
        <div class="ms-style-card">
          <div class="ms-row">
            <v-icon size="15" color="#94a3b8">mdi-format-font</v-icon>
            <span class="ms-row-label">字体</span>
            <v-select
              v-model="option.fontFamily"
              :items="fontOptions"
              item-title="name"
              item-value="value"
              density="compact"
              variant="outlined"
              hide-details
              class="ms-select"
            />
          </div>

          <div class="ms-row">
            <v-icon size="15" color="#94a3b8">mdi-arrow-expand-all</v-icon>
            <span class="ms-row-label">大小</span>
            <v-text-field
              v-model.number="sizeModel"
              type="number"
              density="compact"
              variant="outlined"
              hide-details
              :min="20"
              :max="400"
              class="ms-size-input"
            />
            <v-slider
              v-model.number="sizeModel"
              density="compact"
              hide-details
              :min="20"
              :max="400"
              :step="2"
              thumb-size="14"
              track-size="3"
              color="primary"
              class="ms-slider"
            />
          </div>

          <div class="ms-row">
            <v-icon size="15" color="#94a3b8">mdi-format-bold</v-icon>
            <v-btn-toggle
              v-model="fontWeightModel"
              mandatory
              density="compact"
              variant="outlined"
              divided
              class="ms-weight"
            >
              <v-btn :value="400" size="x-small">常规</v-btn>
              <v-btn :value="700" size="x-small">粗体</v-btn>
            </v-btn-toggle>
            <v-icon size="15" color="#94a3b8">mdi-format-italic</v-icon>
            <v-btn
              size="x-small"
              icon="mdi-format-italic"
              :variant="option.italic ? 'tonal' : 'text'"
              :color="option.italic ? 'primary' : 'grey'"
              @click="option.italic = !option.italic"
            />
          </div>

          <div class="ms-row">
            <v-icon size="15" color="#94a3b8">mdi-palette</v-icon>
            <span class="ms-row-label">颜色</span>
            <v-menu v-model="colorMenu" :close-on-content-click="false" offset="8">
              <template #activator="{ props: menuProps }">
                <div class="ms-swatch" :style="{ background: option.color || '#000' }" v-bind="menuProps"></div>
              </template>
              <v-color-picker
                v-model="option.color"
                mode="hex"
                hide-inputs
                @update:model-value="colorMenu = false"
              />
            </v-menu>
            <span class="ms-hex">{{ option.color }}</span>
          </div>

          <div class="ms-row">
            <v-icon size="15" color="#94a3b8">mdi-opacity</v-icon>
            <span class="ms-row-label">透明度</span>
            <v-slider
              v-model="opacityModel"
              density="compact"
              hide-details
              :min="0.1"
              :max="1"
              :step="0.05"
              thumb-size="14"
              track-size="3"
              color="primary"
              class="ms-slider"
            />
            <span class="ms-op-value">{{ Math.round(opacityModel * 100) }}%</span>
          </div>
        </div>
      </div>

      <div class="ms-preview">
        <span class="ms-preview-label">预览</span>
        <span class="ms-preview-text" :style="textStylePreview">{{ previewChar }}</span>
      </div>
    </template>
  </div>
</template>

<style scoped>
.ms-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow-y: auto;
  padding: 2px 4px 6px 2px;
  overscroll-behavior: contain;
}

.ms-panel::-webkit-scrollbar {
  width: 4px;
}
.ms-panel::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.12);
  border-radius: 4px;
}

.ms-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex-shrink: 0;
}

.ms-section--grow {
  flex: 1;
  min-height: 0;
}

.ms-label {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 10.5px;
  font-weight: 700;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

/* ---- 折叠头（图片选择区） ---- */
.ms-collapse-head {
  display: flex;
  align-items: center;
  gap: 5px;
  width: 100%;
  padding: 0;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 10.5px;
  font-weight: 700;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.ms-collapse-head:hover {
  color: #64748b;
}

.ms-collapse-badge {
  font-size: 9.5px;
  font-weight: 600;
  text-transform: none;
  letter-spacing: 0;
  padding: 1px 7px;
  border-radius: 7px;
  background: rgba(0, 0, 0, 0.06);
  color: #94a3b8;
}

.ms-collapse-badge.ok {
  background: rgba(16, 185, 129, 0.12);
  color: #10b981;
}

.ms-collapse-chevron {
  margin-left: auto;
  color: #94a3b8;
  transition: transform 0.15s;
}

.ms-collapse-chevron.open {
  transform: rotate(180deg);
}

.ms-style-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px;
  border-radius: 10px;
  background: #f8fafc;
  border: 1px solid rgba(0, 0, 0, 0.05);
}

.ms-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ms-row > .v-icon {
  flex-shrink: 0;
}

.ms-select {
  flex: 1;
  min-width: 0;
}

.ms-select :deep(.v-field),
.ms-textarea :deep(.v-field) {
  border-radius: 8px !important;
  box-shadow: none !important;
}

.ms-row-label {
  font-size: 11.5px;
  font-weight: 600;
  color: #94a3b8;
  flex-shrink: 0;
}

.ms-weight {
  border-radius: 8px;
}

.ms-weight :deep(.v-btn) {
  min-width: 48px !important;
  padding: 0 12px !important;
  height: 28px !important;
  font-size: 12px !important;
  text-transform: none !important;
  letter-spacing: 0 !important;
}

.ms-switch {
  flex: 0 0 auto;
}

.ms-switch :deep(.v-selection-control) {
  min-height: auto;
}

.ms-slider {
  flex: 1;
  min-width: 0;
}

.ms-slider :deep(.v-input__control) {
  min-height: 20px;
}

.ms-op-value {
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
  width: 34px;
  text-align: right;
  flex-shrink: 0;
  font-variant-numeric: tabular-nums;
}

.ms-swatch {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  border: 1.5px solid rgba(0, 0, 0, 0.15);
  flex-shrink: 0;
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.15s;
}

.ms-swatch:hover {
  transform: scale(1.1);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.ms-hex {
  font-size: 11.5px;
  font-weight: 500;
  color: #475569;
  font-family: 'SF Mono', 'Cascadia Code', monospace;
}

.ms-size-input {
  width: 72px;
  flex-shrink: 0;
}

.ms-size-input :deep(.v-field) {
  border-radius: 8px !important;
  box-shadow: none !important;
}

.ms-size-input :deep(.v-field__input) {
  font-size: 12px !important;
  padding: 4px 8px !important;
  min-height: auto !important;
  text-align: center;
}

.ms-empty-inline {
  font-size: 11px;
  color: #f59e0b;
}

.ms-empty-block {
  flex: 1;
  min-height: 90px;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  font-size: 12px;
  color: #94a3b8;
  border: 1px dashed rgba(0, 0, 0, 0.12);
  border-radius: 10px;
  background: #f8fafc;
  padding: 8px;
}

/* ---- image grid ---- */
.ms-image-grid {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 6px;
  overflow-y: auto;
  padding: 2px;
  overscroll-behavior: contain;
}

.ms-image-card {
  position: relative;
  aspect-ratio: 1;
  padding: 0;
  border: 2px solid transparent;
  border-radius: 9px;
  background: #f1f5f9;
  cursor: pointer;
  overflow: hidden;
  opacity: 0.6;
  transition: opacity 0.15s, border-color 0.15s, box-shadow 0.15s;
}

.ms-image-card img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.ms-image-card:hover {
  opacity: 0.9;
}

.ms-image-card.selected {
  opacity: 1;
  border-color: #4f8cff;
  box-shadow: 0 0 0 2px rgba(79, 140, 255, 0.22);
}

.ms-check-badge {
  position: absolute;
  top: 3px;
  right: 3px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #4f8cff;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 1px 4px rgba(79, 140, 255, 0.4);
}

/* ---- size presets ---- */
.ms-size-presets {
  display: flex;
  gap: 6px;
}

.ms-size-chip {
  flex: 1;
  height: 26px;
  border: 1.5px solid #e2e8f0;
  background: #fff;
  border-radius: 13px;
  font-size: 11.5px;
  font-weight: 500;
  color: #64748b;
  cursor: pointer;
  transition: all 0.15s;
}

.ms-size-chip:hover {
  border-color: #4f8cff;
  color: #4f8cff;
}

.ms-size-chip.active {
  background: linear-gradient(135deg, #4f8cff, #6366f1);
  border-color: #4f8cff;
  color: #fff;
  font-weight: 600;
}

/* ---- icon picker ---- */
.ms-group-chips {
  flex-shrink: 0;
}

.ms-group-chips :deep(.v-chip) {
  margin-inline-end: 4px;
  margin-block: 0 2px;
}

.ms-icon-grid {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 4px;
  overflow-y: auto;
  padding: 2px;
  overscroll-behavior: contain;
}

.ms-icon-cell {
  padding: 0;
  border: 1.5px solid transparent;
  border-radius: 8px;
  background: #f8fafc;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 34px;
  transition: all 0.12s;
}

.ms-icon-cell:hover {
  background: #f1f5f9;
  border-color: rgba(79, 140, 255, 0.25);
}

.ms-icon-cell.selected {
  background: linear-gradient(135deg, rgba(79, 140, 255, 0.1), rgba(108, 92, 231, 0.06));
  border-color: rgba(79, 140, 255, 0.4);
}

.ms-icon-char {
  font-family: "Segoe UI Symbol", "Segoe UI Emoji", sans-serif;
  font-size: 18px;
  line-height: 1;
}

/* ---- image preview ---- */
.ms-img-box {
  width: 72px;
  height: 72px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background:
    conic-gradient(#eef2f7 0 25%, #fff 0 50%, #eef2f7 0 75%, #fff 0) 0 0 / 12px 12px;
  border: 1px solid rgba(0, 0, 0, 0.08);
}

.ms-img-box img {
  width: 100%;
  height: 100%;
}

.ms-img-empty {
  font-size: 10.5px;
  color: #94a3b8;
  background: rgba(255, 255, 255, 0.85);
  padding: 2px 6px;
  border-radius: 6px;
}

/* ---- preview ---- */
.ms-preview {
  flex-shrink: 0;
  padding: 10px;
  border-radius: 10px;
  background: linear-gradient(135deg, #f8fafc 0%, #eef2ff 100%);
  border: 1px solid rgba(79, 140, 255, 0.12);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  min-height: 56px;
  justify-content: center;
}

.ms-preview-label {
  font-size: 9.5px;
  font-weight: 600;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.ms-preview-text {
  max-width: 100%;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.ms-preview-icon {
  font-family: "Segoe UI Symbol", "Segoe UI Emoji", sans-serif;
  line-height: 1;
}
</style>
