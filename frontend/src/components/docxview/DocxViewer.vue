<template>
  <div ref="containerRef" class="docx-container">
    <div v-if="!bpStore.docxFile || !docBytes" class="empty-tip">
      请先选择 DOCX 模板
    </div>
    <div
      v-else
      ref="hostRef"
      class="docx-host"
      @dragover.capture="onDragOver"
      @drop.capture="onDrop"
      @dragleave.capture="onDragLeave"
      @contextmenu.capture="onContextMenu"
    >
      <LocaleProvider :i18n="zhCN">
        <DocxEditorRoot
          :key="fileKey"
          :document="docBytes"
          mode="edit"
          locale="zh-CN"
          :popups="editorPopups"
          @ready="onEditorReady"
        >
          <div class="docx-editor bp-docx-frame">
            <!-- 编辑栏：仅保留 撤销/重做/段落样式/字体/字号/粗斜下划线删除线/颜色/高亮/对齐/缩进/格式刷/清除格式 -->
            <div class="bp-docx-topbar">
              <div class="bp-docx-toolbar-wrap">
                <DocxEditorToolbar :preset="false" :overflow="false">
                  <DocxEditorToolbar.Undo />
                  <DocxEditorToolbar.Redo />
                  <DocxEditorToolbar.Separator />
                  <DocxEditorToolbar.StylePicker />
                  <DocxEditorToolbar.FontFamily />
                  <DocxEditorToolbar.FontSize />
                  <DocxEditorToolbar.Separator />
                  <DocxEditorToolbar.Bold />
                  <DocxEditorToolbar.Italic />
                  <DocxEditorToolbar.Underline />
                  <DocxEditorToolbar.Strike />
                  <DocxEditorToolbar.FontColor />
                  <DocxEditorToolbar.Highlight />
                  <DocxEditorToolbar.Separator />
                  <DocxEditorToolbar.Alignment />
                  <DocxEditorToolbar.Outdent />
                  <DocxEditorToolbar.Indent />
                  <DocxEditorToolbar.Separator />
                  <DocxEditorToolbar.Button slot="format.painter" />
                  <DocxEditorToolbar.ClearFormatting />
                </DocxEditorToolbar>
              </div>
            </div>
            <DocxEditorFontNotice />
            <div class="bp-docx-body">
              <DocxEditorViewport class="bp-docx-viewport" :style="viewportStyle">
                <DocxEditorHeaderFooterChrome />
                <DocxEditorNotesChrome />
                <DocxEditorContent />
              </DocxEditorViewport>
              <DocxEditorLoading overlay />
            </div>
          </div>
        </DocxEditorRoot>
      </LocaleProvider>
    </div>
  </div>
</template>

