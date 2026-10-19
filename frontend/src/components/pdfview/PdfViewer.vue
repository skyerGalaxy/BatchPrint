<template>
  <div class="pdf-container" ref="pdfContainerRef">
    <div v-for="pageIndex in pdfPages" :key="pageIndex" class="pdf-page-wrapper">
      <canvas
        :id="pdfCanvasId(pageIndex)"
        class="pdf-page"
      />
      <canvas
        :id="overlayCanvasId(pageIndex)"
        class="overlay-canvas"
        :class="{ 'overlay-canvas--readonly': isPreview, 'overlay-canvas--dragging': isDragging }"
        @mousemove="onCanvasMouseMove($event, pageIndex)"
        @mouseleave="onCanvasMouseLeave"
        @mousedown="onCanvasMouseDown($event, pageIndex)"
        @mouseup="onCanvasMouseUp"
        @contextmenu.prevent="onCanvasContextMenu($event, pageIndex)"
        @dragenter.prevent="onCanvasDragEnter"
        @dragover.prevent="onCanvasDragOver"
        @drop.prevent="onCanvasDrop($event, pageIndex)"
      />
    </div>
  </div>
  <LocationDialog
    v-model:dialog="dialog"
    :page-index="indexOfPage"
    :pointer="{ clientX: pointer_x, clientY: pointer_y }"
    :initial-panel="dialogPanel"
    :initial-icon="dialogIcon"
  />

  <!-- 悬浮在材料上时的信息提示 -->
  <div
    v-if="hoverInfo"
    class="icon-tooltip"
    :style="{ left: hoverPos.x + 'px', top: hoverPos.y + 'px' }"
  >
    <div class="icon-tooltip-head">
      <span class="icon-tooltip-chip" :style="{ backgroundColor: hoverInfo.color }">
        {{ hoverInfo.label }}
      </span>
      <span v-if="hoverInfo.content" class="icon-tooltip-content">{{ hoverInfo.content }}</span>
    </div>
    <div v-if="hoverInfo.conditions" class="icon-tooltip-cond">
      <span class="icon-tooltip-cond-tag">条件</span>
      <span class="icon-tooltip-cond-text">{{ hoverInfo.conditions }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import * as PDFJS from "pdfjs-dist";
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from "vue";
import { useBPStore } from '@/stores/bpstore';
import LocationDialog from "./LocationDialog.vue";
import { loadCustomFonts } from '@/utils/fontLoader';
import { jitterConfig, loadJitterConfig, drawJitterText } from '@/utils/fontJitter';
import type { StoreIcon, Condition as IconCondition, IconOption, MaterialKind } from '@/types/icon';


PDFJS.GlobalWorkerOptions.workerSrc = new URL(
    "pdfjs-dist/build/pdf.worker.mjs",
    import.meta.url
  ).toString();

// Props：外部传入 PDF 文件路径；preview 用于「历史快照」只读预览
const props = defineProps<{
  pdfSrc: string
  /** 只读快照预览：提供当时的材料与缩放；fieldNames/excelContent 用于显示字段真实取值 */
  preview?: {
    icons: StoreIcon[]
    scale: number
    fieldNames?: string[]
    excelContent?: any[][]
  } | null
}>()

// refs 与状态变量
let pdfDoc: any = null;
const pdfPages = ref(0);
const pdfScale = ref(props.preview?.scale ?? 2); // 控制清晰度
const pdfContainerRef = ref<HTMLElement | null>(null);

/** 只读快照预览模式 */
const isPreview = computed(() => !!props.preview);

// 每个实例使用独立 id 前缀：历史快照预览会与主预览同时挂载，
// 若沿用固定 id，document.getElementById 会取到另一个实例的 canvas。
const canvasUid = `pdfview-${Math.random().toString(36).slice(2, 8)}`;
const pdfCanvasId = (page: number) => `${canvasUid}-pdf-${page}`;
const overlayCanvasId = (page: number) => `${canvasUid}-overlay-${page}`;

const indexOfPage = ref(1);
const pointer_x = ref(0);
const pointer_y = ref(0);
const dialogPanel = ref<'table' | 'signature' | 'seal' | 'icon' | 'text'>('table');
/** 双击编辑时传入的已有材料；右键空白新增时为 null */
const dialogIcon = ref<StoreIcon | null>(null);

const dialog = ref(false);

const bpStore = useBPStore();

const icons = ref<StoreIcon[]>([]);
const selectedIcon = ref<StoreIcon | null>(null);
const isDragging = ref(false);
const isResizing = ref(false);
const isRotating = ref(false);
const dragOffset = ref({ x: 0, y: 0 });
const resizeStartSize = ref(0);
const resizeStartDist = ref(0);
const resizeIcon = ref<StoreIcon | null>(null);
const rotateIcon = ref<StoreIcon | null>(null);
const rotateStartAngle = ref(0);
const rotateStartRotation = ref(0);
const imageCache = new Map<string, HTMLImageElement>();

const copiedIcon = ref<StoreIcon | null>(null);
const lastMouseCoords = ref({ x: 0, y: 0 });
const lastMousePageIndex = ref(1);

// ---- 命中判定 / 重叠循环选择 ----
// 命中容差：在真实可见边界外再放宽一点，保证小图标也好点中
const HIT_TOLERANCE = 5;
// 区分「点击」与「拖动」的位移阈值，超过则视为拖动
const DRAG_MOVE_THRESHOLD = 3;
// 判定「同一位置重复点击」的距离阈值，用于重叠循环选择
const CLICK_SAME_POINT = 4;
let dragStartPoint: { x: number; y: number } | null = null;
let dragMoved = false;
// 上一次点击的位置与所选图标：只有原地再次点击才切到下一层
let lastClickPoint: { x: number; y: number } | null = null;
let lastClickedIconId: number | null = null;

// ---- 悬浮提示：鼠标停靠在材料上时显示类型/字段/条件 ----
const hoveredIcon = ref<StoreIcon | null>(null);
const hoverPos = ref({ x: 0, y: 0 });

const BTN_R = 10;
const BTN_PAD = 5;
const HIT_PAD = 4;

// 加载 PDF 文件
const loadFile = (url: string) => {
  const loadingTask = PDFJS.getDocument(url);
  loadingTask.promise
    .then(async (pdf: any) => {
      pdfDoc = pdf;
      pdfPages.value = pdf.numPages;
      await nextTick();
      loadIconsFromStore(); // 加载存储的 icon
      renderPage(1);
    })
    .catch((error: any) => {
      console.warn(`[PdfViewer] loadFile error: ${error}`);
    });
};

// 渲染每一页
const renderPage = (num: number) => {
  pdfDoc.getPage(num).then((page: any) => {
    const canvas: HTMLCanvasElement | null = document.getElementById(pdfCanvasId(num)) as HTMLCanvasElement;
    if (!canvas) return;

    const ctx = canvas.getContext("2d")!;
    const viewport = page.getViewport({ scale: pdfScale.value });

    // 获取容器宽度（决定显示大小）
    const containerWidth = pdfContainerRef.value?.clientWidth || 800;
    const pageRatio = viewport.width / viewport.height;

    const maxDisplayWidth = pageRatio > 1
      ? Math.min(containerWidth * 0.95, 1300)
      : Math.min(containerWidth * 0.9, 900);

    const displayWidth = maxDisplayWidth;
    const displayHeight = displayWidth / pageRatio;

    canvas.width = viewport.width;
    canvas.height = viewport.height;
    canvas.style.width = `${displayWidth}px`;
    canvas.style.height = `${displayHeight}px`;

    // 渲染
    page.render({
      canvasContext: ctx,
      viewport,
    });

    // 初始化 overlay canvas
    const overlayCanvas: HTMLCanvasElement | null = document.getElementById(overlayCanvasId(num)) as HTMLCanvasElement;
    if (overlayCanvas) {
      overlayCanvas.width = viewport.width;
      overlayCanvas.height = viewport.height;
      overlayCanvas.style.width = `${displayWidth}px`;
      overlayCanvas.style.height = `${displayHeight}px`;
      redrawIcons(num);
    }

    // 渲染下一页
    if (num < pdfPages.value) {
      renderPage(num + 1);
    }
  });
};

function onCanvasDragEnter(e: DragEvent) {
  // dragenter 也需要 preventDefault 才能在部分 WebView2 版本中允许 drop
  if (e.dataTransfer) {
    e.dataTransfer.dropEffect = 'copy';
  }
}

function onCanvasDragOver(e: DragEvent) {
  if (e.dataTransfer) {
    // 只要是我们自定义的拖拽数据，就允许放置
    if (e.dataTransfer.types?.includes('application/x-batchprint-option')) {
      e.dataTransfer.dropEffect = 'copy';
    }
  }
}

function onCanvasDrop(e: DragEvent, pageIndex: number) {
  if (isPreview.value) return;
  const raw = e.dataTransfer?.getData('application/x-batchprint-option');
  if (!raw) return;

  try {
    const payload = JSON.parse(raw) as { option?: IconOption; panel?: string };
    if (!payload.option) return;
    // 同类型材料沿用上次确认的样式（载荷仅提供身份字段；文本预设自带样式）
    const kind = (payload.panel || 'table') as MaterialKind;
    const option = bpStore.instantiateOption(kind, payload.option);
    const canvas = document.getElementById(overlayCanvasId(pageIndex)) as HTMLCanvasElement | null;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left) * (canvas.width / rect.width);
    const y = (e.clientY - rect.top) * (canvas.height / rect.height);

    // 拖放即落库：直接加入 iconList，字段类型渲染时自动取 Excel 对应字段的值
    const maxId = icons.value.reduce((max, i) => Math.max(max, i.id), 0);
    const size = option.size ?? 120;
    const newIcon: StoreIcon = {
      id: maxId + 1,
      pageIndex,
      pointer: { clientX: x, clientY: y },
      mode: 'single',
      option: { ...option, size },
      size,
      scale: bpStore.pdfScale,
    };

    bpStore.iconList.push(newIcon);
    icons.value = bpStore.iconList as StoreIcon[];
    selectedIcon.value = newIcon;
    redrawIcons(pageIndex);
  } catch (error) {
    console.error('处理材料拖放失败:', error);
  }
}


