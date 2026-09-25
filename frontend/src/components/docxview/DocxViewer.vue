<template>
  <div class="docx-container" ref="containerRef">
    <div v-if="!bpStore.docxFile" class="empty-tip">
      请先选择 DOCX 模板
    </div>
    <div v-else ref="docxWrapperRef" class="docx-host" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'
import { renderAsync } from 'docx-preview'
import { useBPStore } from '@/stores/bpstore'
import type { IconOption, StoreIcon } from '@/types/icon'

const bpStore = useBPStore()
const containerRef = ref<HTMLElement | null>(null)
const docxWrapperRef = ref<HTMLElement | null>(null)

const emit = defineEmits<{
  (e: 'drop-icon', payload: { option: IconOption; anchorId: string; charOffset: number }): void
  (e: 'contextmenu-block', payload: { anchorId: string; loopType: 'paragraph' | 'tableRow' }): void
}>()

/** 段落/表格行与 anchorId 的映射，渲染后建立 */
const anchorMap = new Map<HTMLElement, string>()

async function renderDocx() {
  // 等待 v-else 的容器渲染完成再取 ref
  await nextTick()
  const wrapper = docxWrapperRef.value
  if (!bpStore.docxFile || !wrapper) return
  // 清空上一次渲染内容
  wrapper.innerHTML = ''
  const buf = await bpStore.docxFile.arrayBuffer()
  try {
    await renderAsync(buf, wrapper, undefined, {
      className: 'docx-preview',
      inWrapper: true,
      ignoreWidth: false,
      ignoreHeight: false,
      ignoreFonts: false,
      breakPages: true,
      experimental: true,
    })
    await nextTick()
    buildAnchorMap()
  } catch (e) {
    console.error('DOCX 渲染失败:', e)
  }
}

/** 给渲染后的 DOM 元素绑定 anchorId */
function buildAnchorMap() {
  anchorMap.clear()
  const wrapper = docxWrapperRef.value
  if (!wrapper) return

  // 段落
  const paragraphs = wrapper.querySelectorAll('p')
  paragraphs.forEach((el, idx) => {
    const anchorId = `p_${String(idx).padStart(4, '0')}`
    el.setAttribute('data-anchor-id', anchorId)
    anchorMap.set(el as HTMLElement, anchorId)
    setupDropTarget(el as HTMLElement, anchorId)
    setupContextMenu(el as HTMLElement, anchorId, 'paragraph')
  })

  // 表格
  const tables = wrapper.querySelectorAll('table')
  tables.forEach((tbl, tIdx) => {
    const rows = tbl.querySelectorAll('tr')
    rows.forEach((tr, rIdx) => {
      const anchorId = `tr_${String(tIdx).padStart(4, '0')}_${String(rIdx).padStart(4, '0')}`
      tr.setAttribute('data-anchor-id', anchorId)
      anchorMap.set(tr as HTMLElement, anchorId)
      setupDropTarget(tr as HTMLElement, anchorId)
      setupContextMenu(tr as HTMLElement, anchorId, 'tableRow')
    })
  })

  // 已有标注高亮
  highlightAnchors()
}

function highlightAnchors() {
  // 清除旧高亮
  docxWrapperRef.value?.querySelectorAll('.bp-anchor-active').forEach(el => {
    el.classList.remove('bp-anchor-active')
  })
  // 为已放置材料的锚点添加高亮
  bpStore.iconList.forEach(icon => {
    if (!icon.anchorId) return
    const el = docxWrapperRef.value?.querySelector(`[data-anchor-id="${icon.anchorId}"]`)
    el?.classList.add('bp-anchor-active')
  })
}

function setupDropTarget(el: HTMLElement, anchorId: string) {
  el.addEventListener('dragover', (e: DragEvent) => {
    if (e.dataTransfer?.types?.includes('application/x-batchprint-option')) {
      e.preventDefault()
      e.dataTransfer.dropEffect = 'copy'
      el.classList.add('bp-drag-over')
    }
  })
  el.addEventListener('dragleave', () => {
    el.classList.remove('bp-drag-over')
  })
  el.addEventListener('drop', (e: DragEvent) => {
    e.preventDefault()
    el.classList.remove('bp-drag-over')
    const raw = e.dataTransfer?.getData('application/x-batchprint-option')
    if (!raw) return
    try {
      const payload = JSON.parse(raw) as { option?: IconOption; panel?: string }
      if (!payload.option) return

      // 用 caretRangeFromPoint 获取精确的字符偏移位置
      let charOffset = 0
      const range = document.caretRangeFromPoint(e.clientX, e.clientY)
      if (range) {
        const para = range.startContainer.parentElement?.closest('p') ||
                     range.startContainer.parentElement?.closest('tr')
        if (para) {
          // 计算该段落下，range 起点之前的文本总长度作为字符偏移
          const textNodes: Text[] = []
          const walker = document.createTreeWalker(para, NodeFilter.SHOW_TEXT)
          let node: Node | null
          while ((node = walker.nextNode())) {
            textNodes.push(node as Text)
          }
          for (const tn of textNodes) {
            if (tn === range.startContainer) {
              charOffset += range.startOffset
              break
            }
            charOffset += tn.textContent?.length || 0
          }
        }
      }

      emit('drop-icon', { option: payload.option, anchorId, charOffset })
      setTimeout(highlightAnchors, 0)
    } catch (err) {
      console.error('处理 DOCX 拖放失败:', err)
    }
  })
}

function setupContextMenu(el: HTMLElement, anchorId: string, loopType: 'paragraph' | 'tableRow') {
  el.addEventListener('contextmenu', (e: MouseEvent) => {
    e.preventDefault()
    emit('contextmenu-block', { anchorId, loopType })
  })
}

watch(() => bpStore.docxFile, () => {
  renderDocx()
})

watch(() => bpStore.iconList, () => {
  highlightAnchors()
}, { deep: true })

onMounted(() => {
  renderDocx()
})
</script>

<style scoped>
.docx-container {
  width: 100%;
  height: 100%;
  background: #f8f9fa;
  overflow: auto;
  padding: 16px;
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
  background: #fff;
  margin: 0 auto;
  box-shadow: 0 1px 4px rgba(0,0,0,0.1);
}

:deep(.docx-preview) {
  padding: 24px;
}

:deep(.bp-drag-over) {
  outline: 2px dashed #4f8cff !important;
  outline-offset: -2px;
  background: rgba(79,140,255,0.06) !important;
}

:deep(.bp-anchor-active) {
  background: rgba(16,185,129,0.08) !important;
  position: relative;
}

:deep(.bp-anchor-active)::after {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: #10b981;
}
</style>
