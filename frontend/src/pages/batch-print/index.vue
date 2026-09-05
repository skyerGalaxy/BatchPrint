<template>
  <v-container fluid class="batch-shell px-6 py-6">
    <v-row class="batch-grid" align="stretch" no-gutters>
      <v-col cols="12" lg="4" class="batch-col pe-lg-3">
        <div class="control-card">
          <div class="card-header">
            <v-icon size="20" color="primary" class="mr-2">mdi-tune-variant</v-icon>
            <span class="card-title">输入输出设置</span>
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
              <div class="section-label">材料</div>
              <div class="material-nav">
                <button
                  v-for="item in materialNavItems"
                  :key="item.value"
                  type="button"
                  class="material-nav-item"
                  :class="[`material-nav-item--${item.value}`, { active: activeMaterialNav === item.value }]"
                  @click="toggleMaterialNav(item.value)"
                >
                  <v-icon size="18">{{ item.icon }}</v-icon>
                  <span>{{ item.title }}</span>
                  <v-icon v-if="item.value === 'table'" size="14" class="material-nav-chevron">
                    {{ activeMaterialNav === 'table' ? 'mdi-chevron-up' : 'mdi-chevron-down' }}
                  </v-icon>
                </button>
              </div>
              <v-expand-transition>
                <div v-if="activeMaterialNav" class="material-panel-host">
                  <MaterialPanel :active-nav="activeMaterialNav" />
                </div>
              </v-expand-transition>
            </div>

            <div class="section filename-section">
              <div class="section-label">文件名</div>

              <div
                ref="nameInputRef"
                class="name-input"
                tabindex="0"
                @click.self="setInsert(nameParts.length)"
                @keydown="handleNameKeydown"
              >
                <template v-for="(part, i) in nameParts" :key="i">
                  <span
                    class="insert-gap"
                    :class="{ 'insert-gap--active': insertIndex === i }"
                    @click.stop="setInsert(i)"
                  ></span>
                  <v-chip
                    :color="partColors[part.type]"
                    :variant="part.type === 'sep' ? 'outlined' : 'tonal'"
                    size="small"
                    closable
                    @click.stop="setInsert(i + 1)"
                    @click:close="removeNamePart(i)"
                  >
                    <v-icon
                      v-if="part.type === 'field' || part.type === 'seq'"
                      start
                      size="12"
                    >
                      {{ partIcons[part.type] }}
                    </v-icon>
                    {{ partLabel(part) }}
                  </v-chip>
                </template>
                <span
                  v-if="nameParts.length > 0"
                  class="insert-gap"
                  :class="{ 'insert-gap--active': insertIndex === nameParts.length }"
                  @click.stop="setInsert(nameParts.length)"
                ></span>

                <span
                  v-if="nameParts.length === 0"
                  class="name-placeholder"
                  @click.stop="setInsert(0)"
                >
                  点击 + 组合文件名，默认按序号命名
                </span>

                <v-menu v-model="addMenuOpen" :close-on-content-click="false">
                  <template #activator="{ props }">
                    <v-btn
                      v-bind="props"
                      icon
                      size="x-small"
                      variant="tonal"
                      color="primary"
                      class="name-add-btn"
                    >
                      <v-icon size="16">mdi-plus</v-icon>
                    </v-btn>
                  </template>

                  <v-list density="compact" min-width="170">
                    <v-list-item :disabled="bpStore.fieldNames.length === 0">
                      <template #prepend>
                        <v-icon size="16">mdi-table-column</v-icon>
                      </template>
                      <v-list-item-title>字段</v-list-item-title>
                      <template #append>
                        <v-icon size="16">mdi-menu-right</v-icon>
                      </template>
                      <v-menu submenu activator="parent" open-on-hover>
                        <v-list density="compact" max-height="280">
                          <v-list-item
                            v-for="fieldName in bpStore.fieldNames"
                            :key="fieldName"
                            @click="addFieldPart(fieldName)"
                          >
                            <v-list-item-title>{{ fieldName }}</v-list-item-title>
                          </v-list-item>
                        </v-list>
                      </v-menu>
                    </v-list-item>

                    <v-list-item>
                      <template #prepend>
                        <v-icon size="16">mdi-numeric</v-icon>
                      </template>
                      <v-list-item-title>自增数字</v-list-item-title>
                      <template #append>
                        <v-icon size="16">mdi-menu-right</v-icon>
                      </template>
                      <v-menu submenu activator="parent" open-on-hover>
                        <v-list density="compact">
                          <v-list-item
                            v-for="opt in seqOptions"
                            :key="opt.digits"
                            @click="addSeqPart(opt.digits)"
                          >
                            <v-list-item-title>{{ opt.title }}</v-list-item-title>
                          </v-list-item>
                        </v-list>
                      </v-menu>
                    </v-list-item>

                    <v-list-item>
                      <template #prepend>
                        <v-icon size="16">mdi-format-text</v-icon>
                      </template>
                      <v-list-item-title>自定义文本</v-list-item-title>
                      <template #append>
                        <v-icon size="16">mdi-menu-right</v-icon>
                      </template>
                      <v-menu submenu activator="parent" :close-on-content-click="false">
                        <v-card class="pa-2" min-width="230">
                          <div class="d-flex align-center ga-2">
                            <v-text-field
                              v-model="customText"
                              density="compact"
                              variant="outlined"
                              hide-details
                              autofocus
                              placeholder="输入文本"
                              class="custom-text-input"
                              @keyup.enter="addTextPart"
                            />
                            <v-btn
                              size="small"
                              color="primary"
                              variant="tonal"
                              :disabled="!customText"
                              @click="addTextPart"
                            >
                              添加
                            </v-btn>
                          </div>
                        </v-card>
                      </v-menu>
                    </v-list-item>

                    <v-list-item>
                      <template #prepend>
                        <v-icon size="16">mdi-minus</v-icon>
                      </template>
                      <v-list-item-title>连接符</v-list-item-title>
                      <template #append>
                        <v-icon size="16">mdi-menu-right</v-icon>
                      </template>
                      <v-menu submenu activator="parent" open-on-hover>
                        <v-list density="compact">
                          <v-list-item
                            v-for="sep in sepOptions"
                            :key="sep.value"
                            @click="addSepPart(sep.value)"
                          >
                            <v-list-item-title>{{ sep.title }}</v-list-item-title>
                          </v-list-item>
                        </v-list>
                      </v-menu>
                    </v-list-item>
                  </v-list>
                </v-menu>
              </div>

              <div class="name-preview">
                <span class="preview-label">预览</span>
                <span class="path-mono">{{ fileNamePreview }}</span>
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
              {{ resultSuccess ? '生成成功' : '提示' }}
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

    <v-dialog v-model="excelErrorDialog" max-width="440">
      <v-card>
        <v-card-item>
          <div class="d-flex align-center">
            <v-icon color="error" size="28" class="mr-3">mdi-alert-circle</v-icon>
            <v-card-title class="pa-0">解析失败</v-card-title>
          </div>
        </v-card-item>
        <v-card-text>
          <p class="text-body-2">{{ excelErrorMessage }}</p>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" @click="excelErrorDialog = false">确定</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import axios from 'axios'
