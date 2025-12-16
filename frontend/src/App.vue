<template>
  <v-layout class="rounded rounded-md border">
    <v-app-bar title="AutoFiller">
      
    </v-app-bar>

    <v-navigation-drawer
      width="25%"
      style ="min-width: 220px; max-width: 300px"
    >
      <v-list nav>
        <div class="mt-15">模板</div>
        <v-file-input
          accept="application/pdf,.pdf"
          prepend-icon="mdi-file-pdf"
          label="File input"
          @change="handleFileChange"
        ></v-file-input>
        <v-divider class="mb-5"></v-divider>

        <div class="mb-5">表格</div>
        <v-file-input
          accept=".xlsx, .xls"
          prepend-icon="mdi-file-excel"
          label="File input"
          @change="handleExcelChange"
        ></v-file-input>
        <v-divider class="mt-1"></v-divider>
        <div class="mt-3">
          <v-chip
            v-for="fieldName in useBPStoreInstance.fieldNames"
            :key="fieldName"
            class="ma-1"
            color="primary"
            :draggable="true"
            label
          >
            {{ fieldName }}
          </v-chip>
        </div>
      </v-list>
    </v-navigation-drawer>

    <v-main class="d-flex align-center justify-center" style="flex:1;height: 100vh;">
      <PdfViewer :pdfSrc="pdfSrc" />
    </v-main>
  </v-layout>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useBPStore } from './stores/bpstore';
import axios from 'axios';
import PdfViewer from './components/pdfview/PdfViewer.vue';

const pdfSrc = ref<string>('');
const useBPStoreInstance = useBPStore();

const handleFileChange = async (event: Event) => {
  const fileInput = event.target as HTMLInputElement;
  const file = fileInput.files ? fileInput.files[0] : null;
  console.log(file);
  if (file && file.type === 'application/pdf') {
    pdfSrc.value = URL.createObjectURL(file);
    console.log('PDF file loaded:', pdfSrc.value);
  } else {
    alert('请选择有效的PDF文件');
  }
};

const handleExcelChange = async (event: Event) => {
  const fileInput = event.target as HTMLInputElement
  const file = fileInput.files ? fileInput.files[0] : null

  if (file && (file.type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' || file.type === 'application/vnd.ms-excel')) {
    const formData = new FormData()
    formData.append('file', file)
    const res = await axios.post('http://localhost:8000/get_excel_headers', formData)
    useBPStoreInstance.fieldNames = res.data.headers
    console.log('Excel file loaded:', useBPStoreInstance.fieldNames)
  } else {
    alert('请选择有效的Excel文件')
  }
}
</script>
