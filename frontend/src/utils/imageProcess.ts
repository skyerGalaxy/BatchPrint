/**
 * 签字 / 印章图片预处理
 *
 * 拍摄或扫描得到的签字、印章图片通常带有纸张底色、阴影和多余留白，
 * 直接叠加到 PDF / DOCX 上会盖住正文。这里在浏览器端把它们转成
 * “背景透明、内容紧凑”的 PNG —— PDF 端用 `mask='auto'`、DOCX 端用
 * `add_picture` 都能正确还原透明通道，因此后端无需改动。
 *
 * 算法：
 * - 签字（luma）：按亮度提取。先用背景估计抵消光照不均，再把归一化亮度
 *   作为 alpha（纸张 → 透明，笔画 → 不透明），边缘天然带抗锯齿。
 * - 印章（red / blue）：按通道差提取。红章用 R - max(G, B) 作为“红度”，
 *   光照强度被抵消；黑字、灰影通过饱和度门限过滤。
 * - 质感：用低频 / 高频噪声调制 alpha，模拟印泥浓淡不均与边缘毛糙，
 *   让输出更接近真实盖章而不是纯色贴图。
 */

export type ImageProcessKind = 'signature' | 'seal'
export type ExtractMode = 'luma' | 'red' | 'blue'

export interface ProcessParams {
  /** 提取模式：签字固定 luma，印章可选红 / 蓝 */
  mode: ExtractMode
  /** 去背景强度 0-100，越大只保留颜色最重的笔画 */
  strength: number
  /** 浓淡 0.6-1.6，越大笔画越粗 */
  gamma: number
  /** 印章：统一印色（关闭则保留原图的颜色浓淡） */
  colorize: boolean
  /** 质感 / 做旧强度 0-100：印泥浓淡不均、边缘毛糙 */
  texture: number
  /** 裁切留白比例 0-0.1（相对内容尺寸） */
  padding: number
  /** 输出长边上限（像素） */
  maxEdge: number
}

export interface ProcessResult {
  blob: Blob
  width: number
  height: number
  /** 提取到的内容占原图比例，用于质量提示 */
  coverage: number
}

export interface LoadedImage {
  source: CanvasImageSource
  width: number
  height: number
  release: () => void
}

export const MAX_EDGE = 1200

/** 低于该 alpha 的像素视为背景，用于自动裁切和覆盖率统计 */
const CROP_ALPHA = 8

function clamp(v: number, lo: number, hi: number): number {
  if (v < lo) return lo
  if (v > hi) return hi
  return v
}

function smoothstep(edge0: number, edge1: number, x: number): number {
  if (edge1 <= edge0) return x >= edge1 ? 1 : 0
  const t = clamp((x - edge0) / (edge1 - edge0), 0, 1)
  return t * t * (3 - 2 * t)
}

export function defaultParams(kind: ImageProcessKind): ProcessParams {
  return kind === 'seal'
    ? { mode: 'red', strength: 50, gamma: 1, colorize: true, texture: 28, padding: 0.04, maxEdge: MAX_EDGE }
    : { mode: 'luma', strength: 45, gamma: 1, colorize: false, texture: 12, padding: 0.02, maxEdge: MAX_EDGE }
}

/* ==================== 参数记忆 ==================== */

function presetKey(kind: ImageProcessKind): string {
  return `bp.imageProcess.${kind}`
}

export function loadPreset(kind: ImageProcessKind): ProcessParams {
  const base = defaultParams(kind)
  try {
    const raw = localStorage.getItem(presetKey(kind))
    if (!raw) return base
    const saved = JSON.parse(raw) as Partial<ProcessParams>
    return {
      ...base,
      ...saved,
      // 印章的提取模式允许被记忆，签字固定为亮度
      mode: kind === 'signature' ? 'luma' : (saved.mode === 'blue' ? 'blue' : 'red'),
    }
  } catch {
    return base
  }
}

export function savePreset(kind: ImageProcessKind, params: ProcessParams): void {
  try {
    localStorage.setItem(presetKey(kind), JSON.stringify(params))
  } catch {
    /* 隐私模式等场景下忽略 */
  }
}

/* ==================== 图片解码 ==================== */

