<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { open } from '@tauri-apps/plugin-dialog'
import { Store } from '@tauri-apps/plugin-store'
import { invoke } from '@tauri-apps/api/core'

import { useBPStore } from '@/stores/bpstore'
import { mkdir, readDir, copyFile, remove, exists } from '@tauri-apps/plugin-fs'
import { clearFontsCache, loadCustomFonts } from '@/utils/fontLoader'
import {
  jitterConfig,
  loadJitterConfig,
  saveJitterConfig,
  resetJitterConfig,
  drawJitterText,
} from '@/utils/fontJitter'

const selectedItemIndex = ref(0)
const dataPath = ref('')
let settingsStore: Store | null = null
const settingsItems = [
  { title: '通用设置', icon: 'mdi-cog' },
  { title: '存储与路径', icon: 'mdi-folder-settings' },
  { title: '字体管理', icon: 'mdi-format-font' },
  { title: '字体扰动', icon: 'mdi-wave' },
  { title: '帐户与安全', icon: 'mdi-account-circle' },
  { title: '关于', icon: 'mdi-information' },
]

const selectedPath = ref<string>('')

const isMovingDialog = ref(false)
const moveResultDialog = ref(false)
const moveResultSuccess = ref(false)
const moveResultMessage = ref('')

const bpStore = useBPStore()

const fontFiles = ref<string[]>([])
const fontPath = computed(() => (bpStore.dataPath ? `${bpStore.dataPath}/fonts` : ''))

async function loadFontList() {
  if (!fontPath.value) return
  try {
    const dirExists = await exists(fontPath.value)
    if (!dirExists) {
      fontFiles.value = []
      return
    }
    const entries = await readDir(fontPath.value)
    fontFiles.value = entries
      .filter(e => e.name?.toLowerCase().endsWith('.ttf'))
      .map(e => e.name as string)
  } catch (error) {
    console.error('加载字体列表失败:', error)
  }
}

async function notifyFontsChanged() {
  clearFontsCache()
  await loadCustomFonts(bpStore.dataPath)
  bpStore.fontsVersion++
}

async function uploadFont() {
  try {
    const result = await open({
      multiple: false,
      filters: [{ name: '字体文件', extensions: ['ttf'] }],
      title: '选择字体文件',
    })
    if (result && typeof result === 'string') {
      const fileName = result.split(/[/\\]/).pop() || 'font.ttf'
      const dest = `${fontPath.value}/${fileName}`
      if (!(await exists(fontPath.value))) {
        await mkdir(fontPath.value, { recursive: true })
      }
      await copyFile(result, dest)
      await loadFontList()
      await notifyFontsChanged()
    }
  } catch (error) {
    console.error('上传字体失败:', error)
  }
}

async function deleteFont(filename: string) {
  try {
    await remove(`${fontPath.value}/${filename}`)
    await loadFontList()
    await notifyFontsChanged()
  } catch (error) {
    console.error('删除字体失败:', error)
  }
}

async function openPathDialog() {
  try {
    const result = await open({
      directory: true,
      multiple: false,
      title: '选择数据存储路径',
    })
    if (result) {
      // 如果选择的路径与当前路径相同，直接返回
      if (result === bpStore.dataPath) {
        console.info('选择的路径与当前路径相同')
        return
      }
      selectedPath.value = result
      isMovingDialog.value = true
      console.log('选择的路径:', result)
    }
  } catch (error) {
    console.error('打开文件对话框失败:', error)
  }
}

// 公共函数：更新路径到所有存储位置
async function updateDataPath(newPath: string) {
  bpStore.dataPath = newPath
  if (!settingsStore) {
    settingsStore = await Store.load('settings.json')
  }
  await settingsStore.set('data_storage_path', newPath)
  await settingsStore.save()
  bpStore.dataPath = newPath
}

async function createFolder(path: string) {
  try {
    await Promise.all([
      mkdir(`${path}/sealImg`, { recursive: true }),
      mkdir(`${path}/signImg`, { recursive: true }),
      mkdir(`${path}/generatePdf`, { recursive: true }),
      mkdir(`${path}/fonts`, { recursive: true }),
    ])
    await updateDataPath(path)
    await loadFontList()
    await notifyFontsChanged()
    isMovingDialog.value = false
    moveResultSuccess.value = true
    moveResultMessage.value = '文件夹创建成功，存储路径已更新！'
  } catch (error) {
    console.error('创建文件夹失败:', error)
    isMovingDialog.value = false
    moveResultSuccess.value = false
    moveResultMessage.value = `创建文件夹失败: ${error}`
  } finally {
    moveResultDialog.value = true
  }
}