import { ref, computed, onMounted } from 'vue'
import { invoke } from '@tauri-apps/api/core'
import PdfViewer from '@/components/pdfview/PdfViewer.vue'
import { useBPStore } from '@/stores/bpstore'

const pdfSrc = ref<string>('')
const bpStore = useBPStore()

const activeMaterialNav = ref('table')
const materialNavItems = [
  { title: '表格', value: 'table', icon: 'mdi-table' },
  { title: '签字', value: 'signature', icon: 'mdi-draw-pen' },
  { title: '印章', value: 'seal', icon: 'mdi-seal-variant' },
  { title: '图标', value: 'icon', icon: 'mdi-shape-outline' },
  { title: '文本', value: 'text', icon: 'mdi-format-text' },
]

const toggleMaterialNav = (value: string) => {
  activeMaterialNav.value = value === 'table' && activeMaterialNav.value === 'table' ? '' : value
}

const mergedCellsDialog = ref(false)
const excelErrorDialog = ref(false)
const excelErrorMessage = ref('')
const resetKey = ref(0)

const generating = ref(false)
const resultDialog = ref(false)
const resultSuccess = ref(false)
const resultMessage = ref('')
const resultPath = ref('')

interface NamePart {
  type: 'field' | 'seq' | 'text' | 'sep'
  field?: string
  start?: number
  digits?: number
  text?: string
}

const nameParts = ref<NamePart[]>([])
const addMenuOpen = ref(false)
const customText = ref('')
const insertIndex = ref(0)
const nameInputRef = ref<HTMLElement | null>(null)

const setInsert = (index: number) => {
  insertIndex.value = Math.max(0, Math.min(index, nameParts.value.length))
  nameInputRef.value?.focus()
}