export async function loadImage(file: Blob): Promise<LoadedImage> {
  if (typeof createImageBitmap === 'function') {
    try {
      // from-image：按 EXIF 方向摆正手机拍摄的照片
      const bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' })
      return {
        source: bitmap,
        width: bitmap.width,
        height: bitmap.height,
        release: () => bitmap.close(),
      }
    } catch {
      /* 部分 WebView 不支持该选项，退回 <img> 解码 */
    }
  }

  const url = URL.createObjectURL(file)
  try {
    const img = await new Promise<HTMLImageElement>((resolve, reject) => {
      const el = new Image()
      const handleLoad = () => {
        el.removeEventListener('error', handleError)
        resolve(el)
      }
      const handleError = () => {
        el.removeEventListener('load', handleLoad)
        reject(new Error('图片解码失败，请先转换为 JPG / PNG'))
      }
      el.addEventListener('load', handleLoad)
      el.addEventListener('error', handleError)
      el.src = url
    })
    return {
      source: img,
      width: img.naturalWidth || img.width,
      height: img.naturalHeight || img.height,
      release: () => URL.revokeObjectURL(url),
    }
  } catch (error) {
    URL.revokeObjectURL(url)
    throw error
  }
}

/* ==================== Canvas 工具 ==================== */

interface CanvasPair {
  canvas: HTMLCanvasElement
  ctx: CanvasRenderingContext2D
}

function createCanvas(w: number, h: number): CanvasPair {
  const canvas = document.createElement('canvas')
  canvas.width = Math.max(1, w)
  canvas.height = Math.max(1, h)
  const ctx = canvas.getContext('2d', { willReadFrequently: true })
  if (!ctx) throw new Error('无法创建 Canvas 上下文')
  return { canvas, ctx }
}

export function toPngBlob(canvas: HTMLCanvasElement): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => (blob ? resolve(blob) : reject(new Error('导出 PNG 失败'))),
      'image/png',
    )
  })
}

/* ==================== 背景估计（仅签字使用） ==================== */

/** 把整幅灰度图按块平均降采样到 gw × gh 的小网格 */
function downsampleGrid(
  gray: Float32Array,
  w: number,
  h: number,
  gw: number,
  gh: number,
): Float32Array {
  const out = new Float32Array(gw * gh)
  for (let y = 0; y < gh; y++) {
    const y0 = Math.floor((y * h) / gh)
    const y1 = Math.max(y0 + 1, Math.floor(((y + 1) * h) / gh))
    for (let x = 0; x < gw; x++) {
      const x0 = Math.floor((x * w) / gw)
      const x1 = Math.max(x0 + 1, Math.floor(((x + 1) * w) / gw))
      let sum = 0
      let n = 0
      for (let sy = y0; sy < y1 && sy < h; sy++) {
        const row = sy * w
        for (let sx = x0; sx < x1 && sx < w; sx++) {
          sum += gray[row + sx]
          n++
        }
      }
      out[y * gw + x] = n ? sum / n : 0
    }
  }
  return out
}

/** 可分离滑动窗口均值模糊，边界按最近值延伸 */
function boxBlur1D(
  src: Float32Array,
  gw: number,
  gh: number,
  radius: number,
  horizontal: boolean,
): Float32Array {
  const out = new Float32Array(src.length)
  const len = horizontal ? gw : gh
  const outer = horizontal ? gh : gw
  const step = horizontal ? 1 : gw
  const outerStep = horizontal ? gw : 1
  const window = radius * 2 + 1

  for (let o = 0; o < outer; o++) {
    const base = o * outerStep
    let sum = 0
    for (let k = -radius; k <= radius; k++) {
      sum += src[base + clamp(k, 0, len - 1) * step]
    }
    for (let i = 0; i < len; i++) {
      out[base + i * step] = sum / window
      const leaving = clamp(i - radius, 0, len - 1)
      const entering = clamp(i + radius + 1, 0, len - 1)
      sum += src[base + entering * step] - src[base + leaving * step]
    }
  }
  return out
}

function blurGrid(
  src: Float32Array,
  gw: number,
  gh: number,
  radius: number,
  iterations = 3,
): Float32Array {
  if (radius < 1) return src
  let cur = src
  for (let i = 0; i < iterations; i++) {
    cur = boxBlur1D(cur, gw, gh, radius, true)
    cur = boxBlur1D(cur, gw, gh, radius, false)
  }
  return cur
}