async function moveFolders(newPath: string) {
  try {
    const result = await invoke('move_folder_with_extra', {
      src: bpStore.dataPath,
      dest: newPath,
    })
    console.log('移动结果:', result)

    await updateDataPath(newPath)
    await loadFontList()
    await notifyFontsChanged()
    isMovingDialog.value = false
    moveResultSuccess.value = true
    moveResultMessage.value = '文件移动成功，存储路径已更新！'
  } catch (error) {
    console.error('移动文件夹失败:', error)
    isMovingDialog.value = false
    moveResultSuccess.value = false
    moveResultMessage.value = `文件移动失败: ${error}`
  } finally {
    moveResultDialog.value = true
  }
}

async function initStore() {
  try {
    settingsStore = await Store.load('settings.json')
    const val = await settingsStore.get<string>('data_storage_path')
    if (typeof val === 'string') {
      dataPath.value = val
    }
  } catch (e) {
    console.warn('初始化设置存储失败:', e)
  }
}

// ==================== 字体扰动配置（来自共享模块 fontJitter） ====================
const jitterPanels = ref<string[]>(['geometry', 'ink', 'habit', 'stroke'])

function handleResetJitter() {
  resetJitterConfig()
  renderAll()
}

// 监听配置变化实时保存
watch(
  jitterConfig,
  () => {
    saveJitterConfig()
    renderAll()
  },
  { deep: true }
)

// ==================== 字体扰动预览 ====================
const previewCanvas = ref<HTMLCanvasElement | null>(null)
const originalCanvas = ref<HTMLCanvasElement | null>(null)
const previewText = ref('字体扰动123ABC')
const selectedFont = ref<string>('')

const fontOptions = computed(() =>
  fontFiles.value.map((f) => ({
    title: f,
    value: f.replace(/\.ttf$/i, ''),
  }))
)

function prepareCanvas(canvas: HTMLCanvasElement) {
  const ctx = canvas.getContext('2d')
  if (!ctx) return null
  const dpr = window.devicePixelRatio || 1
  const cssWidth = canvas.clientWidth || 600
  const cssHeight = canvas.clientHeight || 140
  if (canvas.width !== cssWidth * dpr || canvas.height !== cssHeight * dpr) {
    canvas.width = cssWidth * dpr
    canvas.height = cssHeight * dpr
  }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  return { ctx, W: cssWidth, H: cssHeight }
}

// 原字体预览（无任何扰动，干净电子画布）
function renderOriginal() {
  const canvas = originalCanvas.value
  if (!canvas) return
  const prepared = prepareCanvas(canvas)
  if (!prepared) return
  const { ctx, W, H } = prepared

  ctx.fillStyle = '#ffffff'
  ctx.fillRect(0, 0, W, H)

  const text = previewText.value
  const fontFamily = selectedFont.value || 'serif'
  const fontSize = 34
  ctx.font = `${fontSize}px "${fontFamily}", serif`
  ctx.textBaseline = 'alphabetic'
  ctx.textAlign = 'center'
  ctx.fillStyle = '#1c1c1c'
  ctx.fillText(text, W / 2, H / 2 + fontSize / 3)
}

// 扰动后预览
function renderJittered() {
  const canvas = previewCanvas.value
  if (!canvas) return
  const prepared = prepareCanvas(canvas)
  if (!prepared) return
  const { ctx, W, H } = prepared

  // 背景纸张色
  ctx.fillStyle = '#faf8f4'
  ctx.fillRect(0, 0, W, H)

  // 页面明暗不均（四角暗角）
  if (jitterConfig.pageUneven > 0) {
    const grad = ctx.createRadialGradient(W / 2, H / 2, Math.min(W, H) * 0.3, W / 2, H / 2, Math.max(W, H) * 0.75)
    grad.addColorStop(0, 'rgba(0,0,0,0)')
    grad.addColorStop(1, `rgba(0,0,0,${Math.min(0.5, jitterConfig.pageUneven * 0.5)})`)
    ctx.fillStyle = grad
    ctx.fillRect(0, 0, W, H)
  }

  // 逐字应用字符级扰动（以画布中心为文字中心，不传种子 → 每次随机呈现）
  ctx.save()
  ctx.translate(W / 2, H / 2)
  drawJitterText(ctx, previewText.value, {
    fontFamily: selectedFont.value || 'serif',
    fontSize: 34,
    color: '#1c1c1c',
  })
  ctx.restore()

  // 纸张颗粒噪点
  if (jitterConfig.paperNoise > 0) {
    const imageData = ctx.getImageData(0, 0, W, H)
    const data = imageData.data
    const amount = jitterConfig.paperNoise * 40
    for (let i = 0; i < data.length; i += 4) {
      const n = (Math.random() - 0.5) * amount
      data[i] = Math.max(0, Math.min(255, data[i] + n))
      data[i + 1] = Math.max(0, Math.min(255, data[i + 1] + n))
      data[i + 2] = Math.max(0, Math.min(255, data[i + 2] + n))
    }
    ctx.putImageData(imageData, 0, 0)
  }
}

