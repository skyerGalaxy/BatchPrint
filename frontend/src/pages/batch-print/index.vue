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
              <div class="material-nav" @mouseleave="clearHoverTimer">
                <button
                  v-for="item in materialNavItems"
                  :key="item.value"
                  type="button"
                  class="material-nav-item"
                  :class="[
                    `material-nav-item--${item.value}`,
                    { active: activeMaterialNav === item.value }
                  ]"
                  @mouseenter="setActiveNav(item.value)"
                  @focus="setActiveNav(item.value)"
                  @click="activeMaterialNav = item.value"
                >
                  <v-icon size="18">{{ item.icon }}</v-icon>
                  <span>{{ item.title }}</span>
                </button>
              </div>
              <div class="material-expand-host">
                <Transition name="material-fade" mode="out-in">
                  <div :key="activeMaterialNav" class="material-stage-inner">
                  <!-- 表格：解析 Excel 的字段 -->
                  <template v-if="activeMaterialNav === 'table'">
                    <div v-if="bpStore.fieldNames.length === 0" class="expand-empty-tip">
                      请先选择 Excel 文件
                    </div>
                    <div v-else class="field-chip-list">
                      <div
                        v-for="item in bpStore.fieldNames"
                        :key="item"
                        class="field-chip"
                        draggable="true"
                        @dragstart="startFieldDrag($event, item)"
                      >
                        {{ item }}
                      </div>
                    </div>
                  </template>

                  <!-- 签字：设置路径下的签字内容 -->
                  <template v-else-if="activeMaterialNav === 'signature'">
                    <div class="thumb-grid">
                      <div
                        v-for="(img, idx) in bpStore.imageList_signature"
                        :key="idx"
                        class="thumb-card thumb-card--signature"
                        draggable="true"
                        @dragstart="startImageDrag($event, 'signature', idx)"
                        @contextmenu.prevent="onImageContextMenu($event, 'signature', idx)"
                      >
                        <img :src="img" />
                      </div>
                      <button
                        type="button"
                        class="thumb-card thumb-add thumb-add--signature"
                        title="添加签字图片"
                        @click="triggerImagePicker('signature')"
                      >
                        <v-icon size="28">mdi-plus</v-icon>
                      </button>
                    </div>
                  </template>

                  <!-- 印章：设置路径下的印章内容 -->
                  <template v-else-if="activeMaterialNav === 'seal'">
                    <div class="thumb-grid">
                      <div
                        v-for="(img, idx) in bpStore.imageList_seal"
                        :key="idx"
                        class="thumb-card thumb-card--seal"
                        draggable="true"
                        @dragstart="startImageDrag($event, 'seal', idx)"
                        @contextmenu.prevent="onImageContextMenu($event, 'seal', idx)"
                      >
                        <img :src="img" />
                      </div>
                      <button
                        type="button"
                        class="thumb-card thumb-add thumb-add--seal"
                        title="添加印章图片"
                        @click="triggerImagePicker('seal')"
                      >
                        <v-icon size="28">mdi-plus</v-icon>
                      </button>
                    </div>
                  </template>

                  <!-- 图标：预设图标 -->
                  <template v-else-if="activeMaterialNav === 'icon'">
                    <div class="icon-mini-grid">
                      <div
                        v-for="g in iconGroups"
                        :key="g.value"
                        class="icon-mini-group"
                      >
                        <div class="icon-mini-label">{{ g.label }}</div>
                        <div class="icon-mini-row">
                          <div
                            v-for="ic in g.icons"
                            :key="ic.char"
                            class="icon-mini-cell"
                            :title="ic.label"
                            draggable="true"
                            @dragstart="startIconDrag($event, ic.char)"
                          >
                            {{ ic.char }}
                          </div>
                        </div>
                      </div>
                    </div>
                  </template>

                  <!-- 文本：预设文本 chips，+ chip 打开文本窗口添加自定义文字 -->
                  <template v-else-if="activeMaterialNav === 'text'">
                    <div class="text-preset-list">
                      <div
                        v-for="preset in textPresets"
                        :key="preset.id"
                        class="text-preset-chip"
                        :title="`拖动「${preset.text}」到 PDF`"
                        draggable="true"
                        @dragstart="startPresetTextDrag($event, preset)"
                      >
                        <span class="text-preset-label" :style="presetPreviewStyle(preset)">
                          {{ preset.text }}
                        </span>
                        <button
                          type="button"
                          class="text-preset-del"
                          title="删除预设"
                          @click.stop="deleteTextPreset(preset.id)"
                        >
                          <v-icon size="12">mdi-close</v-icon>
                        </button>
                      </div>
                      <button type="button" class="text-preset-add" @click="openTextDialog">
                        <v-icon size="16">mdi-plus</v-icon>
                        <span>添加文本</span>
                      </button>
                    </div>
                  </template>
                  </div>
                </Transition>
              </div>
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
              :disabled="generating"
              @click="generateBatchPDF"
            >
              <v-icon size="18" class="mr-2">mdi-file-document-multiple</v-icon>
              {{ generating ? `生成中 ${generateCurrent}/${generateTotal}` : '生成 PDF' }}
            </v-btn>

            <div v-if="generating" class="generate-progress">
              <v-progress-linear
                :model-value="generateProgress"
                color="primary"
                height="8"
                rounded
                striped
                stream
              />
              <div class="generate-progress-text">
                <span>正在生成 PDF…</span>
                <span>{{ generateCurrent }} / {{ generateTotal }}（{{ Math.round(generateProgress) }}%）</span>
              </div>
            </div>
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

    <!-- 文本预设编辑窗口 -->
    <v-dialog v-model="textDialogOpen" max-width="430">
      <v-card class="text-dialog-card" rounded="xl" elevation="8">
        <v-card-item class="text-dialog-header">
          <v-icon color="#be185d" size="20" class="mr-2">mdi-format-text</v-icon>
          <v-card-title class="text-dialog-title">添加文本预设</v-card-title>
        </v-card-item>

        <v-card-text class="text-dialog-body">
          <v-textarea
            v-model="textForm.text"
            density="compact"
            variant="outlined"
            hide-details
            placeholder="输入自定义文本"
            rows="2"
            auto-grow
            class="text-dialog-textarea"
          />

          <div class="text-dialog-row">
            <v-icon size="16" color="#94a3b8">mdi-format-font</v-icon>
            <v-select
              v-model="textForm.fontFamily"
              :items="fontOptions"
              item-title="name"
              item-value="value"
              density="compact"
              variant="outlined"
              hide-details
              class="text-dialog-select"
            />
          </div>

          <div class="text-dialog-row">
            <v-icon size="16" color="#94a3b8">mdi-format-bold</v-icon>
            <v-btn-toggle
              v-model="textForm.fontWeight"
              mandatory
              density="compact"
              variant="outlined"
              divided
              class="text-weight-toggle"
            >
              <v-btn :value="400" size="x-small">常规</v-btn>
              <v-btn :value="700" size="x-small">粗体</v-btn>
            </v-btn-toggle>
            <v-icon size="16" color="#94a3b8" class="ml-3">mdi-arrow-expand-all</v-icon>
            <v-text-field
              v-model.number="textForm.size"
              type="number"
              density="compact"
              variant="outlined"
              hide-details
              :min="20"
              :max="400"
              class="text-size-field"
            />
          </div>

          <div class="text-dialog-row">
            <v-icon size="16" color="#94a3b8">mdi-opacity</v-icon>
            <v-slider
              v-model="textForm.opacity"
              density="compact"
              hide-details
              :min="0.1"
              :max="1"
              :step="0.05"
              thumb-size="16"
              track-size="3"
              color="#be185d"
              class="text-dialog-slider"
            />
          </div>

          <div class="text-dialog-row">
            <v-icon size="16" color="#94a3b8">mdi-palette</v-icon>
            <v-menu v-model="textColorMenu" :close-on-content-click="false" offset="8">
              <template #activator="{ props: menuProps }">
                <div class="text-color-swatch" :style="{ background: textForm.color }" v-bind="menuProps"></div>
              </template>
              <v-color-picker
                v-model="textForm.color"
                mode="hex"
                hide-inputs
                @update:model-value="textColorMenu = false"
              />
            </v-menu>
            <span class="text-color-hex">{{ textForm.color }}</span>
          </div>

          <div class="text-preview-box">
            <span class="text-preview-label">预览</span>
            <span class="text-preview-value" :style="presetPreviewStyle(textForm)">
              {{ textForm.text || '预览文字' }}
            </span>
          </div>
        </v-card-text>

        <v-card-actions class="text-dialog-actions">
          <v-spacer></v-spacer>
          <v-btn variant="text" rounded="lg" @click="textDialogOpen = false">取消</v-btn>
          <v-btn
            variant="flat"
            rounded="lg"
            color="#be185d"
            :disabled="!textForm.text.trim()"
            @click="saveTextPreset"
          >保存预设</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 签字 / 印章图片添加：隐藏文件选择器 -->
    <input
      ref="imageFileInput"
      type="file"
      accept="image/*"
      class="hidden-file-input"
      @change="handleImageSelect"
    />

    <!-- 签字 / 印章图片右键删除菜单 -->
    <div
      v-if="imageContextMenu.show"
      class="img-ctx-menu"
      :style="{ left: imageContextMenu.x + 'px', top: imageContextMenu.y + 'px' }"
      @click.stop
    >
      <button type="button" class="img-ctx-item" @click="deleteImage">
        <v-icon size="16" color="error">mdi-delete-outline</v-icon>
        <span>删除图片</span>
      </button>
    </div>
    <div
      v-if="imageContextMenu.show"
      class="img-ctx-backdrop"
      @click="closeImageContextMenu"
      @contextmenu.prevent="closeImageContextMenu"
    ></div>
  </v-container>