function upsampleGrid(
  grid: Float32Array,
  gw: number,
  gh: number,
  w: number,
  h: number,
): Float32Array {
  const out = new Float32Array(w * h)
  for (let y = 0; y < h; y++) {
    const fy = ((y + 0.5) * gh) / h - 0.5
    const y0 = clamp(Math.floor(fy), 0, gh - 1)
    const y1 = Math.min(gh - 1, y0 + 1)
    const wy = clamp(fy - y0, 0, 1)
    for (let x = 0; x < w; x++) {
      const fx = ((x + 0.5) * gw) / w - 0.5
      const x0 = clamp(Math.floor(fx), 0, gw - 1)
      const x1 = Math.min(gw - 1, x0 + 1)
      const wx = clamp(fx - x0, 0, 1)
      const top = grid[y0 * gw + x0] + (grid[y0 * gw + x1] - grid[y0 * gw + x0]) * wx
      const bottom = grid[y1 * gw + x0] + (grid[y1 * gw + x1] - grid[y1 * gw + x0]) * wx
      out[y * w + x] = top + (bottom - top) * wy
    }
  }
  return out
}

/** 估计每个像素的纸张亮度（大尺度低频分量） */
function estimateBackground(
  data: Uint8ClampedArray,
  w: number,
  h: number,
): Float32Array {
  const gray = new Float32Array(w * h)
  for (let i = 0, p = 0; i < gray.length; i++, p += 4) {
    gray[i] = 0.299 * data[p] + 0.587 * data[p + 1] + 0.114 * data[p + 2]
  }

  // 先降采样再模糊：网格很小，纯 JS 循环也足够快
  const gw = Math.max(4, Math.round(w / 8))
  const gh = Math.max(4, Math.round(h / 8))
  const small = downsampleGrid(gray, w, h, gw, gh)
  const radius = Math.max(1, Math.round(Math.min(gw, gh) / 8))
  const blurred = blurGrid(small, gw, gh, radius)
  return upsampleGrid(blurred, gw, gh, w, h)
}

/* ==================== 去孤点（仅印章） ==================== */

function removeSpecks(alpha: Uint8ClampedArray, w: number, h: number): void {
  const src = alpha.slice()
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const i = y * w + x
      if (src[i] === 0) continue
      let neighbors = 0
      for (let dy = -1; dy <= 1; dy++) {
        const ny = y + dy
        if (ny < 0 || ny >= h) continue
        for (let dx = -1; dx <= 1; dx++) {
          if (dx === 0 && dy === 0) continue
          const nx = x + dx
          if (nx < 0 || nx >= w) continue
          if (src[ny * w + nx] > 32) neighbors++
        }
      }
      if (neighbors < 2) alpha[i] = 0
    }
  }
}

/* ==================== 质感 / 做旧 ==================== */

/** 32 位整数哈希，返回 0-1；同一坐标 + 种子结果稳定 */
function hash2(x: number, y: number, seed: number): number {
  let h = Math.imul(x, 374761393) + Math.imul(y, 668265263) + Math.imul(seed, 2246822519)
  h = Math.imul(h ^ (h >>> 13), 1274126177)
  h ^= h >>> 16
  return (h >>> 0) / 4294967296
}

/**
 * 生成一张 w×h 的值噪声场（0-1）。
 * cell 越大纹理越粗；双线性插值 + smoothstep 让噪点过渡柔和。
 */
function valueNoiseField(w: number, h: number, cell: number, seed: number): Float32Array {
  const size = Math.max(1, cell)
  const gw = Math.max(2, Math.ceil(w / size) + 2)
  const gh = Math.max(2, Math.ceil(h / size) + 2)
  const lattice = new Float32Array(gw * gh)
  for (let y = 0; y < gh; y++) {
    for (let x = 0; x < gw; x++) {
      lattice[y * gw + x] = hash2(x, y, seed)
    }
  }

  const out = new Float32Array(w * h)
  for (let y = 0; y < h; y++) {
    const fy = y / size
    const y0 = Math.min(gh - 2, Math.floor(fy))
    const wy = fy - y0
    const sy = wy * wy * (3 - 2 * wy)
    for (let x = 0; x < w; x++) {
      const fx = x / size
      const x0 = Math.min(gw - 2, Math.floor(fx))
      const wx = fx - x0
      const sx = wx * wx * (3 - 2 * wx)
      const top = lattice[y0 * gw + x0] + (lattice[y0 * gw + x0 + 1] - lattice[y0 * gw + x0]) * sx
      const bottom
        = lattice[(y0 + 1) * gw + x0]
          + (lattice[(y0 + 1) * gw + x0 + 1] - lattice[(y0 + 1) * gw + x0]) * sx
      out[y * w + x] = top + (bottom - top) * sy
    }
  }
  return out
}

