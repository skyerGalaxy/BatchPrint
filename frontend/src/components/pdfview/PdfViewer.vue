<template>
  <div class="pdf-container" ref="pdfContainerRef">
    <div v-for="pageIndex in pdfPages" :key="pageIndex" class="pdf-page-wrapper">
      <canvas
        :id="`pdf-canvas-${pageIndex}`"
        class="pdf-page"
      />
      <canvas
        :id="`overlay-canvas-${pageIndex}`"
        class="overlay-canvas"
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
</template>

<script setup lang="ts">
import * as PDFJS from "pdfjs-dist";
import { ref, onMounted, onUnmounted, watch, nextTick } from "vue";
import { useBPStore } from '@/stores/bpstore';
import LocationDialog from "./LocationDialog.vue";
import { loadCustomFonts } from '@/utils/fontLoader';
import { jitterConfig, loadJitterConfig, drawJitterText } from '@/utils/fontJitter';
import type { StoreIcon, Condition as IconCondition, IconOption, MaterialKind } from '@/types/icon';


PDFJS.GlobalWorkerOptions.workerSrc = new URL(
    "pdfjs-dist/build/pdf.worker.mjs",
    import.meta.url
  ).toString();

// Props：外部传入 PDF 文件路径
const props = defineProps({
  pdfSrc: {
    type: String,
    required: true,
  },
});

// refs 与状态变量
let pdfDoc: any = null;
const pdfPages = ref(0);
const pdfScale = ref(2); // 控制清晰度
const pdfContainerRef = ref<HTMLElement | null>(null);

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
    const canvas: HTMLCanvasElement | null = document.getElementById(`pdf-canvas-${num}`) as HTMLCanvasElement;
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
    const overlayCanvas: HTMLCanvasElement | null = document.getElementById(`overlay-canvas-${num}`) as HTMLCanvasElement;
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
  const raw = e.dataTransfer?.getData('application/x-batchprint-option');
  if (!raw) return;

  try {
    const payload = JSON.parse(raw) as { option?: IconOption; panel?: string };
    if (!payload.option) return;
    // 同类型材料沿用上次确认的样式（载荷仅提供身份字段；文本预设自带样式）
    const kind = (payload.panel || 'table') as MaterialKind;
    const option = bpStore.instantiateOption(kind, payload.option);
    const canvas = document.getElementById(`overlay-canvas-${pageIndex}`) as HTMLCanvasElement | null;
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
  const canvas = document.getElementById(`overlay-canvas-${pageIndex}`) as HTMLCanvasElement | null;
  if (!canvas) return { x: 0, y: 0 };

  const rect = canvas.getBoundingClientRect();
  const x = (e.clientX - rect.left) * (canvas.width / rect.width);
  const y = (e.clientY - rect.top) * (canvas.height / rect.height);
  return { x, y };
}

// 检查鼠标是否在某个 icon 内
function isPointInIcon(point: { x: number; y: number }, icon: StoreIcon) {
  const size = getIconSize(icon);
  return (
    point.x >= icon.pointer.clientX - size / 2 &&
    point.x <= icon.pointer.clientX + size / 2 &&
    point.y >= icon.pointer.clientY - size / 2 &&
    point.y <= icon.pointer.clientY + size / 2
  );
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
  const coords = getCanvasCoordinates(e, pageIndex);
  lastMouseCoords.value = coords;
  lastMousePageIndex.value = pageIndex;

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
    selectedIcon.value.pointer.clientX = coords.x - dragOffset.value.x;
    selectedIcon.value.pointer.clientY = coords.y - dragOffset.value.y;
    redrawIcons(pageIndex);
    return;
  }
}

function onCanvasMouseLeave() {
  // selection persists, no auto-deselect
}

function onCanvasMouseDown(e: MouseEvent, pageIndex: number) {
  const coords = getCanvasCoordinates(e, pageIndex);
  const pageIcons = icons.value.filter(icon => icon.pageIndex === pageIndex);

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

  for (const icon of pageIcons) {
    if (isPointInIcon(coords, icon)) {
      selectedIcon.value = icon;
      isDragging.value = true;
      dragOffset.value = { x: coords.x - icon.pointer.clientX, y: coords.y - icon.pointer.clientY };
      redrawIcons(pageIndex);
      return;
    }
  }

  selectedIcon.value = null;
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
  isDragging.value = false;
  isResizing.value = false;
  isRotating.value = false;
  resizeIcon.value = null;
  rotateIcon.value = null;
}

// 右键单击 icon 时打开设置弹窗
function onCanvasContextMenu(e: MouseEvent, pageIndex: number) {
  const coords = getCanvasCoordinates(e, pageIndex);
  const pageIcons = icons.value.filter(icon => icon.pageIndex === pageIndex);
  for (const icon of pageIcons) {
    if (isPointInIcon(coords, icon)) {
      selectedIcon.value = icon;
      redrawIcons(pageIndex);
      openLocationDialog(icon);
      return;
    }
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
}

// 重新绘制 overlay canvas 上的 icon
function redrawIcons(pageIndex: number) {
  const canvas = document.getElementById(`overlay-canvas-${pageIndex}`) as HTMLCanvasElement | null;
  if (!canvas) return;

  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  // 清空 overlay canvas
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  const pageIcons = icons.value.filter(icon => icon.pageIndex === pageIndex);
  for (const icon of pageIcons) {
    drawIcon(ctx, icon, icon === selectedIcon.value);
  }
}

function redrawAllPages() {
  for (let i = 1; i <= pdfPages.value; i += 1) {
    redrawIcons(i);
  }
}

// 辅助函数：获取字段值
function getFieldValue(fieldName: string): string {
  if (!fieldName || !bpStore.fieldNames || !bpStore.excelContent?.length) {
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
  cursor: grab;
}

.overlay-canvas:active {
  cursor: grabbing;
}
</style>