const loadIconsFromStore = () => {
  if (isPreview.value) {
    icons.value = (props.preview?.icons ?? []) as StoreIcon[];
    return;
  }
  if (bpStore.iconList && bpStore.iconList.length > 0) {
    icons.value = bpStore.iconList as StoreIcon[];
  } else {
    icons.value = [];
  }
};

function getIconSize(icon: StoreIcon) {
  return icon.size ?? 40;
}

// 获取鼠标在 canvas 上的坐标（考虑样式缩放）
function getCanvasCoordinates(e: MouseEvent, pageIndex: number) {
  const canvas = document.getElementById(overlayCanvasId(pageIndex)) as HTMLCanvasElement | null;
  if (!canvas) return { x: 0, y: 0 };

  const rect = canvas.getBoundingClientRect();
  const x = (e.clientX - rect.left) * (canvas.width / rect.width);
  const y = (e.clientY - rect.top) * (canvas.height / rect.height);
  return { x, y };
}

// 检查鼠标是否在某个 icon 内：用真实可见边界（含旋转）判定，而非 size 正方形
function isPointInIcon(point: { x: number; y: number }, icon: StoreIcon) {
  const { halfW, halfH } = getIconBounds(icon);
  const dx = point.x - icon.pointer.clientX;
  const dy = point.y - icon.pointer.clientY;
  // 反向旋转到图标本地坐标（与 hitCornerButton / 绘制时的 rotate 约定一致）
  const rot = -(icon.rotation ?? 0) * Math.PI / 180;
  const lx = dx * Math.cos(rot) - dy * Math.sin(rot);
  const ly = dx * Math.sin(rot) + dy * Math.cos(rot);
  return Math.abs(lx) <= halfW + HIT_TOLERANCE && Math.abs(ly) <= halfH + HIT_TOLERANCE;
}