</template>

<script setup lang="ts">
import axios from 'axios'
import { ref, computed, onMounted, watch } from 'vue'
import { invoke, convertFileSrc } from '@tauri-apps/api/core'
import { readDir, exists, writeFile, mkdir, remove } from '@tauri-apps/plugin-fs'
import { Store } from '@tauri-apps/plugin-store'
import PdfViewer from '@/components/pdfview/PdfViewer.vue'
import { useBPStore } from '@/stores/bpstore'
import type { IconOption } from '@/types/icon'
import { getFontsList, loadCustomFonts } from '@/utils/fontLoader'

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

// 鼠标停留切换材料板块（带短暂延迟，避免滑过时闪烁）
let navHoverTimer: ReturnType<typeof setTimeout> | null = null
function setActiveNav(value: string) {
  if (navHoverTimer) clearTimeout(navHoverTimer)
  navHoverTimer = setTimeout(() => {
    activeMaterialNav.value = value
  }, 80)
}
function clearHoverTimer() {
  if (navHoverTimer) {
    clearTimeout(navHoverTimer)
    navHoverTimer = null
  }
}

function startFieldDrag(event: DragEvent, fieldName: string) {
  if (!event.dataTransfer) return
  const option: IconOption = {
    type: 'field',
    fieldName,
    fontFamily: '楷体',
    size: 120,
  }
  event.dataTransfer.effectAllowed = 'copy'
  event.dataTransfer.setData('application/x-batchprint-option', JSON.stringify({ option, panel: 'table' }))
}

