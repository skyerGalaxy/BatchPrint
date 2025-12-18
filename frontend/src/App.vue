<template>
  <v-layout class="rounded rounded-md border">
    <v-app-bar title="AutoFiller">
      <template v-slot:append>
        <v-menu
          :offset-y="true"
          :close-on-content-click="true"
          :nudge-bottom="10"
        >
          <template v-slot:activator="{ props }">
            <v-btn 
              v-bind="props"
              icon
              color="primary"
            >
              <v-icon>mdi-account</v-icon>
            </v-btn>
          </template>
          <v-card min-width="200">
            <v-list-item>
              <v-list-item-title>Profile</v-list-item-title>
            </v-list-item>
            <v-divider></v-divider>
            <v-list density="compact">
              <v-list-item @click="settingsDialog?.openDialog()">
                  <v-list-item-title>Settings</v-list-item-title>
              </v-list-item>
              <v-list-item>
                <v-list-item-title>Logout</v-list-item-title>
              </v-list-item>
            </v-list>
          </v-card>
        </v-menu>
      </template>
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

    <SettingsDialog ref="settingsDialog" />
  </v-layout>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useBPStore } from './stores/bpstore';
import axios from 'axios';
import PdfViewer from './components/pdfview/PdfViewer.vue';
import SettingsDialog from './components/global/SettingsDialog.vue';

const pdfSrc = ref<string>('');
const useBPStoreInstance = useBPStore();

const settingsDialog = ref<InstanceType<typeof SettingsDialog> | null>(null);

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
