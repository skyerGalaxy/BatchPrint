<template>
  <v-layout class="rounded rounded-md border">
    <v-app-bar title="AutoFiller"></v-app-bar>

    <v-navigation-drawer>
      <v-list nav>

        #上传模板文件
        <div class="my-5">模板</div>
        <v-file-input
          accept=".pdf"
          prepend-icon="mdi-file-pdf"
          label="File input"
          @change="handleFileChange"
        ></v-file-input>

        <v-divider class="mb-5"></v-divider>

        #上传表格文件
        <div class="mb-5">表格</div>
        <v-file-input
          accept=".xlsx, .xls"
          prepend-icon="mdi-file-excel"
          label="File input"
        ></v-file-input>
        <v-divider class="mt-1"></v-divider>




      </v-list>
    </v-navigation-drawer>

    <v-main class="d-flex align-center justify-center" style="height: 100vh;">
      <!-- 用于展示PDF的iframe -->
      <iframe
        ref="pdfIframe"
        :src="pdfSrc"
        width="100%"
        height="100%"
        style="border: none;"></iframe>
    </v-main>
  </v-layout>
</template>

<script setup lang="ts">
import { ref } from 'vue';

// 用于存储选择的PDF文件
const pdfSrc = ref<string>('');

const handleFileChange = async (event: Event) => {
  const fileInput = event.target as HTMLInputElement;
  const file = fileInput.files ? fileInput.files[0] : null;

  if (file && file.type === 'application/pdf') {
    // 创建一个URL对象来展示PDF
    const fileURL = URL.createObjectURL(file);
    pdfSrc.value = fileURL;
  } else {
    alert('请选择有效的PDF文件');
  }
};
</script>

<style scoped>
/* 可以根据需要进行样式调整 */
</style>
