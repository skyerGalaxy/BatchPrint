<template>
  <v-container fluid class="batch-shell px-6 py-6">
    <v-row class="batch-grid" align="stretch" no-gutters>
      <v-col cols="12" lg="4" class="batch-col pe-lg-3">
        <div class="control-card">
          <div class="card-header">
            <v-icon size="20" color="primary" class="mr-2">mdi-tune-variant</v-icon>
            <span class="card-title">输入与设置</span>
          </div>

          <div class="control-body">
            <div class="section">
              <div class="section-label">模板</div>
              <v-file-input
                accept="application/pdf,.pdf"
                prepend-icon="mdi-file-pdf"
                label="选择 PDF 模板"
                variant="outlined"
                density="comfortable"
                hide-details
                @update:modelValue="handleFileChange"
              />
            </div>

            <div class="section">
              <div class="section-label">表格</div>
              <v-file-input
                accept=".xlsx, .xls"
                prepend-icon="mdi-file-excel"
                label="选择 Excel 数据"
                variant="outlined"
                density="comfortable"
                hide-details
                @change="handleExcelChange"
              />
            </div>

            <div class="section field-section">
              <div class="section-label">字段</div>
              <div v-if="bpStore.fieldNames.length === 0" class="field-empty">
                选择 Excel 后自动显示字段标签
              </div>
              <div v-else class="field-chips">
                <v-chip
                  v-for="fieldName in bpStore.fieldNames"
                  :key="fieldName"
                  color="primary"
                  variant="tonal"
                  size="small"
                  draggable
                >
                  {{ fieldName }}
                </v-chip>
              </div>
            </div>

            <v-btn
              color="primary"
              size="large"
              rounded="lg"
              block
              class="generate-btn"
              @click="generateBatchPDF"
            >
              <v-icon size="18" class="mr-2">mdi-file-document-multiple</v-icon>
              生成 PDF
            </v-btn>
          </div>
        </div>
      </v-col>

      <v-col cols="12" lg="8" class="batch-col ps-lg-3">
        <div class="preview-card">
          <div class="card-header preview-top">
            <div class="d-flex align-center">
              <v-icon size="20" color="primary" class="mr-2">mdi-eye-outline</v-icon>
              <span class="card-title">预览区</span>
            </div>
            <v-btn
              variant="outlined"
              color="primary"
              size="small"
              rounded="lg"
              @click="libraryPanel?.openDialog()"
            >
              <v-icon size="16" class="mr-1">mdi-image-multiple</v-icon>
              素材库
            </v-btn>
          </div>

          <div class="preview-surface">
            <div class="preview-scroll">
              <PdfViewer :pdf-src="pdfSrc" />
            </div>
          </div>
        </div>
      </v-col>
    </v-row>

    <LibraryPanel ref="libraryPanel" />
  </v-container>
</template>

<script setup lang="ts">
import axios from 'axios'
import { ref } from 'vue'
import PdfViewer from '@/components/pdfview/PdfViewer.vue'
import LibraryPanel from '@/components/LibraryPanel.vue'
import { useBPStore } from '@/stores/bpstore'

const pdfSrc = ref<string>('')
const bpStore = useBPStore()

const libraryPanel = ref<InstanceType<typeof LibraryPanel> | null>(null)

const handleFileChange = async (value: File | File[] | null) => {
  const file = Array.isArray(value) ? value[0] : value

  if (file && file.type === 'application/pdf') {
    pdfSrc.value = URL.createObjectURL(file)
    bpStore.pdfSrc = pdfSrc.value
    bpStore.pdfFile = file
  } else {
    alert('请选择有效的PDF文件')
  }
}

const handleExcelChange = async (event: Event) => {
  const fileInput = event.target as HTMLInputElement
  const file = fileInput.files ? fileInput.files[0] : null

  bpStore.excelSrc = file ? URL.createObjectURL(file) : ''
  bpStore.excelFile = file

  if (
    file &&
    (file.type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' ||
      file.type === 'application/vnd.ms-excel')
  ) {
    const formData = new FormData()
    formData.append('file', file)

    const res = await axios.post('http://localhost:8000/get_excel_headers', formData)
    bpStore.fieldNames = res.data.headers
    bpStore.excelContent = res.data.content
  } else {
    alert('请选择有效的Excel文件')
  }
}

const generateBatchPDF = async () => {
  if (!bpStore.pdfFile) {
    alert('请先选择PDF模板')
    return
  }

  if (!bpStore.excelFile) {
    alert('请先选择Excel数据文件')
    return
  }

  try {
    const formData = new FormData()

    formData.append('pdf_file', bpStore.pdfFile)
    formData.append('excel_file', bpStore.excelFile)
    formData.append('path', bpStore.dataPath || '')
    formData.append('icon_list', JSON.stringify(bpStore.iconList))
    formData.append('pdf_scale', bpStore.pdfScale.toString())

    const res = await axios.post('http://localhost:8000/generate_batch_pdf', formData)

    alert('PDF批量生成成功！' + res.data.message)
  } catch (error) {
    console.error('生成PDF失败:', error)
    alert('PDF批量生成出错，请查看浏览器控制台')
  }
}
</script>

<style scoped>
.batch-shell {
  max-width: 1600px;
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.batch-grid {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.batch-col {
  display: flex;
  min-height: 0;
  overflow: hidden;
  padding-bottom: 12px;
}

/* ---- cards ---- */
.control-card,
.preview-card {
  display: flex;
  flex-direction: column;
  min-height: 0;
  width: 100%;
  background: #fff;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  overflow: hidden;
}

.card-header {
  display: flex;
  align-items: center;
  padding: 16px 20px 12px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.04);
}

.card-title {
  font-size: 0.82rem;
  font-weight: 600;
  color: rgb(15, 23, 42);
  letter-spacing: -0.01em;
}

.preview-top {
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
}

/* ---- sections ---- */
.control-body {
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr) auto;
  gap: 0;
  min-height: 0;
  flex: 1;
  overflow: hidden;
  padding: 4px 20px 16px;
}

.section {
  padding: 12px 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.03);
}

.section:last-of-type {
  border-bottom: none;
}

.section-label {
  font-size: 0.7rem;
  font-weight: 600;
  color: rgb(100, 116, 139);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 8px;
}

.field-section {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.field-empty {
  font-size: 0.8rem;
  color: rgb(148, 163, 184);
  padding: 12px 0;
}

.field-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 4px 0;
  overflow-y: auto;
  overscroll-behavior: contain;
}

/* ---- buttons ---- */
.generate-btn {
  margin-top: 12px;
  border-radius: 12px !important;
}

/* ---- preview ---- */
.preview-surface {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  margin: 0 12px 12px;
  border-radius: 12px;
  overflow: hidden;
  background: rgb(248, 249, 250);
  border: 1px solid rgba(0, 0, 0, 0.04);
}

.preview-scroll {
  flex: 1;
  min-height: 0;
  overflow: auto;
  overscroll-behavior: contain;
}
</style>