const iconGroups = [
  { value: 'marks', label: '复选框', icons: [
    { char: '☐', label: '空方框' }, { char: '☑', label: '勾选方框' },
    { char: '☒', label: '叉选方框' }, { char: '✓', label: '对勾' },
    { char: '✗', label: '叉号' }, { char: '✔', label: '粗对勾' },
    { char: '✘', label: '粗叉号' }, { char: '●', label: '实心圆' },
  ]},
  { value: 'stars', label: '星形', icons: [
    { char: '★', label: '实心星' }, { char: '☆', label: '空心星' },
    { char: '✦', label: '四角星' }, { char: '✧', label: '空心四角' },
    { char: '◆', label: '实心菱形' }, { char: '◇', label: '空心菱形' },
    { char: '■', label: '实心方块' }, { char: '□', label: '空心方块' },
  ]},
  { value: 'arrows', label: '箭头', icons: [
    { char: '→', label: '右箭头' }, { char: '←', label: '左箭头' },
    { char: '↑', label: '上箭头' }, { char: '↓', label: '下箭头' },
    { char: '↔', label: '左右箭头' }, { char: '↕', label: '上下箭头' },
    { char: '▶', label: '右三角' }, { char: '◀', label: '左三角' },
  ]},
  { value: 'shapes', label: '图形', icons: [
    { char: '▲', label: '实心三角' }, { char: '△', label: '空心三角' },
    { char: '▼', label: '倒三角' }, { char: '▽', label: '空心倒三角' },
    { char: '○', label: '空心圆' }, { char: '♥', label: '红心' },
    { char: '♦', label: '方块' }, { char: '♣', label: '梅花' },
  ]},
  { value: 'office', label: '办公', icons: [
    { char: '☎', label: '电话' }, { char: '✉', label: '信封' },
    { char: '✎', label: '铅笔' }, { char: '⌂', label: '房子' },
    { char: '⌘', label: '命令键' }, { char: '⏎', label: '回车' },
    { char: '⌫', label: '退格' }, { char: '☺', label: '笑脸' },
  ]},
  { value: 'info', label: '提示', icons: [
    { char: '⚡', label: '闪电' }, { char: '⚠', label: '警告' },
    { char: 'ℹ', label: '信息' }, { char: '©', label: '版权' },
    { char: '®', label: '注册商标' }, { char: '™', label: '商标' },
    { char: '♻', label: '回收' }, { char: '☹', label: '哭脸' },
  ]},
]