<script setup lang="ts">
import { h, ref, shallowRef, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import {
  DocxEditor,
  DocxEditorRoot,
  DocxEditorViewport,
  DocxEditorContent,
  DocxEditorToolbar,
  DocxEditorLoading,
  DocxEditorFontNotice,
  DocxEditorHeaderFooterChrome,
  DocxEditorNotesChrome,
  LocaleProvider,
} from '@docx-editor.dev/vue'
import type { DocxEditorPopups } from '@docx-editor.dev/vue'
import type { DocxEditorInstance } from '@docx-editor.dev/core/editor'
import {
  createBrowserAutomationHost,
  executeImageCommand,
  sniffImageMime,
} from '@docx-editor.dev/core/editor'
import type { Editor } from '@docx-editor.dev/core/contracts/editor'
import type {
  AutomationHost,
  AutomationHandle,
  AutomationOperationResult,
} from '@docx-editor.dev/core/automation'
import zhCN from '@docx-editor.dev/i18n/zh-CN'
import '@docx-editor.dev/vue/styles.css'
import { useBPStore } from '@/stores/bpstore'
import type { IconOption } from '@/types/icon'

const bpStore = useBPStore()
const containerRef = ref<HTMLElement | null>(null)
const hostRef = ref<HTMLElement | null>(null)

const docBytes = ref<Uint8Array | null>(null)
const fileKey = ref(0)
const editorInstance = shallowRef<DocxEditorInstance | null>(null)
/**
 * 实时编辑器上的 automation host：字段控件插入后，需要通过它把内容控件
 * 锁成 contentLocked（内容不可编辑，但整个控件可删除）。
 */
const automationHost = shallowRef<AutomationHost | null>(null)
/** body 句柄在同一 host 生命周期内稳定，缓存避免每次拖放都走两轮查询 */
let bodyHandle: AutomationHandle | null = null

/**
 * 组合式挂载时手动补齐糖组件默认的弹窗（超链接/内容控件/公式/右键菜单），
 * 与原 <DocxEditor> 默认行为一致。
 */
const editorPopups: DocxEditorPopups = {
  hyperlink: (props) => h(DocxEditor.HyperLink, props),
  contentControl: (props) => h(DocxEditor.ContentControl, props),
  equation: () => h(DocxEditor.Equation),
  contextMenu: (props) => h(DocxEditor.ContextMenu, props),
}

function onEditorReady(editor: Editor) {
  automationHost.value?.dispose()
  bodyHandle = null
  // ready 回调的声明类型是核心 Editor，运行时实际是带 surface 的完整实例
  const instance = editor as DocxEditorInstance
  editorInstance.value = instance
  automationHost.value = createBrowserAutomationHost(instance)
}

/** 与糖组件 Frame 中视口的内联样式保持一致：必须 flex:1 + min-width:0，
 *  否则 flex 项按内容收缩，引擎会按错误的窄宽度适配缩放页面 */
const viewportStyle = {
  flex: 1,
  minHeight: 0,
  minWidth: 0,
  overflowAnchor: 'none',
} as const

const emit = defineEmits<{
  (e: 'contextmenu-block', payload: { anchorId: string; loopType: 'paragraph' | 'tableRow' }): void
}>()

/* ========= 模板字节加载 ========= */
async function loadDocx(file: File) {
  const buf = await file.arrayBuffer()
  docBytes.value = new Uint8Array(buf)
  fileKey.value += 1
}

watch(() => bpStore.docxFile, (file) => {
  if (file) {
    loadDocx(file)
  } else {
    docBytes.value = null
  }
})

/* ========= 编辑器 DOM 锚点映射 =========
 * 编辑器（eigenpal docx-editor）正文结构：
 *   .docx-pages > .docx-page > .docx-page-content
 *     .docx-paragraph-fragment[data-paragraph-id][data-fragment-index]
 *     .layout-table[data-table-id] > .docx-table-row[data-row-id] > .docx-table-cell
 * 段落会跨页拆成多个 fragment（同一 paragraphId），单元格内段落位于 .docx-table-cell 内，
 * 页眉页脚位于 .docx-hf 内。后端 anchorId 语义：p_XXXX 为正文 body 下直接段落序号，
 * tr_XXXX_YYYY 为表格序号_行序号，因此这里按文档顺序去重枚举。
 */

interface AnchorMaps {
  /** body 直接段落 paragraphId -> 段落序号 */
  paragraphOrdinal: Map<string, number>
  /** tableId -> 表格序号 */
  tableOrdinal: Map<string, number>
  /** rowId -> { table 序号, 行序号 } */
  rowOrdinal: Map<string, { t: number; r: number }>
}

const pad4 = (n: number) => String(n).padStart(4, '0')

function isInHfOrCell(el: Element): boolean {
  return !!el.closest('.docx-hf') || !!el.closest('.docx-table-cell')
}

function buildAnchorMaps(): AnchorMaps {
  const host = hostRef.value
  const paragraphOrdinal = new Map<string, number>()
  const tableOrdinal = new Map<string, number>()
  const rowOrdinal = new Map<string, { t: number; r: number }>()
  if (!host) return { paragraphOrdinal, tableOrdinal, rowOrdinal }

  // 正文段落：fragment 元素、去重（跨页拆分）、保持文档顺序
  host.querySelectorAll<HTMLElement>('.docx-paragraph-fragment[data-paragraph-id]').forEach((el) => {
    const id = el.dataset.paragraphId || ''
    if (!id || isInHfOrCell(el) || paragraphOrdinal.has(id)) return
    paragraphOrdinal.set(id, paragraphOrdinal.size)
  })

  // 表格：跨页片段共享 tableId，去重保序
  const tables: HTMLElement[] = []
  host.querySelectorAll<HTMLElement>('.layout-table[data-table-id]').forEach((el) => {
    if (el.closest('.docx-hf')) return
    const id = el.dataset.tableId || ''
    if (id && !tables.some(t => t.dataset.tableId === id)) tables.push(el)
  })
  tables.forEach((tbl, tIdx) => {
    const tableId = tbl.dataset.tableId || ''
    tableOrdinal.set(tableId, tIdx)
    let rIdx = 0
    host.querySelectorAll<HTMLElement>('.docx-table-row[data-row-id]').forEach((row) => {
      const ownerTable = row.closest('.layout-table') as HTMLElement | null
      if (!ownerTable || ownerTable.dataset.tableId !== tableId) return
      const rowId = row.dataset.rowId || ''
      if (!rowId || rowOrdinal.has(rowId)) return
      rowOrdinal.set(rowId, { t: tIdx, r: rIdx })
      rIdx += 1
    })
  })

  return { paragraphOrdinal, tableOrdinal, rowOrdinal }
}

type DropTarget = {
  loopType: 'paragraph' | 'tableRow'
  anchorId: string
  /** 高亮用元素 */
  el: HTMLElement
  /** 引擎内部段落 id（data-paragraph-id），用于 setSelection 兜底 */
  paragraphId: string
  /** 段落内字符偏移（仅 body 段落有意义） */
  charOffset: number
}

/** 同一段落跨页的全部 fragment，按 fragmentIndex 排序 */
function fragmentsOfParagraph(paragraphId: string): HTMLElement[] {
  const host = hostRef.value
  if (!host) return []
  return Array.from(
    host.querySelectorAll<HTMLElement>('.docx-paragraph-fragment[data-paragraph-id]'),
  )
    .filter(el => el.dataset.paragraphId === paragraphId)
    .sort((a, b) => Number(a.dataset.fragmentIndex || 0) - Number(b.dataset.fragmentIndex || 0))
}

/** 收集元素内可见文本节点（排除 aria-hidden 的段落标记/列表标记等） */
function visibleTextNodes(root: HTMLElement): Text[] {
  const nodes: Text[] = []
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT)
  let node: Node | null
  while ((node = walker.nextNode())) {
    const parent = (node as Text).parentElement
    if (parent && parent.closest('[aria-hidden="true"]')) continue
    if ((node as Text).textContent) nodes.push(node as Text)
  }
  return nodes
}