/** 用像素内容做种子，保证同一张图每次处理得到相同的纹理 */
function seedFromData(data: Uint8ClampedArray): number {
  let h = 2166136261
  const step = 997 * 4
  for (let i = 0; i < data.length; i += step) {
    h = Math.imul(h ^ data[i], 16777619)
  }
  return h >>> 0
}

/**
 * 给 alpha 叠印泥质感：
 * - 低频噪声：印泥浓淡不均，出现浅色斑块
 * - 高频噪声：边缘毛糙、缺口（越靠近边缘越明显）
 */
function applyTexture(
  alpha: Uint8ClampedArray,
  w: number,
  h: number,
  kind: ImageProcessKind,
  texture: number,
  seed: number,
): void {
  const amount = clamp(texture / 100, 0, 1)
  if (amount <= 0) return

  const base = Math.min(w, h)
  const coarse = valueNoiseField(w, h, Math.max(3, Math.round(base / 30)), seed)
  const fine = valueNoiseField(w, h, Math.max(1, Math.round(base / 150)), seed + 7919)
  // 印章油墨更不均匀，签字只需一点墨量起伏
  const density = kind === 'seal' ? 0.42 : 0.18
  const edge = kind === 'seal' ? 0.45 : 0.2

  for (let i = 0; i < alpha.length; i++) {
    const raw = alpha[i]
    if (raw === 0) continue
    const a = raw / 255
    const patch = 1 - amount * density * (1 - coarse[i])
    const grain = 1 - amount * (0.1 + edge * (1 - a)) * (1 - fine[i])
    alpha[i] = clamp(a * patch * grain, 0, 1) * 255
  }
}

/* ==================== 核心算法（纯函数，便于单独验证） ==================== */

export interface Bounds {
  x: number
  y: number
  width: number
  height: number
}

export interface ExtractResult {
  /** 每个像素的 alpha（长度 w*h） */
  alpha: Uint8ClampedArray
  /** 浓墨区域的平均颜色，作为统一墨色 / 印色 */
  inkColor: [number, number, number]
  /** 内容包围盒（已含留白），无内容时为 null */
  bounds: Bounds | null
  /** 内容像素占比 */
  coverage: number
}

/**
 * 从 RGBA 像素中提取 alpha。只读取 `data`，不修改它。
 */