// 返回该点命中的所有 icon，最上层优先（与绘制顺序相反），用于选择与重叠循环
function hitTestIcons(point: { x: number; y: number }, pageIndex: number): StoreIcon[] {
  const list = icons.value.filter(icon => icon.pageIndex === pageIndex);
  const hits: StoreIcon[] = [];
  for (let i = list.length - 1; i >= 0; i -= 1) {
    if (isPointInIcon(point, list[i])) hits.push(list[i]);
  }
  return hits;
}

function hitCornerButton(point: { x: number; y: number }, icon: StoreIcon): 'delete' | 'rotate' | 'resize' | null {
  const bounds = getIconBounds(icon);
  const dx = point.x - icon.pointer.clientX;
  const dy = point.y - icon.pointer.clientY;
  const rot = -(icon.rotation ?? 0) * Math.PI / 180;
  const rx = dx * Math.cos(rot) - dy * Math.sin(rot);
  const ry = dx * Math.sin(rot) + dy * Math.cos(rot);

  const hw = bounds.halfW + BTN_PAD + BTN_R;
  const hh = bounds.halfH + BTN_PAD + BTN_R;
  const checkR = BTN_R + HIT_PAD;

  if ((rx + hw) ** 2 + (ry + hh) ** 2 <= checkR ** 2) return 'delete';
  if ((rx - hw) ** 2 + (ry + hh) ** 2 <= checkR ** 2) return 'rotate';
  if ((rx - hw) ** 2 + (ry - hh) ** 2 <= checkR ** 2) return 'resize';
  return null;
}

// 由 icon.option 反推材料类型，用于缩放后按类型记忆尺寸
function iconMaterialKind(option: IconOption): MaterialKind {
  switch (option.type) {
    case 'field': return 'table';
    case 'image': return option.imageKind === 'seal' ? 'seal' : 'signature';
    case 'icon': return 'icon';
    case 'text': return 'text';
  }
}

// 缩放过程中防抖落盘：避免每次 mousemove 都写 store
let resizeSaveTimer: ReturnType<typeof setTimeout> | null = null;
const RESIZE_SAVE_DEBOUNCE = 500;

function scheduleResizeSave(icon: StoreIcon) {
  if (resizeSaveTimer) clearTimeout(resizeSaveTimer);
  resizeSaveTimer = setTimeout(() => {
    const kind = iconMaterialKind(icon.option);
    void bpStore.saveMaterialStyle(kind, { size: icon.size });
    resizeSaveTimer = null;
  }, RESIZE_SAVE_DEBOUNCE);
}

function onCanvasMouseMove(e: MouseEvent, pageIndex: number) {
  if (isPreview.value) return;
  const coords = getCanvasCoordinates(e, pageIndex);
  lastMouseCoords.value = coords;
  lastMousePageIndex.value = pageIndex;

  // 未处于拖动/缩放/旋转时，更新悬浮提示（命中用同一套真实边界判定）
  if (!isDragging.value && !isResizing.value && !isRotating.value) {
    const top = hitTestIcons(coords, pageIndex)[0] ?? null;
    hoveredIcon.value = top;
    if (top) {
      hoverPos.value = {
        x: Math.max(8, Math.min(e.clientX + 16, window.innerWidth - 336)),
        y: Math.max(8, Math.min(e.clientY + 18, window.innerHeight - 96)),
      };
    }
  } else {
    hoveredIcon.value = null;
  }

  if (isRotating.value && rotateIcon.value) {
    const dx = coords.x - rotateIcon.value.pointer.clientX;
    const dy = coords.y - rotateIcon.value.pointer.clientY;
    const currentAngle = Math.atan2(dy, dx);
    const delta = currentAngle - rotateStartAngle.value;
    rotateIcon.value.rotation = rotateStartRotation.value + delta * 180 / Math.PI;
    redrawIcons(pageIndex);
    return;
  }

  if (isResizing.value && resizeIcon.value) {
    const dist = Math.sqrt(
      Math.pow(coords.x - resizeIcon.value.pointer.clientX, 2) +
      Math.pow(coords.y - resizeIcon.value.pointer.clientY, 2)
    );
    const newSize = Math.max(20, resizeStartSize.value + (dist - resizeStartDist.value) * 2);
    // 顶层 size 与 option.size 同步：前者用于画布渲染/后端生成，后者用于弹窗回显与确认
    resizeIcon.value.size = newSize;
    resizeIcon.value.option.size = newSize;
    redrawIcons(pageIndex);
    // 防抖写入同类型样式记忆，新拖入的同类材料沿用该尺寸
    scheduleResizeSave(resizeIcon.value);
    return;
  }

  if (isDragging.value && selectedIcon.value) {
    if (dragStartPoint) {
      const moved = Math.hypot(coords.x - dragStartPoint.x, coords.y - dragStartPoint.y);
      if (moved > DRAG_MOVE_THRESHOLD) dragMoved = true;
    }
    selectedIcon.value.pointer.clientX = coords.x - dragOffset.value.x;
    selectedIcon.value.pointer.clientY = coords.y - dragOffset.value.y;
    redrawIcons(pageIndex);
    return;
  }
}