// 同时刷新原字体与扰动后预览
function renderAll() {
  renderOriginal()
  renderJittered()
}

async function initJitter() {
  await loadJitterConfig()
  // 确保自定义字体已加载到 document.fonts
  try {
    await loadCustomFonts(bpStore.dataPath)
  } catch (e) {
    console.warn('加载预览字体失败:', e)
  }
  if (fontOptions.value.length > 0 && !selectedFont.value) {
    selectedFont.value = fontOptions.value[0].value
  }
  await nextTick()
  renderAll()
}

// 切换字体或文本时刷新预览
watch(selectedFont, () => renderAll())
watch(previewText, () => renderAll())

// 切换到字体扰动标签页时，等 canvas 可见后重新渲染（保证尺寸正确）
watch(selectedItemIndex, (i) => {
  if (i === 3) nextTick(() => renderAll())
})
watch(fontFiles, () => {
  if (fontOptions.value.length > 0 && !fontOptions.value.some((f) => f.value === selectedFont.value)) {
    selectedFont.value = fontOptions.value[0].value
  }
  renderAll()
})

onMounted(() => {
  initStore()
  selectedItemIndex.value = 0
  loadFontList()
  initJitter()
})
</script>

<template>
  <v-container fluid class="settings-shell px-6 py-6">
    <div class="settings-card">
      <div class="settings-header">
        <v-icon size="20" color="primary" class="mr-2">mdi-cog-outline</v-icon>
        <span class="settings-title">应用设置</span>
      </div>

      <div class="settings-body d-flex flex-row">
        <v-list density="comfortable" nav class="settings-nav flex-grow-0 flex-shrink-0">
          <v-list-item
            v-for="(item, i) in settingsItems"
            :key="i"
            :value="i"
            :active="selectedItemIndex === i"
            active-color="primary"
            class="settings-nav-item"
            rounded="pill"
            @click="selectedItemIndex = i"
            :prepend-icon="item.icon"
          >
            <v-list-item-title>{{ item.title }}</v-list-item-title>
          </v-list-item>
        </v-list>

        <v-divider vertical />

        <div class="settings-content flex-grow-1 pa-6">
          <v-window v-model="selectedItemIndex" direction="vertical">
            <v-window-item :value="0">
              <div>通用设置</div>
            </v-window-item>

            <v-window-item :value="1">
              <h2 class="text-h6 mb-4">存储与路径</h2>
              <p class="text-subtitle-1 mb-2">数据存储路径:</p>
              <v-text-field
                label="当前路径"
                density="compact"
                readonly
                append-icon="mdi-folder-open"
                v-model="bpStore.dataPath"
              />
              <v-btn color="success" class="mt-2" @click="openPathDialog">更改路径</v-btn>
              <v-alert type="info" class="mt-4">
                推荐将图片路径更改到非系统盘，以节省 C 盘空间
              </v-alert>
            </v-window-item>

            <v-window-item :value="2">
              <h2 class="text-h6 mb-4">字体管理</h2>
              <p class="text-subtitle-1 mb-2">自定义字体列表:</p>

              <v-btn
                color="primary"
                prepend-icon="mdi-upload"
                @click="uploadFont"
                class="mb-3"
              >
                上传字体
              </v-btn>

              <v-alert v-if="fontFiles.length === 0" type="info" class="mt-2" density="compact">
                暂无可字体，点击"上传字体"添加 TTF 字体文件
              </v-alert>

              <v-list v-else density="compact" class="bg-grey-lighten-4 rounded" lines="one">
                <v-list-item
                  v-for="font in fontFiles"
                  :key="font"
                  :title="font"
                  :subtitle="'TTF 字体文件'"
                >
                  <template #prepend>
                    <v-icon>mdi-format-font</v-icon>
                  </template>
                  <template #append>
                    <v-btn
                      icon
                      variant="text"
                      density="compact"
                      color="error"
                      @click="deleteFont(font)"
                    >
                      <v-icon>mdi-delete</v-icon>
                      <v-tooltip activator="parent" location="top">删除</v-tooltip>
                    </v-btn>
                  </template>
                </v-list-item>
              </v-list>
            </v-window-item>

            <v-window-item :value="3">
              <div class="jitter-page d-flex flex-column">
                <!-- 顶部操作栏 -->
                <div class="d-flex align-center justify-space-between mb-3">
                  <h2 class="text-h6 ma-0">字体扰动</h2>
                  <v-btn
                    variant="outlined"
                    prepend-icon="mdi-refresh"
                    size="small"
                    @click="handleResetJitter"
                  >
                    重置为默认参数
                  </v-btn>
                </div>

                <!-- 扰动参数配置区（可滚动） -->
                <div class="jitter-config-scroll flex-grow-1">
                  <v-expansion-panels v-model="jitterPanels" multiple variant="accordion">
                    <!-- 第一组：字符整体几何变换 -->
                    <v-expansion-panel value="geometry">
                      <v-expansion-panel-title>字符整体几何变换</v-expansion-panel-title>
                      <v-expansion-panel-text>
                        <div class="param-row">
                          <div class="param-head">
                            <span class="param-name">X轴左右平移扰动</span>
                            <v-tooltip activator="parent" location="top">
                              <template #activator="{ props }">
                                <v-icon v-bind="props" size="16" color="grey">mdi-help-circle</v-icon>
                              </template>
                              控制每个汉字左右随机偏移幅度，模拟手写左右错位。
                            </v-tooltip>
                          </div>
                          <div class="param-meta">范围 0~5px · 当前 ±{{ jitterConfig.xOffset.toFixed(1) }}px</div>
                          <v-slider v-model="jitterConfig.xOffset" :min="0" :max="5" :step="0.1" density="compact" thumb-label />
                        </div>

                        <div class="param-row">
                          <div class="param-head">
                            <span class="param-name">Y轴上下基线偏移扰动</span>
                            <v-tooltip activator="parent" location="top">
                              <template #activator="{ props }">
                                <v-icon v-bind="props" size="16" color="grey">mdi-help-circle</v-icon>
                              </template>
                              控制每个汉字上下随机浮动，模拟字不在一条绝对水平线上。
                            </v-tooltip>
                          </div>
                          <div class="param-meta">范围 0~4px · 当前 ±{{ jitterConfig.yOffset.toFixed(1) }}px</div>
                          <v-slider v-model="jitterConfig.yOffset" :min="0" :max="4" :step="0.1" density="compact" thumb-label />
                        </div>

                        <div class="param-row">
                          <div class="param-head">
                            <span class="param-name">Scale大小缩放扰动</span>
                            <v-tooltip activator="parent" location="top">
                              <template #activator="{ props }">
                                <v-icon v-bind="props" size="16" color="grey">mdi-help-circle</v-icon>
                              </template>
                              控制单个汉字大小随机缩放区间，模拟写字大小不一。
                            </v-tooltip>
                          </div>
                          <div class="param-meta">范围 0.8~1.2 · 当前 {{ jitterConfig.scaleMin.toFixed(2) }}~{{ jitterConfig.scaleMax.toFixed(2) }}</div>
                          <v-range-slider
                            :model-value="[jitterConfig.scaleMin, jitterConfig.scaleMax]"
                            @update:model-value="(v: number[]) => { jitterConfig.scaleMin = v[0]; jitterConfig.scaleMax = v[1] }"
                            :min="0.8" :max="1.2" :step="0.01" density="compact" thumb-label
                          />
                        </div>

                        <div class="param-row">
                          <div class="param-head">
                            <span class="param-name">单字微小旋转扰动</span>
                            <v-tooltip activator="parent" location="top">
                              <template #activator="{ props }">
                                <v-icon v-bind="props" size="16" color="grey">mdi-help-circle</v-icon>
                              </template>
                              每个字独立轻微旋转倾斜，模拟手写歪字效果。
                            </v-tooltip>
                          </div>
                          <div class="param-meta">范围 0~3° · 当前 ±{{ jitterConfig.rotation.toFixed(1) }}°</div>
                          <v-slider v-model="jitterConfig.rotation" :min="0" :max="3" :step="0.1" density="compact" thumb-label />
                        </div>

                        <div class="param-row">
                          <div class="param-head">
                            <span class="param-name">字/词间距扰动</span>
                            <v-tooltip activator="parent" location="top">
                              <template #activator="{ props }">
                                <v-icon v-bind="props" size="16" color="grey">mdi-help-circle</v-icon>
                              </template>
                              字与字之间空隙随机变化，消除固定字体间距。
                            </v-tooltip>
                          </div>
                          <div class="param-meta">范围 0~3px · 当前 ±{{ jitterConfig.spacing.toFixed(1) }}px</div>
                          <v-slider v-model="jitterConfig.spacing" :min="0" :max="3" :step="0.1" density="compact" thumb-label />
                        </div>

                        <div class="param-row">
                          <div class="param-head">
                            <span class="param-name">基线波浪漂移</span>
                            <v-tooltip activator="parent" location="top">
                              <template #activator="{ props }">
                                <v-icon v-bind="props" size="16" color="grey">mdi-help-circle</v-icon>
                              </template>
                              整行文字基线缓慢波浪起伏，模拟一行字越写越飘。
                            </v-tooltip>
                          </div>
                          <div class="param-meta">范围 0~3px · 当前 {{ jitterConfig.baselineWave.toFixed(1) }}px</div>
                          <v-slider v-model="jitterConfig.baselineWave" :min="0" :max="3" :step="0.1" density="compact" thumb-label />
                        </div>
                      </v-expansion-panel-text>
                    </v-expansion-panel>

                    <!-- 第二组：墨水 + 纸张质感 -->
                    <v-expansion-panel value="ink">
                      <v-expansion-panel-title>墨水 + 纸张质感</v-expansion-panel-title>
                      <v-expansion-panel-text>
                        <div class="param-row">
                          <div class="param-head">
                            <span class="param-name">墨水透明度扰动</span>
                            <v-tooltip activator="parent" location="top">
                              <template #activator="{ props }">
                                <v-icon v-bind="props" size="16" color="grey">mdi-help-circle</v-icon>
                              </template>
                              控制文字墨色深浅随机浮动，模拟下笔轻重不同。
                            </v-tooltip>
                          </div>
                          <div class="param-meta">范围 0.5~1.0 · 当前 {{ jitterConfig.opacityMin.toFixed(2) }}~{{ jitterConfig.opacityMax.toFixed(2) }}</div>
                          <v-range-slider
                            :model-value="[jitterConfig.opacityMin, jitterConfig.opacityMax]"
                            @update:model-value="(v: number[]) => { jitterConfig.opacityMin = v[0]; jitterConfig.opacityMax = v[1] }"
                            :min="0.5" :max="1.0" :step="0.01" density="compact" thumb-label
                          />
                        </div>

                        <div class="param-row">
                          <div class="param-head">
                            <span class="param-name">纸张颗粒噪点</span>
                            <v-tooltip activator="parent" location="top">
                              <template #activator="{ props }">
                                <v-icon v-bind="props" size="16" color="grey">mdi-help-circle</v-icon>
                              </template>
                              叠加纸张细微颗粒噪点，消除干净的电子画布感。
                            </v-tooltip>
                          </div>
                          <div class="param-meta">范围 0~1 · 当前 {{ jitterConfig.paperNoise.toFixed(2) }}</div>
                          <v-slider v-model="jitterConfig.paperNoise" :min="0" :max="1" :step="0.01" density="compact" thumb-label />
                        </div>

                        <div class="param-row">
                          <div class="param-head">
                            <span class="param-name">页面明暗不均</span>
                            <v-tooltip activator="parent" location="top">
                              <template #activator="{ props }">
                                <v-icon v-bind="props" size="16" color="grey">mdi-help-circle</v-icon>
                              </template>
                              页面边角亮度轻微变暗，模拟拍照时的光影不均匀。
                            </v-tooltip>
                          </div>
                          <div class="param-meta">范围 0~1 · 当前 {{ jitterConfig.pageUneven.toFixed(2) }}</div>
                          <v-slider v-model="jitterConfig.pageUneven" :min="0" :max="1" :step="0.01" density="compact" thumb-label />
                        </div>

                        <div class="param-row">
                          <div class="param-head">
                            <span class="param-name">墨水边缘洇染羽化</span>
                            <v-tooltip activator="parent" location="top">
                              <template #activator="{ props }">
                                <v-icon v-bind="props" size="16" color="grey">mdi-help-circle</v-icon>
                              </template>
                              笔迹边缘轻微模糊，模拟墨水在纸张轻微洇开。
                            </v-tooltip>
                          </div>
                          <div class="param-meta">范围 0~2px · 当前 {{ jitterConfig.inkBleed.toFixed(1) }}px</div>
                          <v-slider v-model="jitterConfig.inkBleed" :min="0" :max="2" :step="0.1" density="compact" thumb-label />
                        </div>
                      </v-expansion-panel-text>
                    </v-expansion-panel>

                    <!-- 第三组：书写习惯瑕疵 -->
                    <v-expansion-panel value="habit">
                      <v-expansion-panel-title>书写习惯瑕疵</v-expansion-panel-title>
                      <v-expansion-panel-text>
                        <div class="param-row">
                          <div class="param-head">
                            <span class="param-name">起笔收笔墨点</span>
                            <v-tooltip activator="parent" location="top">
                              <template #activator="{ props }">
                                <v-icon v-bind="props" size="16" color="grey">mdi-help-circle</v-icon>
                              </template>
                              低概率在笔画首尾生成小黑墨点，模拟中性笔起收笔墨渍。
                            </v-tooltip>
                          </div>
                          <div class="param-meta">范围 0~100% · 当前 {{ jitterConfig.inkDot.toFixed(0) }}%</div>
                          <v-slider v-model="jitterConfig.inkDot" :min="0" :max="100" :step="1" density="compact" thumb-label />
                        </div>

                        <div class="param-row">
                          <div class="param-head">
                            <span class="param-name">随机简单涂改划线</span>
                            <v-tooltip activator="parent" location="top">
                              <template #activator="{ props }">
                                <v-icon v-bind="props" size="16" color="grey">mdi-help-circle</v-icon>
                              </template>
                              极低概率生成短横线涂改痕迹，少量增加手写真实感。
                            </v-tooltip>
                          </div>
                          <div class="param-meta">范围 0~100% · 当前 {{ jitterConfig.strikethrough.toFixed(0) }}%</div>
                          <v-slider v-model="jitterConfig.strikethrough" :min="0" :max="100" :step="1" density="compact" thumb-label />
                        </div>
                      </v-expansion-panel-text>
                    </v-expansion-panel>

                    <!-- 第四组：笔画内部扰动 -->
                    <v-expansion-panel value="stroke">
                      <v-expansion-panel-title>笔画内部扰动</v-expansion-panel-title>
                      <v-expansion-panel-text>
                        <div class="param-row">
                          <div class="param-head">
                            <span class="param-name">笔画微抖动（肌肉微颤）</span>
                            <v-tooltip activator="parent" location="top">
                              <template #activator="{ props }">
                                <v-icon v-bind="props" size="16" color="grey">mdi-help-circle</v-icon>
                              </template>
                              笔画线条增加微小抖动，模拟人手写字肌肉细微颤动。
                            </v-tooltip>
                          </div>
                          <div class="param-meta">范围 0~2px · 当前 ±{{ jitterConfig.strokeJitter.toFixed(1) }}px</div>
                          <v-slider v-model="jitterConfig.strokeJitter" :min="0" :max="2" :step="0.1" density="compact" thumb-label />
                        </div>
                      </v-expansion-panel-text>
                    </v-expansion-panel>
                  </v-expansion-panels>
                </div>

                <!-- 预览区域（固定底部，不随配置滚动） -->
                <div class="jitter-preview flex-shrink-0">
                  <div class="d-flex flex-column flex-md-row gap-3 mb-3 align-md-center">
                    <v-select
                      v-model="selectedFont"
                      :items="fontOptions"
                      item-title="title"
                      item-value="value"
                      label="预览字体"
                      density="compact"
                      variant="outlined"
                      class="jitter-preview-select"
                      hide-details
                    />
                    <v-text-field
                      v-model="previewText"
                      label="预览文本"
                      density="compact"
                      variant="outlined"
                      hide-details
                      class="flex-grow-1"
                    />
                  </div>
                  <!-- 上：原字体预览 -->
                  <div class="jitter-canvas-block">
                    <div class="jitter-canvas-label">原字体</div>
                    <div class="jitter-canvas-wrap">
                      <canvas ref="originalCanvas" class="jitter-canvas"></canvas>
                    </div>
                  </div>

                  <!-- 下：扰动后预览 -->
                  <div class="jitter-canvas-block">
                    <div class="jitter-canvas-label">扰动后</div>
                    <div class="jitter-canvas-wrap">
                      <canvas ref="previewCanvas" class="jitter-canvas"></canvas>
                    </div>
                  </div>
                </div>
              </div>
            </v-window-item>

            <v-window-item :value="4">
              <div>帐户与安全</div>
            </v-window-item>

            <v-window-item :value="5">
              <div>关于</div>
            </v-window-item>
          </v-window>
        </div>
      </div>
    </div>

    <v-dialog
      v-model="isMovingDialog"
      persistent
      max-width="400"
    >
      <v-card>
        <v-card-text>
          是否要移动原有图片到新路径？
        </v-card-text>
        <v-card-actions class="d-flex justify-end">
          <v-btn text @click="createFolder(selectedPath)">否</v-btn>
          <v-btn color="primary" @click="moveFolders(selectedPath)">是</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog
      v-model="moveResultDialog"
      max-width="440"
    >
      <v-card>
        <v-card-item>
          <div class="d-flex align-center">
            <v-icon :color="moveResultSuccess ? 'success' : 'error'" size="28" class="mr-3">
              {{ moveResultSuccess ? 'mdi-check-circle' : 'mdi-alert-circle' }}
            </v-icon>
            <v-card-title class="pa-0">
              {{ moveResultSuccess ? '操作成功' : '操作失败' }}
            </v-card-title>
          </div>
        </v-card-item>
        <v-card-text>
          <p class="text-body-2">{{ moveResultMessage }}</p>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="moveResultDialog = false">确定</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<style scoped>
