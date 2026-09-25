/**
 * 字体扰动：共享配置 + Canvas 逐字扰动绘制
 * settings 页面与 PdfViewer 渲染层共用，保证单一数据源。
 */
import { reactive } from 'vue'
import { Store } from '@tauri-apps/plugin-store'

export interface FontJitterConfig {
  // 第一组：字符整体几何变换
  xOffset: number
  yOffset: number
  scaleMin: number
  scaleMax: number
  rotation: number
  spacing: number
  baselineWave: number
  // 第二组：墨水 + 纸张质感
  opacityMin: number
  opacityMax: number
  paperNoise: number
  pageUneven: number
  inkBleed: number
  // 第三组：书写习惯瑕疵
  inkDot: number
  strikethrough: number
  // 第四组：笔画内部扰动
  strokeJitter: number
}

export const defaultJitterConfig: FontJitterConfig = {
  xOffset: 2,
  yOffset: 1.5,
  scaleMin: 0.92,
  scaleMax: 1.08,
  rotation: 1.2,
  spacing: 1,
  baselineWave: 1.5,
  opacityMin: 0.8,
  opacityMax: 1.0,
  paperNoise: 0.15,
  pageUneven: 0.1,
  inkBleed: 0.8,
  inkDot: 5,
  strikethrough: 2,
  strokeJitter: 0.6,
}

/** 全局响应式配置（单例） */
export const jitterConfig = reactive<FontJitterConfig>({ ...defaultJitterConfig })

let jitterStore: Store | null = null
let isLoaded = false

export async function loadJitterConfig(): Promise<void> {
  try {
    jitterStore = await Store.load('settings.json')
    const saved = await jitterStore.get<Partial<FontJitterConfig>>('fontJitterConfig')
    if (saved && typeof saved === 'object') {
      Object.assign(jitterConfig, defaultJitterConfig, saved)
    }
  } catch (e) {
    console.warn('加载字体扰动配置失败:', e)
  } finally {
    isLoaded = true
  }
}

export async function saveJitterConfig(): Promise<void> {
  if (!isLoaded) return
  try {
    if (!jitterStore) {
      jitterStore = await Store.load('settings.json')
    }
    await jitterStore.set('fontJitterConfig', { ...jitterConfig })
    await jitterStore.save()
  } catch (e) {
    console.error('保存字体扰动配置失败:', e)
  }
}

export function resetJitterConfig(): void {
  Object.assign(jitterConfig, defaultJitterConfig)
  saveJitterConfig()
}

/* ==================== 确定性随机（避免重绘闪烁） ==================== */
type Rng = () => number