function onCanvasMouseLeave() {
  // selection persists, no auto-deselect
  hoveredIcon.value = null;
}

function onCanvasMouseDown(e: MouseEvent, pageIndex: number) {
  if (isPreview.value) return;
  const coords = getCanvasCoordinates(e, pageIndex);
  dragStartPoint = { x: coords.x, y: coords.y };
  dragMoved = false;
  // 开始交互时先收起悬浮提示，避免与拖动/操作叠加
  hoveredIcon.value = null;

  const sel = selectedIcon.value;
  if (sel && sel.pageIndex === pageIndex) {
    const action = hitCornerButton(coords, sel);
    if (action === 'delete') {
      deleteIcon(sel);
      return;
    }
    if (action === 'rotate') {
      isRotating.value = true;
      rotateIcon.value = sel;
      rotateStartRotation.value = sel.rotation ?? 0;
      const dx = coords.x - sel.pointer.clientX;
      const dy = coords.y - sel.pointer.clientY;
      rotateStartAngle.value = Math.atan2(dy, dx);
      return;
    }
    if (action === 'resize') {
      isResizing.value = true;
      resizeIcon.value = sel;
      resizeStartSize.value = getIconSize(sel);
      resizeStartDist.value = Math.sqrt(
        Math.pow(coords.x - sel.pointer.clientX, 2) +
        Math.pow(coords.y - sel.pointer.clientY, 2)
      );
      return;
    }
    if (isPointInIcon(coords, sel)) {
      isDragging.value = true;
      dragOffset.value = { x: coords.x - sel.pointer.clientX, y: coords.y - sel.pointer.clientY };
      return;
    }
  }

  // 取最上层（视觉最前面）的命中项
  const hits = hitTestIcons(coords, pageIndex);
  if (hits.length > 0) {
    const target = hits[0];
    selectedIcon.value = target;
    isDragging.value = true;
    dragOffset.value = { x: coords.x - target.pointer.clientX, y: coords.y - target.pointer.clientY };
    redrawIcons(pageIndex);
    return;
  }

  // 空点：取消选择，并清掉循环点击的状态
  selectedIcon.value = null;
  lastClickPoint = null;
  lastClickedIconId = null;
  redrawIcons(pageIndex);
}

function onCanvasMouseUp() {
  // 缩放结束时立即落盘，不等防抖
  if (isResizing.value && resizeIcon.value) {
    if (resizeSaveTimer) {
      clearTimeout(resizeSaveTimer);
      resizeSaveTimer = null;
    }
    const icon = resizeIcon.value;
    const kind = iconMaterialKind(icon.option);
    void bpStore.saveMaterialStyle(kind, { size: icon.size });
  }

  // 未发生位移的点击 = 选择操作：
  // 首次点击选中上层；在「同一位置」再次点击才切到下一层（重叠循环）
  const isClick = isDragging.value && !dragMoved && dragStartPoint !== null;
  if (isClick && selectedIcon.value) {
    const point = dragStartPoint!;
    const samePoint = lastClickPoint !== null
      && Math.hypot(point.x - lastClickPoint.x, point.y - lastClickPoint.y) <= CLICK_SAME_POINT;
    const hits = hitTestIcons(point, selectedIcon.value.pageIndex);
    const idx = hits.indexOf(selectedIcon.value);
    if (samePoint && lastClickedIconId === selectedIcon.value.id && idx >= 0 && hits.length > 1) {
      selectedIcon.value = hits[(idx + 1) % hits.length];
      redrawIcons(selectedIcon.value.pageIndex);
    }
    lastClickPoint = { x: point.x, y: point.y };
    lastClickedIconId = selectedIcon.value.id;
  } else {
    // 拖动 / 缩放 / 旋转 / 空点：结束一轮点击，重置循环状态
    lastClickPoint = null;
    lastClickedIconId = null;
  }

  isDragging.value = false;
  isResizing.value = false;
  isRotating.value = false;
  resizeIcon.value = null;
  rotateIcon.value = null;
  dragStartPoint = null;
  dragMoved = false;
}

