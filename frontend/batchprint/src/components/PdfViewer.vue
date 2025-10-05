<template>
  <div class="pdf-container" ref="pdfContainerRef">
    <canvas
      v-for="pageIndex in pdfPages"
      :id="`pdf-canvas-${pageIndex}`"
      :key="pageIndex"
    />
  </div>
</template>

<script setup lang="ts">
import * as PDFJS from "pdfjs-dist";
import { ref, onMounted, watch } from "vue";


const props = defineProps({
  pdfSrc: {
    type: String,
    required: true,
  },
});

let pdfDoc: any = null;
const pdfPages = ref(0);
const pdfScale = ref(1);
const pdfContainerRef = ref<HTMLElement | null>(null);

// 加载PDF文件
const loadFile = (url: string) => {
  const loadingTask = PDFJS.getDocument(url);
  loadingTask.promise
    .then(async (pdf: any) => {
      pdf.loadingParams.disableAutoFetch = true;
      pdf.loadingParams.disableStream = true;
      pdfDoc = pdf; // 保存加载的pdf文件流
      pdfPages.value = pdfDoc.numPages; // 获取pdf文件的总页数
      renderPage(1); // 渲染第一页
    })
    .catch((error: any) => {
      console.warn(`[PdfViewer] loadFile error: ${error}`);
    });
};

// 渲染页面
const renderPage = (num: number) => {
  pdfDoc.getPage(num).then((page: any) => {
    if (pdfContainerRef.value) {
      pdfScale.value = pdfContainerRef.value.clientWidth / page.view[2];
    }
    const canvas: any = document.getElementById(`pdf-canvas-${num}`);
    if (canvas) {
      const ctx = canvas.getContext("2d");
      const dpr = window.devicePixelRatio || 1;
      const bsr =
        ctx.webkitBackingStorePixelRatio ||
        ctx.mozBackingStorePixelRatio ||
        ctx.msBackingStorePixelRatio ||
        ctx.oBackingStorePixelRatio ||
        ctx.backingStorePixelRatio ||
        1;
      const ratio = dpr / bsr;
      const viewport = page.getViewport({scale: pdfScale.value});
      canvas.width = viewport.width * ratio;
      canvas.height = viewport.height * ratio;
      canvas.style.width = viewport.width + "px";
      canvas.style.height = viewport.height + "px";
      ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
      const renderContext = {
        canvasContext: ctx,
        viewport: viewport,
      };
      page.render(renderContext);
      if (num < pdfPages.value) {
        renderPage(num + 1);
      }
    }
  });
};

onMounted(() => {
  loadFile(props.pdfSrc); // 加载传入的pdf文件
});

// 当 pdfSrc 参数变化时，重新加载新的 PDF 文件
watch(
  () => props.pdfSrc,
  (newPdfSrc) => {
    pdfPages.value = 0; // 重置页数
    //////////////////
    console.log(newPdfSrc);
    // 设定pdfjs的 workerSrc 参数
    PDFJS.GlobalWorkerOptions.workerSrc = new URL(
    "pdfjs-dist/build/pdf.worker.mjs",
    import.meta.url
  ).toString();
    loadFile(newPdfSrc); // 重新加载 PDF 文件
  }

);
</script>

<style scoped>
.pdf-container {
  height: 100%;
  overflow-y: scroll;
  overflow-x: hidden;
}

canvas {
  display: block;
  margin: 10px auto;
}
</style>
