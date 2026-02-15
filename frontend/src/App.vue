<template>
  <v-layout class="rounded rounded-md border">
    <v-app-bar title="AutoFiller">
      <template v-slot:append>
        <v-btn 
          icon
          color="primary"
          @click="libraryPanel?.openDialog()"
        >
          <v-icon>mdi-library</v-icon>
        </v-btn>
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
      location="right"
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
            v-for="fieldName in bpStore.fieldNames"
            :key="fieldName"
            class="ma-1"
            color="primary"
            :draggable="true"
            label
          >
            {{ fieldName }}
          </v-chip>
        </div>
        <v-divider class="mt-5"></v-divider>
        <div class="d-flex justify-center mt-8">
            <v-btn
            class="ma-2"
            color="primary"
            block
            @click="generateBatchPDF"
            >
            生成PDF
            </v-btn>
        </div>
      </v-list>
    </v-navigation-drawer>

    <v-main class="d-flex align-center justify-center" style="flex:1;height: 100vh;">
      <PdfViewer :pdfSrc="pdfSrc" />
    </v-main>

    <SettingsDialog ref="settingsDialog" />
    <LibraryPanel ref="libraryPanel" />
  </v-layout>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useBPStore } from './stores/bpstore';
import axios from 'axios';
import PdfViewer from './components/pdfview/PdfViewer.vue';
import SettingsDialog from './components/global/SettingsDialog.vue';
import LibraryPanel from './components/global/libraryPanel.vue';

const pdfSrc = ref<string>('');
const bpStore = useBPStore();

const settingsDialog = ref<InstanceType<typeof SettingsDialog> | null>(null);
const libraryPanel = ref<InstanceType<typeof LibraryPanel> | null>(null);

const handleFileChange = async (event: Event) => {
  const fileInput = event.target as HTMLInputElement;
  const file = fileInput.files ? fileInput.files[0] : null;
  console.log(file);
  if (file && file.type === 'application/pdf') {
    pdfSrc.value = URL.createObjectURL(file);
    bpStore.pdfSrc = pdfSrc.value;
    console.log('PDF file loaded:', pdfSrc.value);
  } else {
    alert('请选择有效的PDF文件');
  }
};

const handleExcelChange = async (event: Event) => {
  const fileInput = event.target as HTMLInputElement
  const file = fileInput.files ? fileInput.files[0] : null
  bpStore.excelSrc = file ? URL.createObjectURL(file) : ''

  if (file && (file.type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' || file.type === 'application/vnd.ms-excel')) {
    const formData = new FormData()
    formData.append('file', file)
    const res = await axios.post('http://localhost:8000/get_excel_headers', formData)
    bpStore.fieldNames = res.data.headers
    bpStore.excelContent = res.data.content
    console.log('Excel file loaded:', bpStore.fieldNames)
    console.log('Excel content loaded:', bpStore.excelContent)
  } else {
    alert('请选择有效的Excel文件')
  }
}

const generateBatchPDF = async () => {
  if (!bpStore.pdfSrc) {
    alert('请先选择PDF模板')
    return
  }
  if (!bpStore.excelSrc) {
    alert('请先选择Excel数据文件')
    return
  }

  try {
    // 将pdfSrc和excelSrc转换为Base64或者直接发送二进制数据
    const pdfResponse = await fetch(bpStore.pdfSrc)
    const pdfBlob = await pdfResponse.blob()
    
    const excelResponse = await fetch(bpStore.excelSrc)
    const excelBlob = await excelResponse.blob()

    const formData = new FormData()
    formData.append('pdf_file', pdfBlob, 'template.pdf')
    formData.append('excel_file', excelBlob, 'data.xlsx')
    formData.append('icon_list', JSON.stringify(bpStore.iconList))

    console.log('发送的iconList:', bpStore.iconList)

    const res = await axios.post('http://localhost:8000/generate_batch_pdf', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      responseType: 'blob'
    })

    // 处理ZIP文件下载
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', 'batch_pdfs.zip')
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
    
    alert('PDF批量生成成功！文件已下载')
  } catch (error) {
    console.error('生成PDF失败:', error)
    alert('生成PDF出错，请查看浏览器控制台')
  }
}
</script>