// 右键单击 icon 时打开设置弹窗
function onCanvasContextMenu(e: MouseEvent, pageIndex: number) {
  if (isPreview.value) return;
  const coords = getCanvasCoordinates(e, pageIndex);
  const hits = hitTestIcons(coords, pageIndex);
  if (hits.length > 0) {
    selectedIcon.value = hits[0];
    redrawIcons(pageIndex);
    openLocationDialog(hits[0]);
  }
}

function openLocationDialog(icon: StoreIcon) {
  indexOfPage.value = icon.pageIndex;
  pointer_x.value = icon.pointer.clientX;
  pointer_y.value = icon.pointer.clientY;
  dialogIcon.value = icon;
  dialog.value = true;
}

function handleKeyDown(e: KeyboardEvent) {
  if (!selectedIcon.value) return;

  if (e.ctrlKey && e.key === 'c') {
    e.preventDefault();
    copiedIcon.value = JSON.parse(JSON.stringify(selectedIcon.value));
  }

  if (e.ctrlKey && e.key === 'v') {
    e.preventDefault();
    if (!copiedIcon.value) return;
    const clone = JSON.parse(JSON.stringify(copiedIcon.value)) as StoreIcon;
    const maxId = icons.value.reduce((max, i) => Math.max(max, i.id), 0);
    clone.id = maxId + 1;
    const offsetX = lastMouseCoords.value.x - clone.pointer.clientX;
    const offsetY = lastMouseCoords.value.y - clone.pointer.clientY;
    if (Math.abs(offsetX) < 5 && Math.abs(offsetY) < 5) {
      clone.pointer.clientX += 30;
      clone.pointer.clientY += 30;
    } else {
      clone.pointer.clientX = lastMouseCoords.value.x;
      clone.pointer.clientY = lastMouseCoords.value.y;
    }
    clone.pageIndex = lastMousePageIndex.value;
    clone.scale = bpStore.pdfScale;
    icons.value.push(clone);
    selectedIcon.value = clone;
    redrawIcons(clone.pageIndex);
  }
}

// 删除 icon
function deleteIcon(icon: StoreIcon) {
  const index = icons.value.indexOf(icon);
  if (index > -1) {
    icons.value.splice(index, 1);
    redrawIcons(icon.pageIndex);
  }
  if (selectedIcon.value === icon) selectedIcon.value = null;
  if (hoveredIcon.value === icon) hoveredIcon.value = null;
}

// 重新绘制 overlay canvas 上的 icon
function redrawIcons(pageIndex: number) {
  const canvas = document.getElementById(overlayCanvasId(pageIndex)) as HTMLCanvasElement | null;
  if (!canvas) return;

  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  // 清空 overlay canvas
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  const pageIcons = icons.value.filter(icon => icon.pageIndex === pageIndex);
  // 先画未选中的，最后画选中项：保证选中框与角按钮始终在最上层，不被其它图标盖住
  for (const icon of pageIcons) {
    if (icon !== selectedIcon.value) drawIcon(ctx, icon, false);
  }
  if (selectedIcon.value && pageIcons.includes(selectedIcon.value)) {
    drawIcon(ctx, selectedIcon.value, true);
  }
}

function redrawAllPages() {
  for (let i = 1; i <= pdfPages.value; i += 1) {
    redrawIcons(i);
  }
}

// 辅助函数：获取字段值
function getFieldValue(fieldName: string): string {
  if (!fieldName) return '';
  // 只读快照预览：优先用外部传入的表格显示真实取值
  if (isPreview.value) {
    const fieldNames = props.preview?.fieldNames;
    const content = props.preview?.excelContent;
    if (!fieldNames || !content?.length) return `{${fieldName}}`;
    const columnIndex = fieldNames.indexOf(fieldName);
    if (columnIndex === -1) return `{${fieldName}}`;
    return String(content[0][columnIndex] ?? '');
  }
  if (!bpStore.fieldNames || !bpStore.excelContent?.length) {
    return '';
  }
  const columnIndex = bpStore.fieldNames.indexOf(fieldName);
  if (columnIndex === -1) return '';
  return String(bpStore.excelContent[0][columnIndex] || '');
}

// 辅助函数：绘制字段文本
function drawFieldText(ctx: CanvasRenderingContext2D, fieldName: string, fontFamily: string, fontSize: number, fontWeight: number, italic: boolean, opacity: number, color: string, x: number, y: number): void {
  const fieldValue = getFieldValue(fieldName);
  ctx.globalAlpha = opacity;
  ctx.fillStyle = color;
  ctx.font = `${italic ? 'italic ' : ''}${fontWeight} ${fontSize}px "${fontFamily}"`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(fieldValue, x, y);
  ctx.globalAlpha = 1;
}

// 辅助函数：圆角矩形路径
function roundedRectPath(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number): void {
  const rr = Math.min(r, w / 2, h / 2);
  ctx.beginPath();
  ctx.moveTo(x + rr, y);
  ctx.lineTo(x + w - rr, y);
  ctx.arcTo(x + w, y, x + w, y + rr, rr);
  ctx.lineTo(x + w, y + h - rr);
  ctx.arcTo(x + w, y + h, x + w - rr, y + h, rr);
  ctx.lineTo(x + rr, y + h);
  ctx.arcTo(x, y + h, x, y + h - rr, rr);
  ctx.lineTo(x, y + rr);
  ctx.arcTo(x, y, x + rr, y, rr);
  ctx.closePath();
}

