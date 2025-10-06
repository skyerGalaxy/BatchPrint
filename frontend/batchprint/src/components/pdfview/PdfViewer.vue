<template>
  <div class="pdf-container" ref="pdfContainerRef">
    <canvas
      v-for="pageIndex in pdfPages"
      :id="`pdf-canvas-${pageIndex}`"
      :key="pageIndex"
      class="pdf-page"
      style="cursor: crosshair;"
      @click="dialog = !dialog"
    />
  </div>

  <v-dialog v-model="dialog" max-width="500">
    <v-card>
      <v-card-title class="text-h5">Use Google's location service?</v-card-title>
      <v-card-text>
        Let Google help apps determine location. This means sending anonymous location data to
        Google, even when no apps are running.
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn color="primary" text @click="dialog = false">Disagree</v-btn>
        <v-btn color="primary" text @click="dialog = false">Agree</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import * as PDFJS from "pdfjs-dist";
import { ref, onMounted, watch, nextTick } from "vue";

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

const dialog = ref(false);

// 加载 PDF 文件
const loadFile = (url: string) => {
  const loadingTask = PDFJS.getDocument(url);
  loadingTask.promise
    .then(async (pdf: any) => {
      pdfDoc = pdf;
      pdfPages.value = pdf.numPages;
      await nextTick();
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

    // 渲染下一页
    if (num < pdfPages.value) {
      renderPage(num + 1);
    }
  });
};

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
  .pdf-page {
  display: block;
  margin: 12px auto;
  background: white;
  box-shadow: 0 0 8px rgba(0, 0, 0, 0.15);
  aspect-ratio: 210 / 297; /* 强制A4比例 */
}
</style>