/**
 * 在段落 fragment 内按字符矩形命中测试，计算落点字符偏移；
 * 再累加更早 fragment 的文本长度，得到整段内偏移（与后端 paragraph.text 偏移对齐）。
 */
function resolveCharOffset(frag: HTMLElement, x: number, y: number): number {
  const paragraphId = frag.dataset.paragraphId || ''
  const fragments = fragmentsOfParagraph(paragraphId)

  let base = 0
  for (const f of fragments) {
    if (f === frag) break
    base += visibleTextNodes(f).reduce((sum, tn) => sum + (tn.textContent?.length || 0), 0)
  }

  const textNodes = visibleTextNodes(frag)
  let hit: { offset: number; dist: number } | null = null

  for (const tn of textNodes) {
    const len = tn.textContent?.length || 0
    for (let i = 0; i < len; i++) {
      const range = document.createRange()
      range.setStart(tn, i)
      range.setEnd(tn, i + 1)
      const rect = range.getClientRects()[0]
      if (!rect) continue
      const inside = x >= rect.left && x <= rect.right && y >= rect.top && y <= rect.bottom
      if (inside) {
        const mid = rect.left + rect.width / 2
        hit = { offset: base + prefixLength(textNodes, tn) + i + (x >= mid ? 1 : 0), dist: 0 }
        break
      }
      if (!hit || hit.dist === 0) {
        // 同行最近字符兜底
        if (y >= rect.top - rect.height && y <= rect.bottom + rect.height) {
          const dist = Math.min(Math.abs(x - rect.left), Math.abs(x - rect.right))
          if (!hit || dist < hit.dist) {
            hit = { offset: base + prefixLength(textNodes, tn) + i + (x > rect.right ? 1 : 0), dist }
          }
        }
      }
    }
    if (hit?.dist === 0) break
  }

  if (hit) return hit.offset
  // 落点不在任何字符上时，按文本末尾处理
  return base + textNodes.reduce((sum, tn) => sum + (tn.textContent?.length || 0), 0)
}