const insertPart = (part: NamePart) => {
  const idx = Math.max(0, Math.min(insertIndex.value, nameParts.value.length))
  nameParts.value.splice(idx, 0, part)
  insertIndex.value = idx + 1
  addMenuOpen.value = false
  nameInputRef.value?.focus()
}

const partIcons: Partial<Record<NamePart['type'], string>> = {
  field: 'mdi-table-column',
  seq: 'mdi-numeric',
}

const partColors: Record<NamePart['type'], string> = {
  field: 'primary',
  seq: 'teal',
  text: 'orange',
  sep: 'grey',
}

const seqOptions = [
  { title: '1, 2, 3 …', digits: 0 },
  { title: '01, 02, 03 …', digits: 2 },
  { title: '001, 002, 003 …', digits: 3 },
  { title: '0001, 0002, 0003 …', digits: 4 },
]

const sepOptions = [
  { title: '下划线 _', value: '_' },
  { title: '连字符 -', value: '-' },
  { title: '点 .', value: '.' },
  { title: '空格', value: ' ' },
]

const partLabel = (part: NamePart): string => {
  if (part.type === 'field') return part.field || ''
  if (part.type === 'seq') {
    return part.digits ? `${'1'.padStart(part.digits, '0')}…` : '1,2,3…'
  }
  if (part.type === 'sep') return part.text === ' ' ? '空格' : part.text || ''
  return part.text || ''
}

const addFieldPart = (fieldName: string) => {
  insertPart({ type: 'field', field: fieldName })
}

const addSeqPart = (digits: number) => {
  insertPart({ type: 'seq', start: 1, digits })
}

const addTextPart = () => {
  if (!customText.value) return
  insertPart({ type: 'text', text: customText.value })
  customText.value = ''
}

const addSepPart = (value: string) => {
  insertPart({ type: 'sep', text: value })
}

const normalizeSeps = () => {
  const parts = nameParts.value
  for (let i = parts.length - 1; i >= 0; i--) {
    if (parts[i].type !== 'sep') continue
    if (i === 0 || i === parts.length - 1 || parts[i - 1].type === 'sep') {
      parts.splice(i, 1)
      if (insertIndex.value > i) {
        insertIndex.value--
      }
    }
  }
}

const removeNamePart = (index: number) => {
  const parts = nameParts.value
  parts.splice(index, 1)
  if (insertIndex.value > index) {
    insertIndex.value--
  }
  nameInputRef.value?.focus()
}

const handleNameKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Backspace') {
    if (insertIndex.value > 0) {
      removeNamePart(insertIndex.value - 1)
    }
    e.preventDefault()
  } else if (e.key === 'Delete') {
    if (insertIndex.value < nameParts.value.length) {
      removeNamePart(insertIndex.value)
    }
    e.preventDefault()
  } else if (e.key === 'ArrowLeft') {
    setInsert(insertIndex.value - 1)
    e.preventDefault()
  } else if (e.key === 'ArrowRight') {
    setInsert(insertIndex.value + 1)
    e.preventDefault()
  }
}

const buildFileName = (rowIndex: number): string => {
  const row = bpStore.excelContent[rowIndex] || []
  return nameParts.value
    .map(part => {
      if (part.type === 'field') {
        const idx = bpStore.fieldNames.indexOf(part.field || '')
        const val = idx >= 0 ? row[idx] : undefined
        return val === null || val === undefined ? (part.field ? `{${part.field}}` : '') : String(val)
      }
      if (part.type === 'seq') {
        const num = (part.start ?? 1) + rowIndex
        return part.digits ? String(num).padStart(part.digits, '0') : String(num)
      }
      return part.text || ''
    })
    .join('')
}

const fileNamePreview = computed(() => {
  const name = buildFileName(0)
  return (name || '1') + '.pdf'
})

async function apiPost(url: string, formData: FormData, retries = 30): Promise<any> {
  for (let i = 0; i < retries; i++) {
    try {
      return await axios.post(url, formData)
    } catch {
      if (i < retries - 1) {
        await new Promise(r => setTimeout(r, 1000))
      } else {
        throw new Error(`无法连接后端服务: ${url}`)
      }
    }
  }
}

onMounted(() => {
  if (bpStore.pdfSrc) {
    pdfSrc.value = bpStore.pdfSrc
  }
})

