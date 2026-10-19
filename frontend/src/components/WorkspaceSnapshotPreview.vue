<template>
  <v-dialog
    :model-value="modelValue"
    max-width="900"
    scrollable
    @update:model-value="emit('update:modelValue', $event)"
  >
    <v-card rounded="xl" elevation="8" class="snapshot-card">
      <v-card-item>
        <div class="d-flex align-center">
          <v-icon color="primary" size="22" class="mr-2">mdi-image-search-outline</v-icon>
          <v-card-title class="pa-0 snapshot-title">历史快照</v-card-title>
          <v-spacer />
          <v-btn icon size="small" variant="text" color="grey-darken-1" @click="close">
            <v-icon size="18">mdi-close</v-icon>
          </v-btn>
        </div>
        <v-card-subtitle class="pa-0 mt-1 snapshot-subtitle">
          {{ snapshot.title }} · {{ formatTime(snapshot.savedAt) }}
          <v-chip
            size="x-small"
            variant="tonal"
            class="ml-2"
            :color="snapshot.templateType === 'pdf' ? 'primary' : 'teal'"
          >
            {{ snapshot.templateType === 'pdf' ? 'PDF' : 'DOCX' }}
          </v-chip>
        </v-card-subtitle>
      </v-card-item>

      <v-divider />

      <v-card-text class="snapshot-body">
        <div class="snapshot-files">
          <div class="file-line">
            <v-icon size="14">mdi-file-document-outline</v-icon>
            <span class="file-label">模板</span>
            <span class="file-path" :title="snapshot.templatePath">{{ basename(snapshot.templatePath) }}</span>
          </div>
          <div class="file-line">
            <v-icon size="14">mdi-file-excel</v-icon>
            <span class="file-label">表格</span>
            <span class="file-path" :title="snapshot.excelPath">{{ basename(snapshot.excelPath) }}</span>
          </div>
          <div v-if="snapshot.nameParts?.length" class="file-line">
            <v-icon size="14">mdi-rename-box-outline</v-icon>
            <span class="file-label">文件名</span>
            <code class="name-preview">{{ namePreview }}</code>
          </div>
        </div>

        <!-- PDF：复用预览区的 PdfViewer（只读），按当时坐标展示材料 -->
        <template v-if="snapshot.templateType === 'pdf'">
          <div v-if="fileError" class="snapshot-state">{{ fileError }}</div>
          <div v-else-if="!pdfUrl" class="snapshot-state">
            <v-progress-circular indeterminate size="24" color="primary" />
            <span>正在读取模板快照…</span>
          </div>
          <div v-else class="snapshot-viewer">
            <PdfViewer
              :pdf-src="pdfUrl"
              :preview="pdfPreview"
            />
          </div>
        </template>

        <!-- DOCX：展示保存时的结构与循环块 -->
        <template v-else>
          <div class="snapshot-section">
            <div class="section-heading">
              <v-icon size="15" class="mr-1">mdi-repeat</v-icon>
              循环块（{{ snapshot.loopBlocks.length }}）
            </div>
            <div v-if="snapshot.loopBlocks.length === 0" class="section-empty">未配置循环块</div>
            <div v-else class="loop-list">
              <div v-for="block in snapshot.loopBlocks" :key="block.id" class="loop-item">
                <div class="loop-title">
                  <v-chip size="x-small" variant="tonal" color="teal">
                    {{ block.loopType === 'tableRow' ? '表格行' : '段落' }}
                  </v-chip>
                  <span class="loop-var">{{ block.loopVar }} ← {{ block.listVar }}</span>
                  <span class="loop-range">{{ block.dataRange === 'all' ? '全部行' : `列「${block.rangeColumn ?? ''}」非空` }}</span>
                </div>
                <div v-if="block.conditions?.length" class="loop-cond">
                  {{ formatConditions(block.conditions, block.matchMode) }}
                </div>
              </div>
            </div>
          </div>

          <div class="snapshot-section">
            <div class="section-heading">
              <v-icon size="15" class="mr-1">mdi-format-list-bulleted</v-icon>
              文档结构（{{ snapshot.docxStructure.length }} 项）
            </div>
            <div v-if="snapshot.docxStructure.length === 0" class="section-empty">无结构信息</div>
            <div v-else class="structure-list">
              <div v-for="(item, idx) in snapshot.docxStructure" :key="idx" class="structure-item">
                <v-chip size="x-small" variant="tonal" :color="item.type === 'table' ? 'indigo' : 'grey'">
                  {{ item.type === 'table' ? '表格' : '段落' }}
                </v-chip>
                <span class="structure-text">
                  {{ item.type === 'table' ? `${item.rows?.length ?? 0} 行` : (item.text || '（空段落）') }}
                </span>
              </div>
            </div>
          </div>
        </template>

        <!-- 材料图例（PDF） -->
        <div v-if="snapshot.templateType === 'pdf'" class="snapshot-section">
          <div class="section-heading">
            <v-icon size="15" class="mr-1">mdi-tag-multiple-outline</v-icon>
            材料（{{ snapshot.iconList.length }}）
          </div>
          <div v-if="snapshot.iconList.length === 0" class="section-empty">当时还没有放置材料</div>
          <div v-else class="legend-list">
            <div v-for="(icon, idx) in snapshot.iconList" :key="icon.id ?? idx" class="legend-item">
              <span class="legend-no" :style="{ background: materialColor(icon) }">{{ idx + 1 }}</span>
              <span class="legend-type">{{ materialLabel(icon) }}</span>
              <span class="legend-meta">第 {{ icon.pageIndex }} 页 · 位置 ({{ Math.round(icon.pointer.clientX) }}, {{ Math.round(icon.pointer.clientY) }})</span>
              <span v-if="conditionSummary(icon)" class="legend-cond">{{ conditionSummary(icon) }}</span>
            </div>
          </div>
        </div>

        <div v-if="snapshot.templateType === 'pdf'" class="snapshot-hint">
          提示：预览复用批量打印页的渲染，字段取值来自当前表格文件；若表格已修改，显示内容可能与当时略有差异。
        </div>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import axios from 'axios'