function prefixLength(textNodes: Text[], current: Text): number {
  let sum = 0
  for (const tn of textNodes) {
    if (tn === current) break
    sum += tn.textContent?.length || 0
  }
  return sum
}

/** 根据坐标解析正文段落 / 表格行目标 */
function resolveTarget(x: number, y: number): DropTarget | null {
  const host = hostRef.value
  if (!host) return null
  const el = document.elementFromPoint(x, y) as HTMLElement | null
  if (!el || !host.contains(el)) return null

  const frag = el.closest('.docx-paragraph-fragment') as HTMLElement | null
  if (frag) {
    const paragraphId = frag.dataset.paragraphId || ''
    const maps = buildAnchorMaps()
    const row = el.closest('.docx-table-row') as HTMLElement | null

    if (frag.closest('.docx-table-cell') && row) {
      // 单元格内：按表格行处理（后端图片/字段定位以正文段落为主，行内落点偏移取 0）
      const rowId = row.dataset.rowId || ''
      const pos = maps.rowOrdinal.get(rowId)
      if (!pos) return null
      return {
        loopType: 'tableRow',
        anchorId: `tr_${pad4(pos.t)}_${pad4(pos.r)}`,
        el: row,
        paragraphId,
        charOffset: resolveCharOffset(frag, x, y),
      }
    }

    if (frag.closest('.docx-hf')) return null
    const ordinal = maps.paragraphOrdinal.get(paragraphId)
    if (ordinal === undefined) return null
    return {
      loopType: 'paragraph',
      anchorId: `p_${pad4(ordinal)}`,
      el: frag,
      paragraphId,
      charOffset: resolveCharOffset(frag, x, y),
    }
  }

  const row = el.closest('.docx-table-row') as HTMLElement | null
  if (row && !row.closest('.docx-hf')) {
    const maps = buildAnchorMaps()
    const pos = maps.rowOrdinal.get(row.dataset.rowId || '')
    if (!pos) return null
    const cellFrag = row.querySelector<HTMLElement>('.docx-paragraph-fragment[data-paragraph-id]')
    return {
      loopType: 'tableRow',
      anchorId: `tr_${pad4(pos.t)}_${pad4(pos.r)}`,
      el: row,
      paragraphId: cellFrag?.dataset.paragraphId || '',
      charOffset: 0,
    }
  }

  return null
}

/* ========= 拖放（捕获阶段拦截，避免触发编辑器自身 drop） ========= */
let dragOverTarget: HTMLElement | null = null

function clearDragOver() {
  dragOverTarget?.classList.remove('bp-drag-over')
  dragOverTarget = null
}

function hasOurPayload(e: DragEvent): boolean {
  return !!e.dataTransfer?.types?.includes('application/x-batchprint-option')
}

function onDragOver(e: DragEvent) {
  if (!hasOurPayload(e)) return
  e.preventDefault()
  e.stopPropagation()
  if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy'
  const target = resolveTarget(e.clientX, e.clientY)
  if (target?.el !== dragOverTarget) {
    clearDragOver()
    dragOverTarget = target?.el || null
    dragOverTarget?.classList.add('bp-drag-over')
  }
}

function onDragLeave(e: DragEvent) {
  if (!hasOurPayload(e)) return
  const related = e.relatedTarget as Node | null
  if (related && hostRef.value?.contains(related)) return
  clearDragOver()
}

async function onDrop(e: DragEvent) {
  if (!hasOurPayload(e)) return
  e.preventDefault()
  e.stopPropagation()
  clearDragOver()
  const raw = e.dataTransfer?.getData('application/x-batchprint-option')
  if (!raw) return
  const target = resolveTarget(e.clientX, e.clientY)
  if (!target) return
  let option: IconOption
  try {
    const payload = JSON.parse(raw) as { option?: IconOption }
    if (!payload.option) return
    option = payload.option
  } catch (err) {
    console.error('解析 DOCX 拖放数据失败:', err)
    return
  }

  const editor = editorInstance.value
  if (!editor) return

  // 1) 先把光标移动到落点：优先派发合成 pointer 事件让引擎自己做命中测试，
  //    失败时用段落 id + 字符偏移兜底
  if (!placeCaretFromPointer(e.clientX, e.clientY)) {
    if (!target.paragraphId) return
    const r = editor.exec({
      type: 'setSelection',
      range: {
        anchor: { paragraphId: target.paragraphId, offset: target.charOffset },
        head: { paragraphId: target.paragraphId, offset: target.charOffset },
      },
    })
    if (!r.ok) {
      console.error('拖放定位光标失败:', r.reason)
      return
    }
  }

  // 2) 按材料类型真正写入编辑器文档
  try {
    if (option.type === 'field') {
      insertFieldChip(option)
    } else if (option.type === 'image') {
      await insertFloatingImage(option)
    } else if (option.type === 'icon' && option.icon) {
      // 图标按普通字符插入（与键入一致）
      editor.exec({ type: 'insertText', text: option.icon })
    }
  } catch (err) {
    console.error('写入 DOCX 拖放内容失败:', err)
  }
}