const handleFileChange = async (value: File | File[] | null) => {
  const file = Array.isArray(value) ? value[0] : value

  if (file && file.type === 'application/pdf') {
    bpStore.iconList = []
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
  bpStore.fieldNames = []
  bpStore.excelContent = []

  if (
    file &&
    (file.type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' ||
      file.type === 'application/vnd.ms-excel')
  ) {
    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await apiPost('http://localhost:8000/get_excel_headers', formData)
      if (res.data.has_merged_cells) {
        mergedCellsDialog.value = true
      } else {
        bpStore.fieldNames = res.data.headers
        bpStore.excelContent = res.data.content
        nameParts.value = nameParts.value.filter(
          p => p.type !== 'field' || bpStore.fieldNames.includes(p.field || '')
        )
        insertIndex.value = Math.min(insertIndex.value, nameParts.value.length)
        normalizeSeps()
      }
    } catch (e: any) {
      excelErrorMessage.value = e.message || '无法解析 Excel 文件，请检查后端服务是否正常'
      excelErrorDialog.value = true
    }
  } else if (file) {
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

  if (bpStore.iconList.length === 0) {
    resultSuccess.value = false
    resultMessage.value = '请先在PDF模板上放置图章/签名标注，图标列表为空'
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
    formData.append(
      'filename_config',
      JSON.stringify({ parts: nameParts.value, separator: '' })
    )

    const res = await apiPost('http://localhost:8000/generate_batch_pdf', formData)

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
  nameParts.value = []
  customText.value = ''
  insertIndex.value = 0
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
  grid-template-rows: auto auto minmax(0, 1fr) auto auto;
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

.material-nav {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 4px;
}

.material-nav-item {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  min-width: 0;
  min-height: 34px;
  padding: 4px 5px;
  border: 1px solid transparent;
  border-radius: 8px;
  background: color-mix(in srgb, var(--material-color) 8%, white);
  color: var(--material-color);
  cursor: pointer;
  font: inherit;
  font-size: 0.72rem;
  font-weight: 600;
  transition: background 0.15s, border-color 0.15s, transform 0.15s;
}

.material-nav-item:hover,
.material-nav-item.active {
  background: color-mix(in srgb, var(--material-color) 16%, white);
  border-color: color-mix(in srgb, var(--material-color) 30%, white);
  transform: translateY(-1px);
}

.material-nav-item--table { --material-color: #2563eb; }
.material-nav-item--signature { --material-color: #0f766e; }
.material-nav-item--seal { --material-color: #c2410c; }
.material-nav-item--icon { --material-color: #7c3aed; }
.material-nav-item--text { --material-color: #be185d; }

.material-nav-item span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.material-nav-chevron {
  margin-left: -2px;
}

.material-panel-host {
  min-height: 150px;
  margin-top: 8px;
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

/* ---- filename ---- */
.filename-section {
  overflow-y: auto;
  max-height: 220px;
  overscroll-behavior: contain;
}

.name-input {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 2px;
  min-height: 46px;
  padding: 8px 10px;
  border: 1px solid rgba(0, 0, 0, 0.16);
  border-radius: 8px;
  transition: border-color 0.15s;
  cursor: text;
}

.name-input:hover {
  border-color: rgba(0, 0, 0, 0.4);
}

.name-input:focus {
  outline: none;
  border-color: rgb(var(--v-theme-primary));
}

.insert-gap {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 9px;
  height: 26px;
  cursor: text;
  flex: 0 0 auto;
}

.insert-gap::after {
  content: '';
  width: 2px;
  height: 18px;
  border-radius: 1px;
  background: transparent;
  transition: background 0.1s;
}

.insert-gap:hover::after {
  background: rgba(0, 0, 0, 0.2);
}

.insert-gap--active::after {
  background: rgb(var(--v-theme-primary));
  animation: caret-blink 1s step-end infinite;
}

@keyframes caret-blink {
  50% {
    opacity: 0;
  }
}

.name-placeholder {
  font-size: 0.78rem;
  color: rgb(148, 163, 184);
  cursor: text;
}

.name-add-btn {
  margin-left: auto;
}

.custom-text-input {
  min-width: 130px;
}

.name-preview {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  padding: 6px 10px;
  background: rgb(248, 250, 252);
  border: 1px dashed rgba(0, 0, 0, 0.08);
  border-radius: 8px;
  min-width: 0;
}

.preview-label {
  flex: 0 0 auto;
  font-size: 0.68rem;
  font-weight: 600;
  color: rgb(148, 163, 184);
  letter-spacing: 0.04em;
}

.name-preview .path-mono {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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