// 辅助函数：绘制图片（支持透明度 / 圆角 / 印章拉伸）
function drawImageIcon(ctx: CanvasRenderingContext2D, icon: StoreIcon, x: number, y: number, size: number): void {
  const imgSrc = icon.option.src || '';
  if (!imgSrc) return;

  let img = imageCache.get(imgSrc);
  if (!img) {
    img = new Image();
    img.src = imgSrc;
    imageCache.set(imgSrc, img);
    // 仅在首次加载完成时重绘该页（避免多个图片加载时重复重绘）
    img.onload = () => {
      redrawIcons(icon.pageIndex);
    };
  }

  if (img.complete && img.width && img.height) {
    // 印章未锁定纵横比时拉伸填满正方形区域，其余保持原始比例
    const stretch = icon.option.imageKind === 'seal' && icon.option.keepRatio === false;
    const imgRatio = img.width / img.height;
    const drawWidth = stretch ? size : (imgRatio > 1 ? size : size * imgRatio);
    const drawHeight = stretch ? size : (imgRatio > 1 ? size / imgRatio : size);

    // 圆角：短边尺寸的百分比
    const radius = ((icon.option.cornerRadius ?? 0) / 100) * Math.min(drawWidth, drawHeight);

    ctx.save();
    ctx.globalAlpha = icon.option.opacity ?? 1;
    if (radius > 0) {
      roundedRectPath(ctx, x - drawWidth / 2, y - drawHeight / 2, drawWidth, drawHeight, radius);
      ctx.clip();
    }
    ctx.drawImage(img, x - drawWidth / 2, y - drawHeight / 2, drawWidth, drawHeight);
    ctx.restore();
  }
}

function checkConditionFlat(cond: IconCondition): boolean {
  const fieldValue = getFieldValue(cond.field || '');
  switch (cond.op) {
    case '等于': return fieldValue === cond.value;
    case '不等于': return fieldValue !== cond.value;
    case '包含': return fieldValue.includes(cond.value);
    case '不包含': return !fieldValue.includes(cond.value);
    case '为空': return !fieldValue;
    case '不为空': return !!fieldValue;
    default: return false;
  }
}

function checkConditions(condArr: IconCondition[] | undefined, matchMode: string | undefined): boolean {
  if (!condArr?.length) return true;
  return matchMode === '所有' ? condArr.every(checkConditionFlat) : condArr.some(checkConditionFlat);
}

function checkIconConditions(icon: StoreIcon): boolean {
  if (!icon.conditions && !icon.groups) return true;

  if (icon.logicType === 'advanced' && icon.groups?.length) {
    const groupResults = icon.groups.map(g => checkConditions(g.conditions, g.matchMode));
    let result = groupResults[0];
    const connectors = icon.groupConnectors || [];
    for (let i = 0; i < connectors.length; i++) {
      if (connectors[i] === '所有') {
        result = result && groupResults[i + 1];
      } else {
        result = result || groupResults[i + 1];
      }
    }
    return result;
  }

  return checkConditions(icon.conditions, icon.matchMode);
}

// 把条件表达式整理成可读文本，用于悬浮提示
function describeConditions(icon: StoreIcon): string {
  const fmt = (c: IconCondition) => {
    const field = c.field || '字段';
    if (c.op === '为空' || c.op === '不为空') return `${field} ${c.op}`;
    return `${field} ${c.op} ${c.value ?? ''}`.trim();
  };
  if (icon.logicType === 'advanced' && icon.groups?.length) {
    const connectors = icon.groupConnectors || [];
    return icon.groups
      .map((g, i) => {
        const inner = g.conditions.map(fmt).join(g.matchMode === '任一' ? ' 或 ' : ' 且 ');
        const wrapped = g.conditions.length > 1 ? `(${inner})` : inner;
        return i === 0 ? wrapped : `${connectors[i - 1] ?? '且'} ${wrapped}`;
      })
      .join(' ');
  }
  const mode = icon.matchMode === '任一' ? ' 或 ' : ' 且 ';
  return (icon.conditions || []).map(fmt).join(mode);
}

// 悬浮提示的展示信息：常规只显示类型/字段，条件字段额外显示条件
const hoverInfo = computed(() => {
  const icon = hoveredIcon.value;
  if (!icon) return null;
  let label = '材料';
  let color = '#64748b';
  let content = '';
  switch (icon.option.type) {
    case 'field':
      label = '字段';
      color = '#2563eb';
      content = icon.option.fieldName || '未命名';
      break;
    case 'text':
      label = '文本';
      color = '#db2777';
      content = icon.option.text || '';
      break;
    case 'icon':
      label = '图标';
      color = '#7c3aed';
      content = icon.option.icon || '';
      break;
    case 'image':
      if (icon.option.imageKind === 'seal') {
        label = '印章';
        color = '#dc2626';
      } else {
        label = '签字';
        color = '#059669';
      }
      break;
  }
  const conditions = icon.mode === 'conditional' ? describeConditions(icon) : '';
  return { label, color, content, conditions };
});