/* ========= 拖入内容的真实写入 ========= */

/**
 * 派发合成 pointerdown，让编辑器自身的命中测试在落点放置光标。
 * 编辑器不监听 HTML5 drop，drop 本身不会移动 caret。
 */
function placeCaretFromPointer(x: number, y: number): boolean {
  const host = hostRef.value
  const editor = editorInstance.value
  if (!host || !editor) return false
  const el = document.elementFromPoint(x, y)
  if (!el || !host.contains(el)) return false
  const init: PointerEventInit = {
    clientX: x,
    clientY: y,
    button: 0,
    buttons: 1,
    bubbles: true,
    cancelable: true,
    pointerId: 1,
    pointerType: 'mouse',
    isPrimary: true,
  }
  try {
    el.dispatchEvent(new PointerEvent('pointerdown', init))
    el.dispatchEvent(new PointerEvent('pointerup', { ...init, buttons: 0 }))
  } catch {
    return false
  }
  // 引擎的 pointerdown 命中测试会把光标放到坐标命中的位置（调用方已确认落点在正文
  // 段落/表格行上）；有选区即认为落点成功，否则由调用方走 setSelection 兜底
  return !!editor.query({ type: 'selection' })
}

/* ---------- 字段：plainText 内容控件 + 内容锁定 ---------- */

/** 字段控件统一 tag 前缀，后端渲染后据此把控件解包成普通文本 */
const FIELD_TAG_PREFIX = 'bpf_'
let fieldSeq = 0

function insertFieldChip(option: IconOption) {
  const editor = editorInstance.value
  if (!editor || !option.fieldName) return
  const tag = `${FIELD_TAG_PREFIX}${Date.now().toString(36)}_${(++fieldSeq).toString(36)}`

  // collapsed caret 处插入空的纯文本内容控件（target 省略 = 当前选区）
  const inserted = editor.exec({
    type: 'insertContentControl',
    subtype: 'plainText',
    tag,
    title: option.fieldName,
  })
  if (!inserted.ok) {
    console.error('插入字段控件失败:', inserted.reason)
    return
  }

  fillAndLockFieldControl(tag, `{{${option.fieldName}}}`)
}

/**
 * 通过 automation host 按 tag 找回刚插入的控件，写入 docxtpl 占位符并锁为
 * contentLocked（内容不可改，控件整体可删除）。同一批次提交，共用一个撤销单元。
 */
function fillAndLockFieldControl(tag: string, placeholder: string) {
  const host = automationHost.value
  if (!host) return
  try {
    const body = getBodyHandle(host)
    if (!body) {
      console.warn('字段控件未写入：无法取得文档 body 句柄')
      return
    }
    const found = host.execute({
      operations: [{ op: 'getContentControlsByTag', scope: { body }, tag }],
    })
    const handle = firstHandle(found, 0)
    if (!handle) {
      console.warn('字段控件未写入：按 tag 未找到控件')
      return
    }
    const written = host.execute({
      operations: [
        { op: 'setContentControlValue', contentControl: handle, value: { kind: 'text', text: placeholder } },
        { op: 'setContentControlProperties', contentControl: handle, lock: 'contentLocked' },
      ],
    })
    if (!written.ok) console.warn('字段控件写入/锁定失败:', written.results)
  } catch (err) {
    console.warn('字段控件写入异常:', err)
  }
}

