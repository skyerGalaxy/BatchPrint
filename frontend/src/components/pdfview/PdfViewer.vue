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
        @contextmenu.prevent="onCanvasClick($event, pageIndex)"
        @mousemove="onCanvasMouseMove($event, pageIndex)"
        @mouseleave="onCanvasMouseLeave"
        @mousedown="onCanvasMouseDown($event, pageIndex)"
        @mouseup="onCanvasMouseUp"
      />
    </div>
  </div>
  <LocationDialog v-model:dialog="dialog" />
</template>

<script setup lang="ts">
import * as PDFJS from "pdfjs-dist";
import { ref, onMounted, watch, nextTick } from "vue";

import LocationDialog from "./LocationDialog.vue";

import { useBPStore } from "@/stores/bpstore";

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

const pointer_x = ref(0);
const pointer_y = ref(0);

const dialog = ref(false);

const bpStore = useBPStore();

// Icon 相关状态
interface Icon {
  id: string;
  pageIndex: number;
  x: number;
  y: number;
  size: number;
  type: string; // 'stamp' | 'text' 等
}

const icons = ref<Icon[]>([]);
const selectedIcon = ref<Icon | null>(null);
const hoveredIcon = ref<Icon | null>(null);
const isDragging = ref(false);
const isResizing = ref(false);
const dragOffset = ref({ x: 0, y: 0 });
const resizeStartSize = ref(0);
const resizeStartDist = ref(0);
const resizeIcon = ref<Icon | null>(null);


// 初始化示例 icon
const initSampleIcons = () => {
  // 清空旧 icon
  icons.value = [];
  
  // 第一页示例 icon
  if (pdfPages.value >= 1) {
    icons.value.push(
      {
        id: '1',
        pageIndex: 1,
        x: 300,
        y: 400,
        size: 40,
        type: 'stamp',
      },
      {
        id: '2',
        pageIndex: 1,
        x: 600,
        y: 600,
        size: 35,
        type: 'text',
      },
      {
        id: '3',
        pageIndex: 1,
        x: 450,
        y: 800,
        size: 45,
        type: 'stamp',
      }
    );
  }
  
  // 第二页示例 icon
  if (pdfPages.value >= 2) {
    icons.value.push(
      {
        id: '4',
        pageIndex: 2,
        x: 500,
        y: 500,
        size: 40,
        type: 'text',
      },
      {
        id: '5',
        pageIndex: 2,
        x: 700,
        y: 1000,
        size: 38,
        type: 'stamp',
      }
    );
  }
};

// 加载 PDF 文件
const loadFile = (url: string) => {
  const loadingTask = PDFJS.getDocument(url);
  loadingTask.promise
    .then(async (pdf: any) => {
      pdfDoc = pdf;
      pdfPages.value = pdf.numPages;
      await nextTick();
      initSampleIcons(); // 初始化示例 icon
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

    // 根据A4比例计算显示高度
    const displayWidth = Math.min(containerWidth * 0.9, 900); // 保留10%边距，最大宽900px
    const displayHeight = (displayWidth * 297) / 210; // 保持A4比例

    // 设置canvas绘制分辨率（清晰度）
    canvas.width = viewport.width;
    canvas.height = viewport.height;

    // 设置在页面上的显示比例（仅视觉缩放）
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
    }

    // 渲染下一页
    if (num < pdfPages.value) {
      renderPage(num + 1);
    }
  });
};