import PdfViewer from '@/components/pdfview/PdfViewer.vue'
import type { StoreIcon, Condition } from '@/types/icon'
import type { WorkspaceSnapshot } from '@/types/workspace'
import { readPathAsFile } from '@/utils/workspace'

const props = defineProps<{
  modelValue: boolean
  snapshot: WorkspaceSnapshot
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()

const pdfUrl = ref('')
const fileError = ref('')
let blobUrl = ''
/** 加载令牌：关闭 / 切换快照时取消过期的异步加载 */
let loadToken = 0

/** 从磁盘表格解析出的字段与首行数据，用于预览时显示字段真实取值 */
const previewFieldNames = ref<string[]>([])
const previewExcelContent = ref<any[][]>([])

async function apiPost(url: string, formData: FormData, retries = 5): Promise<any> {
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

function close() {
  emit('update:modelValue', false)
}

function basename(path: string): string {
  return path ? path.split(/[/\\]/).pop() || path : ''
}

function formatTime(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

const namePreview = computed(() => {
  return (props.snapshot.nameParts || []).map(part => {
    if (part.type === 'field') return `{{${part.field ?? ''}}}`
    if (part.type === 'seq') return `[序号${part.start ?? 1}${part.digits ? `/${part.digits}位` : ''}]`
    return part.text ?? ''
  }).join('')
})

/** 传给 PdfViewer 的只读预览数据；computed 保证引用稳定，避免无谓重绘 */
const pdfPreview = computed(() => ({
  icons: props.snapshot.iconList,
  scale: props.snapshot.pdfScale || 2,
  fieldNames: previewFieldNames.value,
  excelContent: previewExcelContent.value,
}))

function materialColor(icon: StoreIcon): string {
  if (icon.option.type === 'field') return '#2563eb'
  if (icon.option.type === 'text') return '#db2777'
  if (icon.option.type === 'icon') return '#7c3aed'
  return icon.option.imageKind === 'seal' ? '#dc2626' : '#059669'
}

/** 用已解析的表格数据取字段首行真实值，取不到返回空串 */
function fieldValue(fieldName?: string): string {
  if (!fieldName) return ''
  const index = previewFieldNames.value.indexOf(fieldName)
  if (index === -1) return ''
  return String(previewExcelContent.value[0]?.[index] ?? '')
}

function materialLabel(icon: StoreIcon): string {
  switch (icon.option.type) {
    case 'field': {
      const name = icon.option.fieldName || '未命名'
      const value = fieldValue(icon.option.fieldName)
      return value ? `字段：${name} = ${value}` : `字段：${name}`
    }
    case 'image': return icon.option.imageKind === 'seal' ? '印章' : '签字'
    case 'icon': return `图标：${icon.option.icon || ''}`
    case 'text': return `文本：${icon.option.text || ''}`
    default: return '材料'
  }
}

function formatConditions(conditions: Condition[], matchMode?: string): string {
  const format = (c: Condition) => `${c.field ?? ''} ${c.op} ${c.value}`.trim()
  return conditions.map(format).join(matchMode === '任一' ? ' 或 ' : ' 且 ')
}

function conditionSummary(icon: StoreIcon): string {
  if (icon.mode !== 'conditional') return ''
  if (icon.logicType === 'advanced' && icon.groups?.length) {
    const connectors = icon.groupConnectors || []
    return icon.groups
      .map((g, i) => {
        const inner = formatConditions(g.conditions, g.matchMode)
        const wrapped = g.conditions.length > 1 ? `(${inner})` : inner
        return i === 0 ? wrapped : `${connectors[i - 1] ?? '且'} ${wrapped}`
      })
      .join(' ')
  }
  return formatConditions(icon.conditions || [], icon.matchMode)
}

function releasePdf() {
  loadToken += 1
  pdfUrl.value = ''
  previewFieldNames.value = []
  previewExcelContent.value = []
  if (blobUrl) {
    URL.revokeObjectURL(blobUrl)
    blobUrl = ''
  }
}

/** 从磁盘表格解析字段与首行数据；失败时退回占位显示 */
async function loadSnapshotExcel(token: number) {
  try {
    const file = await readPathAsFile(props.snapshot.excelPath)
    if (token !== loadToken || !file) return
    const formData = new FormData()
    formData.append('file', file)
    const res = await apiPost('http://localhost:8000/get_excel_headers', formData)
    if (token !== loadToken) return
    // 合并表头无法直接取列名，退回占位显示
    if (res?.data?.has_merged_cells) return
    previewFieldNames.value = res?.data?.headers ?? []
    previewExcelContent.value = res?.data?.content ?? []
  } catch (error) {
    console.warn('快照预览读取表格失败，字段将用占位显示:', error)
  }
}

async function loadTemplate() {
  releasePdf()
  fileError.value = ''
  if (props.snapshot.templateType !== 'pdf') return

  const token = ++loadToken
  try {
    const file = await readPathAsFile(props.snapshot.templatePath)
    if (token !== loadToken) return
    if (!file) {
      fileError.value = '模板文件已不存在，无法生成快照预览'
      return
    }
    // 先取表格数据，保证首帧就按真实取值渲染
    await loadSnapshotExcel(token)
    if (token !== loadToken) return
    blobUrl = URL.createObjectURL(file)
    pdfUrl.value = blobUrl
  } catch (error) {
    if (token !== loadToken) return
    console.error('读取模板快照失败:', error)
    fileError.value = `快照预览失败：${(error as Error)?.message || '未知错误'}`
  }
}

watch(
  () => [props.modelValue, props.snapshot] as const,
  ([open]) => {
    if (open) void loadTemplate()
    else releasePdf()
  },
  { immediate: true },
)

onBeforeUnmount(releasePdf)
</script>

<style scoped>
.snapshot-title {
  font-size: 0.95rem !important;
  font-weight: 600;
}

.snapshot-subtitle {
  font-size: 0.76rem !important;
  color: rgb(100, 116, 139) !important;
  min-height: 0;
}

.snapshot-body {
  max-height: 72vh;
  overflow-y: auto;
  padding-top: 12px !important;
}

.snapshot-files {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 14px;
  padding: 10px 12px;
  background: rgba(15, 23, 42, 0.03);
  border-radius: 10px;
}

.file-line {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  font-size: 0.76rem;
  color: rgb(71, 85, 105);
}

.file-label {
  flex: none;
  color: rgb(148, 163, 184);
}

.file-path {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 500;
  color: rgb(51, 65, 85);
}

.name-preview {
  font-size: 0.74rem;
  color: rgb(24, 103, 192);
  background: rgba(24, 103, 192, 0.08);
  border-radius: 6px;
  padding: 2px 8px;
}

.snapshot-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 160px;
  font-size: 0.8rem;
  color: #94a3b8;
}

.snapshot-viewer {
  height: 56vh;
  overflow: auto;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 10px;
  background: #f8f9fa;
}

.snapshot-section {
  margin-top: 18px;
}

.section-heading {
  display: flex;
  align-items: center;
  font-size: 0.8rem;
  font-weight: 600;
  color: rgb(30, 41, 59);
  margin-bottom: 8px;
}

.section-empty {
  font-size: 0.76rem;
  color: #94a3b8;
}

.legend-list,
.loop-list,
.structure-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 8px;
  font-size: 0.76rem;
  color: rgb(51, 65, 85);
}

.legend-no {
  flex: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  color: #fff;
  font-size: 0.66rem;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.legend-type {
  flex: none;
  font-weight: 600;
}

.legend-meta {
  flex: 1;
  min-width: 0;
  color: rgb(100, 116, 139);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.legend-cond {
  flex: none;
  color: rgb(190, 24, 93);
  background: rgba(190, 24, 93, 0.08);
  border-radius: 6px;
  padding: 1px 6px;
}

.loop-item,
.structure-item {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 8px;
  font-size: 0.76rem;
  color: rgb(51, 65, 85);
}

.loop-title {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.loop-var {
  font-weight: 600;
}

.loop-range,
.loop-cond {
  color: rgb(100, 116, 139);
}

.loop-cond {
  flex-basis: 100%;
  padding-left: 2px;
  color: rgb(190, 24, 93);
}

.structure-text {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.snapshot-hint {
  margin-top: 16px;
  font-size: 0.72rem;
  color: #94a3b8;
}
</style>