function getBodyHandle(host: AutomationHost): AutomationHandle | null {
  if (bodyHandle) return bodyHandle
  const docRes = host.execute({ operations: [{ op: 'getDocument' }] })
  const doc = singleHandle(docRes, 0)
  if (!doc) return null
  const bodyRes = host.execute({ operations: [{ op: 'getBody', document: doc }] })
  bodyHandle = singleHandle(bodyRes, 0)
  return bodyHandle
}

function singleHandle(
  res: { ok: boolean; results: readonly AutomationOperationResult[] },
  index: number,
): AutomationHandle | null {
  const item = res.results[index]
  if (item && item.status === 'ok' && item.value.kind === 'handle') return item.value.handle
  return null
}

function firstHandle(
  res: { ok: boolean; results: readonly AutomationOperationResult[] },
  index: number,
): AutomationHandle | null {
  const item = res.results[index]
  if (item && item.status === 'ok') {
    if (item.value.kind === 'handle') return item.value.handle
    if (item.value.kind === 'handles') return item.value.handles[0] ?? null
  }
  return null
}

/* ---------- 图片：插入内联后提升为“浮于文字上方” ---------- */

const SUPPORTED_IMAGE_MIMES = new Set(['image/png', 'image/jpeg', 'image/gif', 'image/bmp', 'image/webp'])

async function insertFloatingImage(option: IconOption) {
  const editor = editorInstance.value
  if (!editor || !option.src) return

  const resp = await fetch(option.src)
  if (!resp.ok) throw new Error(`图片读取失败: HTTP ${resp.status}`)
  const bytes = new Uint8Array(await resp.arrayBuffer())

  const sniffed = sniffImageMime(bytes)
  if (!SUPPORTED_IMAGE_MIMES.has(sniffed)) {
    console.error('不支持的图片格式:', sniffed)
    return
  }
  const mime = sniffed as 'image/png' | 'image/jpeg' | 'image/gif' | 'image/bmp' | 'image/webp'

  // 自然尺寸：按 option.size(px, @96dpi) 折算磅，并保持宽高比
  const natural = await loadNaturalSize(option.src)
  const maxWidthPt = (option.size ?? 120) * 0.75
  let widthPoints = maxWidthPt
  let heightPoints = maxWidthPt
  if (natural && natural.w > 0 && natural.h > 0) {
    heightPoints = widthPoints * natural.h / natural.w
  }

  const result = await executeImageCommand(editor, {
    type: 'insertImage',
    data: bytes,
    mime,
    widthPoints,
    heightPoints,
  })
  if (!result.ok) {
    console.error('插入图片失败:', result.reason)
    return
  }

  // 选中态即新插入图片；提升为浮于文字上方，之后拖动/缩放由编辑器原生 chrome 提供
  const selected = editor.getSelectedImage()
  const wrapped = editor.exec({
    type: 'setImageWrapType',
    target: 'inFront',
    ...(selected ? { drawingNodeId: selected.id } : {}),
  })
  if (!wrapped.ok) console.error('图片浮动设置失败:', wrapped.reason)
}

function loadNaturalSize(url: string): Promise<{ w: number; h: number } | null> {
  return new Promise((resolve) => {
    const img = new Image()
    img.onload = () => resolve({ w: img.naturalWidth, h: img.naturalHeight })
    img.onerror = () => resolve(null)
    img.src = url
  })
}

function onContextMenu(e: MouseEvent) {
  const target = resolveTarget(e.clientX, e.clientY)
  if (!target) return
  e.preventDefault()
  e.stopPropagation()
  emit('contextmenu-block', { anchorId: target.anchorId, loopType: target.loopType })
}

/* ========= 已放置材料高亮 ========= */
function highlightAnchors() {
  const host = hostRef.value
  if (!host) return
  host.querySelectorAll('.bp-anchor-active').forEach(el => el.classList.remove('bp-anchor-active'))

  const maps = buildAnchorMaps()
  const activeParagraphs = new Set<number>()
  const activeRows = new Set<string>()
  bpStore.iconList.forEach((icon) => {
    if (!icon.anchorId) return
    const [kind, a, b] = icon.anchorId.split('_')
    if (kind === 'p') activeParagraphs.add(Number(a))
    else if (kind === 'tr') activeRows.add(`${a}_${b}`)
  })

  maps.paragraphOrdinal.forEach((ordinal, paragraphId) => {
    if (!activeParagraphs.has(ordinal)) return
    fragmentsOfParagraph(paragraphId).forEach(f => f.classList.add('bp-anchor-active'))
  })
  maps.rowOrdinal.forEach((pos, rowId) => {
    if (!activeRows.has(`${pad4(pos.t)}_${pad4(pos.r)}`)) return
    host.querySelectorAll<HTMLElement>(`.docx-table-row[data-row-id="${CSS.escape(rowId)}"]`)
      .forEach(r => r.classList.add('bp-anchor-active'))
  })
}