function startImageDrag(event: DragEvent, type: 'signature' | 'seal', index: number) {
  if (!event.dataTransfer) return
  const list = type === 'signature' ? bpStore.imageList_signature : bpStore.imageList_seal
  const option: IconOption = { type: 'image', imageKind: type, src: list[index] ?? '', size: 120 }
  event.dataTransfer.effectAllowed = 'copy'
  event.dataTransfer.setData('application/x-batchprint-option', JSON.stringify({ option, panel: type }))
}

function startIconDrag(event: DragEvent, char: string) {
  if (!event.dataTransfer) return
  const option: IconOption = {
    type: 'icon', icon: char, color: '#000000', opacity: 1, size: 120,
  }
  event.dataTransfer.effectAllowed = 'copy'
  event.dataTransfer.setData('application/x-batchprint-option', JSON.stringify({ option, panel: 'icon' }))
}

/* ========= 文本预设 ========= */
interface TextPreset {
  id: string
  text: string
  fontFamily: string
  fontWeight: number
  color: string
  opacity: number
  size: number
}

interface FontOption {
  name: string
  value: string
  type: 'system' | 'custom'
  file?: string
  url?: string
}

const textPresets = ref<TextPreset[]>([])
const textDialogOpen = ref(false)
const textColorMenu = ref(false)
const fontOptions = ref<FontOption[]>([])

function createEmptyTextForm(): TextPreset {
  return {
    id: '',
    text: '',
    fontFamily: fontOptions.value[0]?.value ?? '楷体',
    fontWeight: 400,
    color: '#000000',
    opacity: 1,
    size: 120,
  }
}

const textForm = ref<TextPreset>(createEmptyTextForm())

let textPresetStore: Store | null = null