function mulberry32(seed: number): Rng {
  let a = seed >>> 0
  return () => {
    a |= 0
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

/* ==================== 逐字扰动绘制 ==================== */
export interface JitterDrawOptions {
  fontFamily: string
  fontSize: number
  fontWeight?: number
  italic?: boolean
  color?: string
  /** 整段文字的基础透明度 */
  opacity?: number
  /**
   * 随机种子：传入稳定值（如材料 id）时同一材料的扰动在多次重绘间保持一致；
   * 不传或传 0 时每次都重新随机（用于设置页预览）。
   */
  seed?: number
}

/**
 * 以 (0,0) 为文字中心，逐字应用扰动绘制（调用前可自行 translate / rotate）。
 * 仅应用字符级扰动；纸张噪点 / 明暗不均属于整页效果，不在此处理。
 */
export function drawJitterText(
  ctx: CanvasRenderingContext2D,
  text: string,
  opts: JitterDrawOptions,
): void {
  if (!text) return
  const cfg = jitterConfig
  const {
    fontFamily,
    fontSize,
    fontWeight = 400,
    italic = false,
    color = '#000000',
    opacity = 1,
    seed = 0,
  } = opts

  const rng: Rng = seed ? mulberry32(seed) : Math.random

  // 像素类参数按字号等比缩放：以 24px 为基准，保证大字号下扰动效果依然可见
  const k = Math.max(0.5, fontSize / 24)
  const xOff = cfg.xOffset * k
  const yOff = cfg.yOffset * k
  const spacingJit = cfg.spacing * k
  const waveAmp = cfg.baselineWave * k
  const inkBlur = cfg.inkBleed * k
  const strokeJit = cfg.strokeJitter * k

  ctx.font = `${italic ? 'italic ' : ''}${fontWeight} ${fontSize}px "${fontFamily}", serif`
  ctx.textBaseline = 'middle'
  ctx.textAlign = 'left'

  const chars = Array.from(text)
  const charWidths = chars.map((ch) => ctx.measureText(ch).width)
  const totalW =
    charWidths.reduce((a, b) => a + b, 0) + (chars.length - 1) * spacingJit

  let cursor = -totalW / 2
  const waveLen = Math.max(120, fontSize * 6)

  // 预先（确定性地）生成每个字符的随机参数
  for (let i = 0; i < chars.length; i++) {
    const ch = chars[i]
    const cw = charWidths[i]

    const dx = (rng() - 0.5) * 2 * xOff
    const dy = (rng() - 0.5) * 2 * yOff
    const scale = cfg.scaleMin + rng() * (cfg.scaleMax - cfg.scaleMin)
    const rot = ((rng() - 0.5) * 2 * cfg.rotation * Math.PI) / 180
    const charOpacity = cfg.opacityMin + rng() * (cfg.opacityMax - cfg.opacityMin)
    const spacingJitter = (rng() - 0.5) * 2 * spacingJit
    const waveY = Math.sin(((cursor + totalW / 2) / waveLen) * Math.PI * 2) * waveAmp
    const dotAtStart = rng() * 100 < cfg.inkDot
    const dotAtEnd = rng() * 100 < cfg.inkDot
    const hasStrike = rng() * 100 < cfg.strikethrough

    ctx.save()
    ctx.translate(cursor + cw / 2 + dx, dy + waveY)
    ctx.rotate(rot)
    ctx.scale(scale, scale)
    ctx.globalAlpha = opacity * charOpacity
    ctx.fillStyle = color

    // 墨水边缘洇染羽化
    if (inkBlur > 0) {
      ctx.shadowColor = 'rgba(20,20,20,0.55)'
      ctx.shadowBlur = inkBlur
    }

    ctx.fillText(ch, -cw / 2, 0)

    // 笔画微抖动（肌肉微颤）：叠加一层轻微偏移的半透明笔迹
    if (strokeJit > 0) {
      ctx.globalAlpha = opacity * charOpacity * 0.35
      ctx.shadowBlur = 0
      const sjx = (rng() - 0.5) * strokeJit
      const sjy = (rng() - 0.5) * strokeJit
      ctx.fillText(ch, -cw / 2 + sjx, sjy)
    }

    ctx.restore()

    // 起笔 / 收笔墨点
    if (dotAtStart || dotAtEnd) {
      ctx.save()
      ctx.fillStyle = color
      ctx.globalAlpha = opacity * 0.8
      ctx.beginPath()
      const dotX = cursor + dx + (dotAtStart ? 0 : cw)
      ctx.arc(dotX, dy + waveY, Math.max(0.8, fontSize * 0.035) + rng() * 0.6, 0, Math.PI * 2)
      ctx.fill()
      ctx.restore()
    }

    // 随机简单涂改划线
    if (hasStrike) {
      ctx.save()
      ctx.strokeStyle = color
      ctx.globalAlpha = opacity * 0.7
      ctx.lineWidth = Math.max(1, fontSize * 0.035)
      ctx.beginPath()
      const sx = cursor + dx
      const sy = dy + waveY - fontSize * 0.12
      ctx.moveTo(sx, sy)
      ctx.lineTo(sx + cw * scale + 2, sy + (rng() - 0.5) * 2)
      ctx.stroke()
      ctx.restore()
    }

    cursor += cw + spacingJitter
  }

  ctx.globalAlpha = 1
}