// 点击时计算 canvas 内的绘制坐标（考虑了样式缩放）
function onCanvasClick(e: MouseEvent, pageIndex: number) {
  const canvas = document.getElementById(`pdf-canvas-${pageIndex}`) as HTMLCanvasElement | null;
  if (!canvas) return;

  const rect = canvas.getBoundingClientRect();
  const clientX = e.clientX;
  const clientY = e.clientY;

  // 将屏幕坐标转换为 canvas 绘制坐标（与 canvas.width / canvas.height 对应）
  const pointer_x = (clientX - rect.left) * (canvas.width / rect.width);
  const pointer_y = (clientY - rect.top) * (canvas.height / rect.height);

  // 归一化坐标（0..1）
  const nx = (clientX - rect.left) / rect.width;
  const ny = (clientY - rect.top) / rect.height;


  // 保留原来的行为：切换对话框显示
  dialog.value = !dialog.value;
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
function isPointInIcon(point: { x: number; y: number }, icon: Icon) {
  return (
    point.x >= icon.x - icon.size / 2 &&
    point.x <= icon.x + icon.size / 2 &&
    point.y >= icon.y - icon.size / 2 &&
    point.y <= icon.y + icon.size / 2
  );
}

// 检查鼠标是否在左上角删除按钮上
function isPointOnDeleteButton(point: { x: number; y: number }, icon: Icon): boolean {
  const deleteX = icon.x - icon.size / 2;
  const deleteY = icon.y - icon.size / 2;
  const buttonSize = 16;
  return (
    point.x >= deleteX - buttonSize / 2 &&
    point.x <= deleteX + buttonSize / 2 &&
    point.y >= deleteY - buttonSize / 2 &&
    point.y <= deleteY + buttonSize / 2
  );
}

// 检查鼠标是否在右下角缩放按钮上
function isPointOnResizeButton(point: { x: number; y: number }, icon: Icon): boolean {
  const resizeX = icon.x + icon.size / 2;
  const resizeY = icon.y + icon.size / 2;
  const buttonSize = 16;
  return (
    point.x >= resizeX - buttonSize / 2 &&
    point.x <= resizeX + buttonSize / 2 &&
    point.y >= resizeY - buttonSize / 2 &&
    point.y <= resizeY + buttonSize / 2
  );
}

// Canvas 鼠标移动事件
function onCanvasMouseMove(e: MouseEvent, pageIndex: number) {
  const coords = getCanvasCoordinates(e, pageIndex);

  // 处理缩放
  if (isResizing.value && resizeIcon.value) {
    const dist = Math.sqrt(
      Math.pow(coords.x - resizeIcon.value.x, 2) + 
      Math.pow(coords.y - resizeIcon.value.y, 2)
    );
    const newSize = Math.max(20, resizeStartSize.value + (dist - resizeStartDist.value) * 2);
    resizeIcon.value.size = newSize;
    redrawIcons(pageIndex);
    return;
  }

  // 处理拖拽
  if (isDragging.value && selectedIcon.value) {
    selectedIcon.value.x = coords.x - dragOffset.value.x;
    selectedIcon.value.y = coords.y - dragOffset.value.y;
    redrawIcons(pageIndex);
    return;
  }

  const pageIcons = icons.value.filter(icon => icon.pageIndex === pageIndex);
  
  let found = false;
  for (const icon of pageIcons) {
    if (isPointInIcon(coords, icon)) {
      hoveredIcon.value = icon;
      found = true;
      break;
    }
  }
  if (!found) {
    hoveredIcon.value = null;
  }

  redrawIcons(pageIndex);
}

// Canvas 鼠标离开事件
function onCanvasMouseLeave() {
  hoveredIcon.value = null;
}

// Canvas 鼠标按下事件
function onCanvasMouseDown(e: MouseEvent, pageIndex: number) {
  const coords = getCanvasCoordinates(e, pageIndex);
  const pageIcons = icons.value.filter(icon => icon.pageIndex === pageIndex);
  
  for (const icon of pageIcons) {
    // 优先检查删除按钮
    if (isPointOnDeleteButton(coords, icon)) {
      deleteIcon(icon);
      return;
    }
    
    // 然后检查缩放按钮
    if (isPointOnResizeButton(coords, icon)) {
      isResizing.value = true;
      resizeIcon.value = icon;
      resizeStartSize.value = icon.size;
      resizeStartDist.value = Math.sqrt(
        Math.pow(coords.x - icon.x, 2) + 
        Math.pow(coords.y - icon.y, 2)
      );
      return;
    }
    
    // 最后检查 icon 主体
    if (isPointInIcon(coords, icon)) {
      isDragging.value = true;
      selectedIcon.value = icon;
      dragOffset.value = {
        x: coords.x - icon.x,
        y: coords.y - icon.y,
      };
      return;
    }
  }
}

// Canvas 鼠标抬起事件
function onCanvasMouseUp() {
  isDragging.value = false;
  isResizing.value = false;
  resizeIcon.value = null;
}

// 删除 icon
function deleteIcon(icon: Icon) {
  const index = icons.value.indexOf(icon);
  if (index > -1) {
    icons.value.splice(index, 1);
    redrawIcons(icon.pageIndex);
  }
  hoveredIcon.value = null;
}

// 重新绘制 overlay canvas 上的 icon
function redrawIcons(pageIndex: number) {
  const canvas = document.getElementById(`overlay-canvas-${pageIndex}`) as HTMLCanvasElement | null;
  if (!canvas) return;

  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  // 清空 overlay canvas
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // 获取样式缩放比例
  const rect = canvas.getBoundingClientRect();
  const scaleX = canvas.width / rect.width;
  const scaleY = canvas.height / rect.height;

  // 绘制该页的所有 icon
  const pageIcons = icons.value.filter(icon => icon.pageIndex === pageIndex);
  for (const icon of pageIcons) {
    drawIcon(ctx, icon, scaleX, scaleY, icon === selectedIcon.value, icon === hoveredIcon.value);
  }
}

// 绘制所有 icon
function drawAllIcons(ctx: CanvasRenderingContext2D, pageIndex: number) {
  const canvas = document.getElementById(`overlay-canvas-${pageIndex}`) as HTMLCanvasElement | null;
  if (!canvas) return;

  const rect = canvas.getBoundingClientRect();
  const scaleX = canvas.width / rect.width;
  const scaleY = canvas.height / rect.height;

  const pageIcons = icons.value.filter(icon => icon.pageIndex === pageIndex);
  for (const icon of pageIcons) {
    drawIcon(ctx, icon, scaleX, scaleY, icon === selectedIcon.value, icon === hoveredIcon.value);
  }
}

// 绘制单个 icon
function drawIcon(ctx: CanvasRenderingContext2D, icon: Icon, scaleX: number, scaleY: number, isSelected: boolean, isHovered: boolean) {
  const x = icon.x;
  const y = icon.y;
  const size = icon.size;

  // 直接绘制 icon（emoji）
  ctx.fillStyle = "#000";
  ctx.font = `bold ${size}px Arial`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(icon.type === "stamp" ? "📌" : "✎", x, y);

  // 只在悬停时显示删除和缩放按钮
  if (isHovered) {
    const halfSize = size / 2;
    
    // 绘制左上角删除按钮
    const deleteX = x - halfSize;
    const deleteY = y - halfSize;
    const deleteSize = 18;
    
    // 删除按钮背景（圆形）
    ctx.fillStyle = "#ff4444";
    ctx.beginPath();
    ctx.arc(deleteX, deleteY, deleteSize / 2, 0, Math.PI * 2);
    ctx.fill();
    
    // 删除符号
    ctx.fillStyle = "#fff";
    ctx.font = "bold 14px Arial";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("✕", deleteX, deleteY);

    // 绘制右下角缩放按钮
    const resizeX = x + halfSize;
    const resizeY = y + halfSize;
    const resizeSize = 18;
    
    // 缩放按钮背景（圆形）
    ctx.fillStyle = "#4444ff";
    ctx.beginPath();
    ctx.arc(resizeX, resizeY, resizeSize / 2, 0, Math.PI * 2);
    ctx.fill();
    
    // 缩放符号（斜双向箭头）
    ctx.fillStyle = "#fff";
    ctx.font = "bold 14px Arial";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("⇲", resizeX, resizeY);
  }
}

// 初始化
onMounted(() => {
  loadFile(props.pdfSrc);
});

// 当传入的 PDF 路径变化时重新加载
watch(
  () => props.pdfSrc,
  (newPdfSrc) => {
    pdfPages.value = 0;
    loadFile(newPdfSrc);
  }
);
</script>

<style scoped>
.pdf-container {
  width: 100%;
  height: 100%;
  overflow-y: auto;
  background-color: #f8f9fa;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px 0;
}

/* 每页保持 A4 比例、居中显示 */
.pdf-page-wrapper {
  position: relative;
  display: inline-block;
  margin: 12px auto;
}

.pdf-page {
  display: block;
  background: white;
  box-shadow: 0 0 8px rgba(0, 0, 0, 0.15);
  aspect-ratio: 210 / 297; /* 强制A4比例 */
}

.overlay-canvas {
  position: absolute;
  top: 0;
  left: 0;
  cursor: grab;
  aspect-ratio: 210 / 297;
}

.overlay-canvas:active {
  cursor: grabbing;
}
</style>