function genPresetId(): string {
  return `tp_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
}

function openTextDialog() {
  textForm.value = createEmptyTextForm()
  textColorMenu.value = false
  textDialogOpen.value = true
}

async function saveTextPreset() {
  const text = textForm.value.text.trim()
  if (!text) return
  textPresets.value.push({ ...textForm.value, id: genPresetId(), text })
  await persistTextPresets()
  textDialogOpen.value = false
}

async function deleteTextPreset(id: string) {
  textPresets.value = textPresets.value.filter(p => p.id !== id)
  await persistTextPresets()
}

async function loadTextPresets() {
  try {
    textPresetStore = await Store.load('text_presets.json')
    const saved = await textPresetStore.get<TextPreset[]>('presets')
    textPresets.value = Array.isArray(saved) ? saved : []
  } catch (error) {
    console.error('加载文本预设失败:', error)
    textPresets.value = []
  }
}

async function persistTextPresets() {
  try {
    if (!textPresetStore) {
      textPresetStore = await Store.load('text_presets.json')
    }
    await textPresetStore.set('presets', textPresets.value)
    await textPresetStore.save()
  } catch (error) {
    console.error('保存文本预设失败:', error)
  }
}

function presetPreviewStyle(preset: TextPreset) {
  return {
    fontFamily: preset.fontFamily,
    fontWeight: preset.fontWeight,
    color: preset.color,
    opacity: preset.opacity,
    fontSize: `${Math.max(10, Math.min(preset.size * 0.12, 18))}px`,
  }
}

function startPresetTextDrag(event: DragEvent, preset: TextPreset) {
  if (!event.dataTransfer) return
  const option: IconOption = {
    type: 'text',
    text: preset.text,
    fontFamily: preset.fontFamily,
    fontWeight: preset.fontWeight,
    color: preset.color,
    opacity: preset.opacity,
    size: preset.size,
  }
  event.dataTransfer.effectAllowed = 'copy'
  event.dataTransfer.setData('application/x-batchprint-option', JSON.stringify({ option, panel: 'text' }))
}

/* ========= 字体列表（文本预设弹窗用） ========= */
async function loadFonts() {
  try {
    await loadCustomFonts(bpStore.dataPath)
    fontOptions.value = await getFontsList(bpStore.dataPath)
  } catch (error) {
    console.error('加载字体列表失败:', error)
    fontOptions.value = [
      { name: '楷体', value: '楷体', type: 'system' },
      { name: '微软雅黑', value: '微软雅黑', type: 'system' },
      { name: '宋体', value: '宋体', type: 'system' },
      { name: '黑体', value: '黑体', type: 'system' },
      { name: 'Arial', value: 'Arial', type: 'system' },
    ]
  }
}

/* ========= 设置路径下的签字 / 印章图片 ========= */
const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']

async function loadImagesFromDir(dirPath: string): Promise<string[]> {
  try {
    if (!await exists(dirPath)) return []
    const files = await readDir(dirPath)
    return files
      .filter(file => file.isFile)
      .map(file => file.name)
      .filter(name => imageExtensions.some(ext => name.toLowerCase().endsWith(ext)))
      .map(name => convertFileSrc(`${dirPath}/${name}`))
  } catch (error) {
    console.error(`读取图片目录失败 ${dirPath}:`, error)
    return []
  }
}

async function refreshImageLists() {
  if (!bpStore.dataPath) return
  const [sig, seal] = await Promise.all([
    loadImagesFromDir(`${bpStore.dataPath}/signImg`),
    loadImagesFromDir(`${bpStore.dataPath}/sealImg`),
  ])
  bpStore.imageList_signature = sig
  bpStore.imageList_seal = seal
}

/* ========= 添加签字 / 印章图片 ========= */
const imagePickerKind = ref<'signature' | 'seal'>('signature')
const imageFileInput = ref<HTMLInputElement | null>(null)

function triggerImagePicker(kind: 'signature' | 'seal') {
  if (!bpStore.dataPath) return
  imagePickerKind.value = kind
  imageFileInput.value?.click()
}

async function handleImageSelect(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  const kind = imagePickerKind.value
  const subDir = kind === 'signature' ? 'signImg' : 'sealImg'
  const dirPath = `${bpStore.dataPath}/${subDir}`
  try {
    if (!await exists(dirPath)) {
      await mkdir(dirPath, { recursive: true })
    }
    const buf = await file.arrayBuffer()
    await writeFile(`${dirPath}/${file.name}`, new Uint8Array(buf))
    await refreshImageLists()
  } catch (error) {
    console.error('添加图片失败:', error)
    alert('添加图片失败，请检查路径权限')
  } finally {
    input.value = ''
  }
}

/* ========= 右键删除签字 / 印章图片 ========= */
const imageContextMenu = ref({
  show: false,
  x: 0,
  y: 0,
  kind: 'signature' as 'signature' | 'seal',
  index: -1,
})

function onImageContextMenu(event: MouseEvent, kind: 'signature' | 'seal', index: number) {
  event.preventDefault()
  imageContextMenu.value = {
    show: true,
    x: event.clientX,
    y: event.clientY,
    kind,
    index,
  }
}

function closeImageContextMenu() {
  imageContextMenu.value.show = false
}

async function deleteImage() {
  const { kind, index } = imageContextMenu.value
  closeImageContextMenu()
  if (index < 0 || !bpStore.dataPath) return
  const list = kind === 'signature' ? bpStore.imageList_signature : bpStore.imageList_seal
  const src = list[index]
  if (!src) return
  const subDir = kind === 'signature' ? 'signImg' : 'sealImg'
  // convertFileSrc 生成 URL 时会编码路径，先整体解码再取最后一段文件名
  const decoded = decodeURIComponent(src)
  const fileName = decoded.split(/[/\\]/).pop() || ''
  if (!fileName) return
  const filePath = `${bpStore.dataPath}/${subDir}/${fileName}`
  try {
    await remove(filePath)
    await refreshImageLists()
  } catch (error) {
    console.error('删除图片失败:', error)
    alert('删除图片失败，请检查文件是否被占用')
  }
}

const mergedCellsDialog = ref(false)
const excelErrorDialog = ref(false)
const excelErrorMessage = ref('')
const resetKey = ref(0)

const generating = ref(false)
const generateProgress = ref(0)
const generateCurrent = ref(0)
const generateTotal = ref(0)
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

onMounted(async () => {
  if (bpStore.pdfSrc) {
    pdfSrc.value = bpStore.pdfSrc
  }
  await Promise.all([
    loadFonts(),
    loadTextPresets(),
    refreshImageLists(),
    bpStore.loadMaterialStyles(),
  ])
})

watch(() => bpStore.dataPath, async (newPath) => {
  if (!newPath) return
  await Promise.all([
    loadFonts(),
    refreshImageLists(),
  ])
})

watch(() => bpStore.fontsVersion, () => {
  loadFonts()
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
  generateProgress.value = 0
  generateCurrent.value = 0
  generateTotal.value = 0

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

    // 后端通过 SSE 逐行上报进度
    const resp = await fetch('http://localhost:8000/generate_batch_pdf', {
      method: 'POST',
      body: formData,
    })
    if (!resp.ok || !resp.body) {
      throw new Error(`后端响应异常: HTTP ${resp.status}`)
    }

    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let donePayload: { msg?: string; path?: string } | null = null

    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const chunks = buffer.split('\n\n')
      buffer = chunks.pop() || ''
      for (const chunk of chunks) {
        const line = chunk.trim()
        if (!line.startsWith('data:')) continue
        const evt = JSON.parse(line.slice(5).trim())
        if (evt.type === 'start') {
          generateTotal.value = evt.total || 0
        } else if (evt.type === 'progress') {
          generateCurrent.value = evt.current
          generateTotal.value = evt.total
          generateProgress.value = evt.total ? (evt.current / evt.total) * 100 : 0
        } else if (evt.type === 'done') {
          donePayload = evt
        } else if (evt.type === 'error') {
          throw new Error(evt.message || '生成失败')
        }
      }
    }

    if (!donePayload) throw new Error('未收到后端完成事件')

    resultSuccess.value = true
    resultMessage.value = donePayload.msg || 'PDF批量生成成功！'
    resultPath.value = donePayload.path || ''
    resultDialog.value = true
  } catch (error) {
    console.error('生成PDF失败:', error)
    resultSuccess.value = false
    resultMessage.value = (error as Error)?.message || 'PDF批量生成出错，请查看浏览器控制台'
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
  height: 100%;
  min-height: 0;
  overflow: hidden;
  padding-bottom: 12px;
}

/* 小屏下列上下堆叠时，高度由内容决定，整列在 batch-grid 内部滚动 */
@media (max-width: 1279.98px) {
  .batch-grid {
    overflow-y: auto;
  }

  .batch-col {
    height: auto;
  }
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

.material-nav-item:focus-visible {
  outline: 2px solid rgba(79, 140, 255, 0.45);
  outline-offset: 1px;
}

.material-expand-host {
  flex: 1;
  min-height: 0;
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.material-stage-inner {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.material-fade-enter-active,
.material-fade-leave-active {
  transition: opacity 0.14s ease;
}

.material-fade-enter-from,
.material-fade-leave-to {
  opacity: 0;
}

.expand-empty-tip {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
  color: rgb(148, 163, 184);
  text-align: center;
}

/* ---- field chips ---- */
.field-chip-list {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-wrap: wrap;
  align-content: flex-start;
  gap: 6px;
  padding: 4px 0;
  overflow-y: auto;
  overscroll-behavior: contain;
}

.field-chip {
  padding: 6px 12px;
  border-radius: 16px;
  background: linear-gradient(135deg, rgba(79,140,255,0.08), rgba(108,92,231,0.05));
  border: 1px solid rgba(79,140,255,0.35);
  cursor: grab;
  transition: all 0.15s ease;
  user-select: none;
  font-size: 0.78rem;
  font-weight: 500;
  color: #2563eb;
}

.field-chip:hover {
  background: linear-gradient(135deg, rgba(79,140,255,0.15), rgba(108,92,231,0.1));
  border-color: rgba(79,140,255,0.55);
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(79,140,255,0.15);
}

.field-chip:active {
  cursor: grabbing;
  transform: translateY(0);
}

/* ---- signature / seal thumbnails ---- */
.thumb-grid {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  align-content: start;
  gap: 6px;
  padding: 4px 0;
  overflow-y: auto;
  overscroll-behavior: contain;
}

.thumb-card {
  aspect-ratio: 1;
  border-radius: 10px;
  background: #f1f5f9;
  border: 2px solid transparent;
  cursor: grab;
  overflow: hidden;
  transition: all 0.15s ease;
  opacity: 0.85;
}

.thumb-card img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.thumb-card:hover {
  opacity: 1;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.thumb-card--signature:hover {
  border-color: rgba(15,118,110,0.45);
}

.thumb-card--seal:hover {
  border-color: rgba(194,65,12,0.45);
}

.thumb-card:active {
  cursor: grabbing;
  transform: translateY(0);
}

/* ---- signature / seal add card ---- */
.thumb-add {
  cursor: pointer;
  opacity: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px dashed rgba(100, 116, 139, 0.4);
  background: rgba(100, 116, 139, 0.06);
  color: rgba(100, 116, 139, 0.7);
  font: inherit;
}

.thumb-add:hover {
  border-style: solid;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.thumb-add:active {
  cursor: pointer;
  transform: translateY(0);
}

.thumb-add--signature {
  border-color: rgba(15, 118, 110, 0.45);
  background: rgba(15, 118, 110, 0.05);
  color: rgba(15, 118, 110, 0.8);
}

.thumb-add--seal {
  border-color: rgba(194, 65, 12, 0.45);
  background: rgba(194, 65, 12, 0.05);
  color: rgba(194, 65, 12, 0.8);
}

.hidden-file-input {
  display: none;
}

/* ---- icon mini grid ---- */
.icon-mini-grid {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 4px 0;
  overflow-y: auto;
  overscroll-behavior: contain;
}

.icon-mini-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.icon-mini-label {
  font-size: 0.68rem;
  font-weight: 600;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.icon-mini-row {
  display: flex;
  flex-wrap: wrap;
  gap: 3px;
}

.icon-mini-cell {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  font-family: "Segoe UI Symbol", "Segoe UI Emoji", sans-serif;
  font-size: 16px;
  cursor: grab;
  background: #f8fafc;
  border: 1px solid transparent;
  transition: all 0.12s ease;
}

.icon-mini-cell:hover {
  background: linear-gradient(135deg, rgba(124,58,237,0.1), rgba(168,85,247,0.05));
  border-color: rgba(124,58,237,0.35);
  color: #7c3aed;
  transform: scale(1.1);
}

.icon-mini-cell:active {
  cursor: grabbing;
  transform: scale(1);
}

/* ---- text presets ---- */
.text-stage {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.text-preset-list {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-wrap: wrap;
  align-content: flex-start;
  gap: 6px;
  padding: 4px 0;
  overflow-y: auto;
  overscroll-behavior: contain;
}

.text-preset-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 100%;
  padding: 5px 6px 5px 12px;
  border-radius: 16px;
  background: linear-gradient(135deg, rgba(190,24,93,0.07), rgba(219,39,119,0.04));
  border: 1px solid rgba(190,24,93,0.35);
  cursor: grab;
  transition: all 0.15s ease;
  user-select: none;
}

.text-preset-chip:hover {
  background: linear-gradient(135deg, rgba(190,24,93,0.12), rgba(219,39,119,0.08));
  border-color: rgba(190,24,93,0.55);
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(190,24,93,0.15);
}

.text-preset-chip:active {
  cursor: grabbing;
  transform: translateY(0);
}

.text-preset-label {
  font-size: 0.8rem;
  max-width: 180px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.text-preset-del {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  padding: 0;
  border: none;
  border-radius: 50%;
  background: rgba(190,24,93,0.12);
  color: #be185d;
  cursor: pointer;
  flex-shrink: 0;
  transition: background 0.15s, color 0.15s;
}

.text-preset-del:hover {
  background: #be185d;
  color: #fff;
}

.text-preset-add {
  align-self: flex-start;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 14px;
  border-radius: 16px;
  border: 1px dashed rgba(190,24,93,0.45);
  background: rgba(190,24,93,0.04);
  color: #be185d;
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
  flex-shrink: 0;
}

.text-preset-add:hover {
  background: rgba(190,24,93,0.1);
  border-style: solid;
  transform: translateY(-1px);
}

/* ---- text preset dialog ---- */
.text-dialog-header {
  display: flex;
  align-items: center;
  padding-bottom: 0;
}

.text-dialog-title {
  font-size: 1.05rem;
  font-weight: 700;
}

.text-dialog-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-top: 8px !important;
}

.text-dialog-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.text-dialog-row > .v-icon {
  flex-shrink: 0;
}

.text-dialog-select {
  flex: 1;
  min-width: 0;
}

.text-dialog-select :deep(.v-field) {
  border-radius: 8px !important;
  box-shadow: none !important;
}

.text-weight-toggle {
  border-radius: 8px;
  overflow: hidden;
}

.text-weight-toggle :deep(.v-btn) {
  min-width: 48px !important;
  padding: 0 12px !important;
  height: 28px !important;
  font-size: 12px !important;
  text-transform: none !important;
  letter-spacing: 0 !important;
}

.text-size-field {
  width: 88px;
  flex-shrink: 0;
}

.text-size-field :deep(.v-field) {
  border-radius: 8px !important;
  box-shadow: none !important;
}

.text-dialog-slider {
  flex: 1;
  min-width: 0;
}

.text-color-swatch {
  width: 26px;
  height: 26px;
  border-radius: 7px;
  border: 1.5px solid rgba(0,0,0,0.15);
  flex-shrink: 0;
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.15s;
}

.text-color-swatch:hover {
  transform: scale(1.1);
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}

.text-color-hex {
  font-size: 12px;
  font-weight: 500;
  color: #475569;
  font-family: 'SF Mono', 'Cascadia Code', monospace;
}

.text-preview-box {
  padding: 14px 12px;
  border-radius: 12px;
  background: linear-gradient(135deg, #fdf2f8 0%, #fce7f3 100%);
  border: 1px solid rgba(190,24,93,0.12);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 64px;
  gap: 6px;
}

.text-preview-label {
  font-size: 10px;
  font-weight: 600;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.text-preview-value {
  max-width: 100%;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.text-dialog-actions {
  padding: 8px 16px 16px;
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

.generate-progress {
  margin-top: 10px;
}

.generate-progress-text {
  display: flex;
  justify-content: space-between;
  margin-top: 6px;
  font-size: 12px;
  color: #64748b;
  font-variant-numeric: tabular-nums;
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

/* ---- 右键删除菜单 ---- */
.img-ctx-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1999;
}

.img-ctx-menu {
  position: fixed;
  z-index: 2000;
  min-width: 140px;
  padding: 4px;
  background: #fff;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  animation: img-ctx-fade 0.1s ease;
}

@keyframes img-ctx-fade {
  from {
    opacity: 0;
    transform: scale(0.96);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.img-ctx-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 12px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #ef4444;
  font: inherit;
  font-size: 0.82rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.12s;
}

.img-ctx-item:hover {
  background: rgba(239, 68, 68, 0.08);
}
</style>