export function extractAlpha(
  data: Uint8ClampedArray,
  w: number,
  h: number,
  kind: ImageProcessKind,
  params: ProcessParams,
): ExtractResult {
  const total = w * h
  const t = clamp(params.strength / 100, 0, 1)
  // 强度越高，阈值越高：只保留颜色最重的那部分笔画
  const lo = kind === 'seal' ? 0.04 + 0.12 * t : 0.06 + 0.3 * t
  const hi = kind === 'seal' ? 0.12 + 0.36 * t : 0.25 + 0.45 * t

  const background = kind === 'signature' ? estimateBackground(data, w, h) : null
  const score = new Float32Array(total)

  // 第一遍：计算每个像素的“墨迹得分”，并统计浓墨区域的平均颜色
  let sumR = 0
  let sumG = 0
  let sumB = 0
  let sumCount = 0

  for (let i = 0, p = 0; i < total; i++, p += 4) {
    const r = data[p]
    const g = data[p + 1]
    const b = data[p + 2]
    let value: number

    if (kind === 'signature' && background) {
      const bg = Math.max(background[i], 1)
      const luminance = 0.299 * r + 0.587 * g + 0.114 * b
      // 归一化后纸张接近 255，笔画明显低于纸张；换算成 0-1 的墨量
      value = clamp(1 - luminance / bg, 0, 1)
    } else {
      const maxc = Math.max(r, g, b)
      const minc = Math.min(r, g, b)
      const chroma = params.mode === 'blue'
        ? b - Math.max(r, g)
        : r - Math.max(g, b)
      const saturation = maxc > 0 ? (maxc - minc) / maxc : 0
      // 饱和度门限：黑字、灰色阴影的通道差很小，会被压到接近 0；
      // 门限取得很低，避免把褪色的浅红印泥一起丢掉
      const gate = clamp((saturation - 0.05) / 0.1, 0, 1)
      value = clamp(chroma / 255, 0, 1) * gate
    }

    score[i] = value
    if (value > hi) {
      sumR += r
      sumG += g
      sumB += b
      sumCount++
    }
  }

  let fallbackInk: [number, number, number] = [200, 30, 30]
  if (kind === 'signature') fallbackInk = [26, 26, 26]
  else if (params.mode === 'blue') fallbackInk = [30, 58, 200]
  const inkColor: [number, number, number] = sumCount
    ? [Math.round(sumR / sumCount), Math.round(sumG / sumCount), Math.round(sumB / sumCount)]
    : fallbackInk

  // 第二遍：得分 → alpha
  const alpha = new Uint8ClampedArray(total)
  const gammaExp = 1 / Math.max(0.2, params.gamma)
  for (let i = 0; i < total; i++) {
    let a = smoothstep(lo, hi, score[i])
    if (a > 0 && gammaExp !== 1) a = Math.pow(a, gammaExp)
    alpha[i] = a * 255
  }

  if (params.texture > 0) {
    applyTexture(alpha, w, h, kind, params.texture, seedFromData(data))
  }

  if (kind === 'seal') removeSpecks(alpha, w, h)

  // 包围盒 + 覆盖率
  let minX = w
  let minY = h
  let maxX = -1
  let maxY = -1
  let contentPixels = 0
  for (let y = 0; y < h; y++) {
    const row = y * w
    for (let x = 0; x < w; x++) {
      if (alpha[row + x] > CROP_ALPHA) {
        contentPixels++
        if (x < minX) minX = x
        if (x > maxX) maxX = x
        if (y < minY) minY = y
        if (y > maxY) maxY = y
      }
    }
  }

  let bounds: Bounds | null = null
  if (maxX >= minX && maxY >= minY) {
    const pad = Math.round(params.padding * Math.max(maxX - minX + 1, maxY - minY + 1))
    const left = clamp(minX - pad, 0, w - 1)
    const top = clamp(minY - pad, 0, h - 1)
    const right = clamp(maxX + pad, 0, w - 1)
    const bottom = clamp(maxY + pad, 0, h - 1)
    bounds = { x: left, y: top, width: right - left + 1, height: bottom - top + 1 }
  }

  return { alpha, inkColor, bounds, coverage: contentPixels / total }
}

/* ==================== 主流程 ==================== */

export async function processImage(
  file: Blob,
  kind: ImageProcessKind,
  params: ProcessParams,
): Promise<ProcessResult> {
  const loaded = await loadImage(file)
  try {
    const longEdge = Math.max(loaded.width, loaded.height)
    const scale = longEdge > params.maxEdge ? params.maxEdge / longEdge : 1
    const w = Math.max(1, Math.round(loaded.width * scale))
    const h = Math.max(1, Math.round(loaded.height * scale))

    const work = createCanvas(w, h)
    work.ctx.drawImage(loaded.source, 0, 0, w, h)
    const imageData = work.ctx.getImageData(0, 0, w, h)
    const data = imageData.data

    const { alpha, inkColor, bounds, coverage } = extractAlpha(data, w, h, kind, params)

    // 写回 RGBA：签字统一墨色（笔画浓淡由 alpha 表达），印章可选择统一印色
    const uniformColor = kind === 'signature' || params.colorize
    const [inkR, inkG, inkB] = inkColor
    for (let i = 0, p = 0; i < alpha.length; i++, p += 4) {
      if (uniformColor) {
        data[p] = inkR
        data[p + 1] = inkG
        data[p + 2] = inkB
      }
      data[p + 3] = alpha[i]
    }

    const crop: Bounds = bounds ?? { x: 0, y: 0, width: w, height: h }
    const out = createCanvas(crop.width, crop.height)
    const outData = out.ctx.createImageData(crop.width, crop.height)
    for (let y = 0; y < crop.height; y++) {
      const srcStart = ((crop.y + y) * w + crop.x) * 4
      outData.data.set(data.subarray(srcStart, srcStart + crop.width * 4), y * crop.width * 4)
    }
    out.ctx.putImageData(outData, 0, 0)

    const blob = await toPngBlob(out.canvas)
    return { blob, width: crop.width, height: crop.height, coverage }
  } finally {
    loaded.release()
  }
}

/** 处理质量提示：返回 null 表示看起来正常 */
export function resultWarning(coverage: number): string | null {
  if (coverage <= 0.003) {
    return '几乎没有提取到内容，请降低“去背景强度”，或选择“使用原图”。'
  }
  if (coverage >= 0.95) {
    return '背景可能没有被去掉，请提高“去背景强度”。'
  }
  return null
}