.settings-shell {
  max-width: 1200px;
  height: 100%;
  min-height: 0;
  margin: 0 auto;
}

.settings-card {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  width: 100%;
  background: #fff;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  overflow: hidden;
}

.settings-header {
  display: flex;
  align-items: center;
  padding: 16px 20px 12px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.04);
}

.settings-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: rgb(15, 23, 42);
  letter-spacing: -0.01em;
}

.settings-body {
  flex: 1;
  min-height: 0;
}

.settings-nav {
  width: 240px;
  padding: 12px;
}

.settings-nav-item {
  height: 40px !important;
  min-height: 40px !important;
  margin-bottom: 4px !important;
}

.settings-content {
  min-width: 0;
  overflow-y: auto;
}

.settings-content::-webkit-scrollbar {
  width: 6px;
}
.settings-content::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.08);
  border-radius: 3px;
}
.settings-content:hover::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.15);
}

/* ===== 字体扰动页面 ===== */
.settings-content :deep(.v-window) {
  height: 100%;
}
.settings-content :deep(.v-window-item) {
  height: 100%;
}

.jitter-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.jitter-config-scroll {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  padding-right: 6px;
}

.jitter-config-scroll::-webkit-scrollbar {
  width: 6px;
}
.jitter-config-scroll::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.08);
  border-radius: 3px;
}
.jitter-config-scroll:hover::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.15);
}

.jitter-preview {
  flex: 0 0 auto;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
}

.jitter-preview-select {
  max-width: 260px;
  min-width: 180px;
}

.jitter-canvas-wrap {
  width: 100%;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 8px;
  overflow: hidden;
  background: #faf8f4;
}

.jitter-canvas-block {
  margin-bottom: 12px;
}

.jitter-canvas-block:last-child {
  margin-bottom: 0;
}

.jitter-canvas-label {
  font-size: 0.75rem;
  color: rgba(0, 0, 0, 0.5);
  margin-bottom: 4px;
  font-weight: 500;
}

.jitter-canvas {
  display: block;
  width: 100%;
  height: 130px;
}

.param-row {
  margin-bottom: 18px;
}

.param-row:last-child {
  margin-bottom: 0;
}

.param-head {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}

.param-name {
  font-size: 0.875rem;
  font-weight: 500;
  color: rgba(0, 0, 0, 0.8);
}

.param-meta {
  font-size: 0.72rem;
  color: rgba(0, 0, 0, 0.45);
  margin-bottom: 2px;
  letter-spacing: 0.01em;
}
</style>