let observer: MutationObserver | null = null
let highlightTimer: ReturnType<typeof setTimeout> | null = null

function scheduleHighlight() {
  if (highlightTimer) clearTimeout(highlightTimer)
  highlightTimer = setTimeout(() => highlightAnchors(), 150)
}

watch(() => bpStore.iconList, () => {
  nextTick(highlightAnchors)
}, { deep: true })

watch(docBytes, () => {
  nextTick(() => {
    highlightAnchors()
    observer?.disconnect()
    observer = new MutationObserver(scheduleHighlight)
    if (hostRef.value) observer.observe(hostRef.value, { childList: true, subtree: true })
  })
})

/* ========= 对外暴露：获取编辑后的 DOCX 字节 ========= */
async function getDocxArrayBuffer(): Promise<ArrayBuffer | null> {
  try {
    return (await editorInstance.value?.save()) ?? null
  } catch (e) {
    console.error('获取编辑后 DOCX 失败:', e)
    return null
  }
}

defineExpose({ getDocxArrayBuffer })

onMounted(() => {
  if (bpStore.docxFile) loadDocx(bpStore.docxFile)
})

onBeforeUnmount(() => {
  observer?.disconnect()
  if (highlightTimer) clearTimeout(highlightTimer)
  automationHost.value?.dispose()
  automationHost.value = null
  bodyHandle = null
})
</script>

<style scoped>
.docx-container {
  width: 100%;
  height: 100%;
  min-height: 0;
  background: #f8f9fa;
  overflow: hidden;
  box-sizing: border-box;
}

.empty-tip {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #94a3b8;
  font-size: 14px;
}

.docx-host {
  height: 100%;
  min-height: 0;
  overflow: auto;
  overscroll-behavior: contain;
}

:deep(.docx-editor) {
  min-height: 100%;
}

/* ===== 组合式编辑器骨架（对齐原糖组件 Frame 布局） ===== */
.bp-docx-frame {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  background-color: var(--doc-bg);
}

.bp-docx-topbar {
  flex: none;
  display: flex;
  flex-direction: column;
  position: relative;
  z-index: var(--doc-z-overlay);
  background-color: var(--doc-surface);
  border-bottom: 1px solid var(--doc-border);
  box-shadow: 0 1px 3px var(--doc-shadow-subtle);
}

.bp-docx-toolbar-wrap {
  padding: 8px 12px;
}

.bp-docx-body {
  position: relative;
  display: flex;
  flex: 1;
  min-height: 0;
  min-width: 0;
}

:deep(.bp-drag-over) {
  outline: 2px dashed #4f8cff !important;
  outline-offset: -2px;
  background: rgba(79, 140, 255, 0.08) !important;
}

:deep(.bp-anchor-active) {
  background: rgba(16, 185, 129, 0.08) !important;
  box-shadow: inset 3px 0 0 #10b981;
}

/* ===== 拖入的字段控件：常显浅蓝胶囊外观（内容锁定，仅可整体删除） ===== */
:deep(.docx-content-control-chrome[data-tag^="bpf_"] .docx-content-control-boundary) {
  opacity: 1;
  background: rgba(79, 140, 255, 0.12);
  border-color: rgba(79, 140, 255, 0.55);
  border-radius: 4px;
}

:deep(.docx-content-control-chrome[data-tag^="bpf_"]:hover .docx-content-control-boundary),
:deep(.docx-content-control-chrome[data-tag^="bpf_"][data-active] .docx-content-control-boundary),
:deep(.docx-content-control-chrome[data-tag^="bpf_"][data-hover] .docx-content-control-boundary) {
  opacity: 1;
  background: rgba(79, 140, 255, 0.2);
  border-color: #4f8cff;
}
</style>
