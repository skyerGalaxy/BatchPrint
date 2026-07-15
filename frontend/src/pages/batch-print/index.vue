<template>
  <v-container fluid class="batch-shell px-6 py-6">
    <v-row class="batch-grid" align="stretch" no-gutters>
      <v-col cols="12" lg="4" class="batch-col pe-lg-3">
        <div class="control-card">
          <div class="card-header">
            <v-icon size="20" color="primary" class="mr-2">mdi-tune-variant</v-icon>
            <span class="card-title">输入与设置</span>
            <v-spacer></v-spacer>
            <v-btn
              variant="text"
              color="grey-darken-1"
              size="small"
              rounded="lg"
              @click="handleReset"
            >
              <v-icon size="16" class="mr-1">mdi-refresh</v-icon>
              重置
            </v-btn>
          </div>

          <div class="control-body">
            <div class="section">
              <div class="section-label">模板</div>
              <v-file-input
                :key="'pdf-' + resetKey"
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
                :key="'xls-' + resetKey"
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
              :loading="generating"
              :disabled="generating"
              @click="generateBatchPDF"
            >
              <v-icon size="18" class="mr-2">mdi-file-document-multiple</v-icon>
              {{ generating ? '生成中...' : '生成 PDF' }}
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
            <v-chip
              v-if="bpStore.iconList.length > 0"
              variant="outlined"
              size="small"
              color="grey"
              class="clear-chip"
              @click="bpStore.iconList = []"
            >
              <v-icon start size="12">mdi-delete-outline</v-icon>
              清空标注 ({{ bpStore.iconList.length }})
            </v-chip>
          </div>

          <div class="preview-surface">
            <div class="preview-scroll">
              <PdfViewer :pdf-src="pdfSrc" />
            </div>
          </div>
        </div>
      </v-col>
    </v-row>

    <v-dialog v-model="resultDialog" max-width="440">
      <v-card rounded="xl" elevation="8">
        <v-card-item>
          <div class="d-flex align-center">
            <v-icon :color="resultSuccess ? 'success' : 'error'" size="28" class="mr-3">
              {{ resultSuccess ? 'mdi-check-circle' : 'mdi-alert-circle' }}
            </v-icon>
            <v-card-title class="pa-0">
              {{ resultSuccess ? '生成成功' : '生成失败' }}
            </v-card-title>
          </div>
        </v-card-item>
        <v-card-text>
          <p class="text-body-2 mb-4">{{ resultMessage }}</p>
          <div v-if="resultSuccess && resultPath" class="d-flex align-center ga-2">
            <span class="text-caption text-grey-darken-1">输出目录：</span>
            <code class="path-mono">{{ resultPath }}</code>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-btn
            v-if="resultSuccess && resultPath"
            variant="tonal"
            color="primary"
            rounded="lg"
            prepend-icon="mdi-folder-open-outline"
            @click="openFolder(resultPath)"
          >
            打开目录
          </v-btn>
          <v-spacer></v-spacer>
          <v-btn variant="text" rounded="lg" @click="resultDialog = false">确定</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="mergedCellsDialog" max-width="480">
      <v-card>
        <v-card-item>
          <v-card-title class="text-warning">
            <v-icon color="warning" class="mr-2">mdi-alert</v-icon>
            表格格式需要调整
          </v-card-title>
        </v-card-item>
        <v-card-text>
          <p>检测到 Excel 首行存在合并单元格，无法正确解析字段名。</p>
          <p>请取消合并首行单元格，确保每个字段独占一列，然后重新选择文件。</p>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" @click="mergedCellsDialog = false">知道了</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import axios from 'axios'
import { ref, onMounted } from 'vue'
import { invoke } from '@tauri-apps/api/core'
import PdfViewer from '@/components/pdfview/PdfViewer.vue'
import { useBPStore } from '@/stores/bpstore'

const pdfSrc = ref<string>('')
const bpStore = useBPStore()

const mergedCellsDialog = ref(false)
const resetKey = ref(0)

const generating = ref(false)
const resultDialog = ref(false)
const resultSuccess = ref(false)
const resultMessage = ref('')
const resultPath = ref('')

onMounted(() => {
  if (bpStore.pdfSrc) {
    pdfSrc.value = bpStore.pdfSrc
  }
})

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
    if (res.data.has_merged_cells) {
      mergedCellsDialog.value = true
      bpStore.fieldNames = []
      bpStore.excelContent = []
    } else {
      bpStore.fieldNames = res.data.headers
      bpStore.excelContent = res.data.content
    }
  } else {
    alert('请选择有效的Excel文件')
  }
}

const generateBatchPDF = async () => {
  if (!bpStore.pdfFile) {
    resultSuccess.value = false
    resultMessage.value = '请先选择PDF模板'
    resultPath.value = ''
    resultDialog.value = true
    return
  }

  if (!bpStore.excelFile) {
    resultSuccess.value = false
    resultMessage.value = '请先选择Excel数据文件'
    resultPath.value = ''
    resultDialog.value = true
    return
  }

  generating.value = true

  try {
    const formData = new FormData()

    formData.append('pdf_file', bpStore.pdfFile)
    formData.append('excel_file', bpStore.excelFile)
    formData.append('path', bpStore.dataPath || '')
    formData.append('icon_list', JSON.stringify(bpStore.iconList))
    formData.append('pdf_scale', bpStore.pdfScale.toString())

    const res = await axios.post('http://localhost:8000/generate_batch_pdf', formData)

    resultSuccess.value = true
    resultMessage.value = res.data.msg || 'PDF批量生成成功！'
    resultPath.value = res.data.path || ''
    resultDialog.value = true
  } catch (error) {
    console.error('生成PDF失败:', error)
    resultSuccess.value = false
    resultMessage.value = 'PDF批量生成出错，请查看浏览器控制台'
    resultPath.value = ''
    resultDialog.value = true
  } finally {
    generating.value = false
  }
}

async function openFolder(path: string) {
  try {
    await invoke('open_folder', { path })
  } catch (e) {
    console.error('打开文件夹失败:', e)
  }
}

const handleReset = () => {
  pdfSrc.value = ''
  bpStore.pdfSrc = ''
  bpStore.pdfFile = null
  bpStore.excelSrc = ''
  bpStore.excelFile = null
  bpStore.fieldNames = []
  bpStore.excelContent = []
  bpStore.iconList = []
  resetKey.value++
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

.clear-chip {
  cursor: pointer;
  font-weight: 500;
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
  /* 把预览区限制成可收缩的 flex 子项，确保内部滚动不会推动外层布局 */
  flex: 1 1 0;
  height: 0; /* 关键：与父容器的 flex 布局配合，约束高度 */
  min-height: 0;
  display: flex;
  flex-direction: column;
  margin: 0 12px 12px;
  border-radius: 12px;
  overflow: hidden;
  background: rgb(248, 249, 250);
  border: 1px solid rgba(0, 0, 0, 0.04);
  box-sizing: border-box;
}

.preview-scroll {
  /* 占满父高度并由自身滚动 */
  flex: 1 1 0;
  height: 100%;
  min-height: 0;
  overflow: auto;
  overscroll-behavior: contain;
}

.path-mono {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 11px;
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 4px;
  word-break: break-all;
}
</style>