function getIconBounds(icon: StoreIcon): { halfW: number; halfH: number } {
  const s = getIconSize(icon);
  if (icon.option.type === 'field') {
    const fontFamily = icon.option.fontFamily || '楷体';
    const fontSize = Math.max(8, Math.floor(s * 0.3));
    const fieldValue = getFieldValue(icon.option.fieldName || '');
    const charCount = fieldValue.length || 1;
    const halfW = Math.max(14, Math.floor(fontSize * charCount * 0.45));
    const halfH = Math.max(8, Math.floor(fontSize * 0.5));
    return { halfW, halfH };
  }
  if (icon.option.type === 'text') {
    const fontSize = Math.max(8, Math.floor(s * 0.3));
    const textValue = icon.option.text || '';
    const charCount = textValue.length || 1;
    const halfW = Math.max(14, Math.floor(fontSize * charCount * 0.45));
    const halfH = Math.max(8, Math.floor(fontSize * 0.5));
    return { halfW, halfH };
  }
  if (icon.option.type === 'image') {
    return { halfW: s * 0.4, halfH: s * 0.4 };
  }
  return { halfW: s / 2, halfH: s / 2 };
}

function drawCornerButtons(ctx: CanvasRenderingContext2D, icon: StoreIcon, bounds: { halfW: number; halfH: number }) {
  const x = icon.pointer.clientX;
  const y = icon.pointer.clientY;
  const rotation = icon.rotation ?? 0;

  const hw = bounds.halfW + BTN_PAD + BTN_R;
  const hh = bounds.halfH + BTN_PAD + BTN_R;

  const tl = rotatePoint(-hw, -hh, rotation);
  const tr = rotatePoint(hw, -hh, rotation);
  const br = rotatePoint(hw, hh, rotation);

  const btns: { cx: number; cy: number; color: string; glyph: string }[] = [
    { cx: x + tl.x, cy: y + tl.y, color: '#ef4444', glyph: '\u2715' },
    { cx: x + tr.x, cy: y + tr.y, color: '#4f8cff', glyph: '\u21BB' },
    { cx: x + br.x, cy: y + br.y, color: '#10b981', glyph: '\u21C5' },
  ];

  for (const b of btns) {
    ctx.beginPath();
    ctx.arc(b.cx, b.cy, BTN_R, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(255,255,255,0.93)';
    ctx.shadowColor = 'rgba(0,0,0,0.15)';
    ctx.shadowBlur = 4;
    ctx.shadowOffsetX = 0;
    ctx.shadowOffsetY = 1;
    ctx.fill();
    ctx.shadowColor = 'transparent';
    ctx.shadowBlur = 0;
    ctx.shadowOffsetY = 0;
    ctx.strokeStyle = b.color;
    ctx.lineWidth = 2;
    ctx.stroke();

    ctx.fillStyle = b.color;
    ctx.font = `bold ${BTN_R - 1}px system-ui`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(b.glyph, b.cx, b.cy + 0.5);
  }
}

function rotatePoint(px: number, py: number, deg: number): { x: number; y: number } {
  if (!deg) return { x: px, y: py };
  const rad = deg * Math.PI / 180;
  const cos = Math.cos(rad), sin = Math.sin(rad);
  return { x: px * cos - py * sin, y: px * sin + py * cos };
}

function drawIcon(ctx: CanvasRenderingContext2D, icon: StoreIcon, isSelected: boolean) {
  const x = icon.pointer.clientX;
  const y = icon.pointer.clientY;
  const size = getIconSize(icon);
  const rotation = icon.rotation ?? 0;

  ctx.save();
  ctx.translate(x, y);
  if (rotation !== 0) ctx.rotate(rotation * Math.PI / 180);

  if (icon.option.type === 'field') {
    const fontFamily = icon.option.fontFamily || '楷体';
    const fontSize = Math.max(8, Math.floor(size * 0.3));
    const fontWeight = icon.option.fontWeight ?? 400;
    const italic = icon.option.italic ?? false;
    const baseOpacity = icon.option.opacity ?? 1;
    const color = icon.option.color ?? '#000000';

    if (icon.option.applyJitter !== false) {
      drawJitterText(ctx, getFieldValue(icon.option.fieldName || ''), {
        fontFamily, fontSize, fontWeight, italic, color, opacity: baseOpacity,
        seed: icon.id * 1000 + 11,
      });
    } else {
      drawFieldText(ctx,
        icon.option.fieldName || '',
        fontFamily,
        fontSize,
        fontWeight,
        italic,
        baseOpacity,
        color,
        0, 0
      );
    }
  } else if (icon.option.type === 'text') {
    const fontFamily = icon.option.fontFamily || '楷体';
    const fontSize = Math.max(8, Math.floor(size * 0.3));
    const fontWeight = icon.option.fontWeight ?? 400;
    const italic = icon.option.italic ?? false;
    const baseOpacity = icon.option.opacity ?? 1;
    const color = icon.option.color ?? '#000000';

    if (icon.option.applyJitter !== false) {
      drawJitterText(ctx, icon.option.text || '', {
        fontFamily, fontSize, fontWeight, italic, color, opacity: baseOpacity,
        seed: icon.id * 1000 + 22,
      });
    } else {
      ctx.globalAlpha = baseOpacity;
      ctx.fillStyle = color;
      ctx.font = `${italic ? 'italic ' : ''}${fontWeight} ${fontSize}px "${fontFamily}"`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(icon.option.text || '', 0, 0);
      ctx.globalAlpha = 1;
    }
  } else if (icon.option.type === 'image') {
    drawImageIcon(ctx, icon, 0, 0, size);
  } else if (icon.option.type === 'icon') {
    const iconFontSize = Math.max(12, Math.floor(size * 0.8));
    ctx.globalAlpha = icon.option.opacity ?? 1;
    ctx.fillStyle = icon.option.color ?? '#000000';
    ctx.font = `${iconFontSize}px "Segoe UI Symbol"`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(icon.option.icon || '', 0, 0);
    ctx.globalAlpha = 1;
  }

  ctx.restore();

  if (isSelected) {
    const bounds = getIconBounds(icon);
    if (rotation !== 0) {
      ctx.save();
      ctx.translate(x, y);
      ctx.rotate(rotation * Math.PI / 180);
      ctx.strokeStyle = 'rgba(79,140,255,0.35)';
      ctx.lineWidth = 1.5;
      ctx.setLineDash([5, 3]);
      ctx.strokeRect(-bounds.halfW - 2, -bounds.halfH - 2, (bounds.halfW + 2) * 2, (bounds.halfH + 2) * 2);
      ctx.setLineDash([]);
      ctx.restore();
    } else {
      ctx.strokeStyle = 'rgba(79,140,255,0.35)';
      ctx.lineWidth = 1.5;
      ctx.setLineDash([5, 3]);
      ctx.strokeRect(x - bounds.halfW - 2, y - bounds.halfH - 2, (bounds.halfW + 2) * 2, (bounds.halfH + 2) * 2);
      ctx.setLineDash([]);
    }

    drawCornerButtons(ctx, icon, bounds);
  }
}

// 初始化
onMounted(async () => {
  if (isPreview.value) {
    // 只读预览：加载字体/扰动配置用于绘制文字，但不写入 store，也不接管键盘
    await loadCustomFonts(bpStore.dataPath);
    await loadJitterConfig();
    loadFile(props.pdfSrc);
    loadIconsFromStore();
    return;
  }

  document.addEventListener('keydown', handleKeyDown);
  // 先加载自定义字体与扰动配置
  await loadCustomFonts(bpStore.dataPath);
  await loadJitterConfig();
  bpStore.pdfScale = pdfScale.value;
  
  // 然后加载 PDF
  loadFile(props.pdfSrc);
  loadIconsFromStore();
});

onUnmounted(() => {
  if (isPreview.value) return;
  document.removeEventListener('keydown', handleKeyDown);
});

// 扰动参数变化时实时重绘（设置页拖动滑动条 → PDF 文字即时更新）
watch(jitterConfig, () => redrawAllPages(), { deep: true });

// 当传入的 PDF 路径变化时重新加载
watch(
  () => props.pdfSrc,
  (newPdfSrc) => {
    pdfPages.value = 0;
    loadFile(newPdfSrc);
    loadIconsFromStore();
  }
);

watch(
  () => bpStore.iconList,
  () => {
    if (isPreview.value) return;
    loadIconsFromStore();
    redrawAllPages();
  },
  { deep: true }
);

// 只读预览：快照内容/缩放变化时同步重绘
watch(
  () => props.preview,
  (preview) => {
    if (!preview) return;
    pdfScale.value = preview.scale || 2;
    loadIconsFromStore();
    redrawAllPages();
  },
  { deep: true }
);
</script>

<style scoped>
.pdf-container {
  width: 100%;
  height: 100%;
  background-color: #f8f9fa;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px 0;
  box-sizing: border-box;
  overflow: visible;
}

/* 页面容器：居中显示 */
.pdf-page-wrapper {
  position: relative;
  width: fit-content;
  margin: 12px auto;
}

.pdf-page {
  display: block;
  background: white;
  box-shadow: 0 0 8px rgba(0, 0, 0, 0.15);
}

.overlay-canvas {
  position: absolute;
  top: 0;
  left: 0;
  cursor: default;
}

/* 仅在真正拖动材料时显示手形 */
.overlay-canvas--dragging {
  cursor: grabbing;
}

.overlay-canvas--readonly {
  pointer-events: none;
  cursor: default;
}

/* ---- 悬浮提示 ---- */
.icon-tooltip {
  position: fixed;
  z-index: 3000;
  pointer-events: none;
  max-width: 320px;
  padding: 8px 11px;
  border-radius: 10px;
  background: rgba(15, 23, 42, 0.94);
  color: #f8fafc;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.28);
  backdrop-filter: blur(6px);
  font-size: 12px;
  line-height: 1.5;
  animation: icon-tooltip-in 0.12s ease-out;
}

.icon-tooltip-head {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.icon-tooltip-chip {
  flex: none;
  padding: 1px 7px;
  border-radius: 999px;
  color: #fff;
  font-size: 11px;
  font-weight: 600;
  line-height: 1.6;
}

.icon-tooltip-content {
  font-weight: 600;
  letter-spacing: 0.2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.icon-tooltip-cond {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-top: 6px;
  padding-top: 6px;
  border-top: 1px solid rgba(255, 255, 255, 0.14);
  color: rgba(226, 232, 240, 0.92);
}

.icon-tooltip-cond-tag {
  flex: none;
  padding: 0 5px;
  border-radius: 4px;
  background: rgba(251, 191, 36, 0.22);
  color: #fcd34d;
  font-size: 10px;
  line-height: 1.7;
}

.icon-tooltip-cond-text {
  word-break: break-word;
}

@keyframes icon-tooltip-in {
  from {
    opacity: 0;
    transform: translateY(2px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
