import { exists, mkdir, readDir, readFile, remove, writeFile } from '@tauri-apps/plugin-fs'
import { save as saveFileDialog } from '@tauri-apps/plugin-dialog'
import type { WorkspaceListItem, WorkspaceSnapshot } from '@/types/workspace'

/** 工作进度根目录名，位于用户配置的数据目录下 */
const WORKSPACES_DIRNAME = 'workspaces'
const PROGRESS_FILENAME = 'progress.json'
const HISTORY_FILENAME = 'history.json'
/** 当前快照格式版本：v2 起模板/表格以路径引用 */
const SNAPSHOT_VERSION = 2 as const
/** 每个项目最多保留的历史版本数（不含当前版本），超出后丢弃最旧的 */
const MAX_HISTORY_VERSIONS = 50

const encoder = new TextEncoder()
const decoder = new TextDecoder()

function trimTrailingSlash(path: string): string {
  return path.replace(/[/\\]+$/, '')
}

export function workspacesRoot(dataPath: string): string {
  return `${trimTrailingSlash(dataPath)}/${WORKSPACES_DIRNAME}`
}

export function workspaceDir(dataPath: string, id: string): string {
  return `${workspacesRoot(dataPath)}/${id}`
}

function progressPath(dataPath: string, id: string): string {
  return `${workspaceDir(dataPath, id)}/${PROGRESS_FILENAME}`
}

function historyPath(dataPath: string, id: string): string {
  return `${workspaceDir(dataPath, id)}/${HISTORY_FILENAME}`
}

function encodeJson(data: unknown): Uint8Array {
  return encoder.encode(JSON.stringify(data, null, 2))
}

function extensionOf(fileName: string): string {
  const idx = fileName.lastIndexOf('.')
  return idx > 0 ? fileName.slice(idx).toLowerCase() : ''
}

function mimeOf(fileName: string): string {
  switch (extensionOf(fileName)) {
    case '.pdf':
      return 'application/pdf'
    case '.docx':
      return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    case '.xlsx':
      return 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    case '.xls':
      return 'application/vnd.ms-excel'
    default:
      return 'application/octet-stream'
  }
}

function sanitizeFileName(name: string): string {
  return name.replace(/[\\/:*?"<>|]/g, '_').trim().replace(/\.+$/, '')
}

function createWorkspaceId(): string {
  return `ws_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`
}

function createRevisionId(): string {
  return `rev_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`
}

/** 旧快照没有 revisionId 时，用保存时间作为版本标识 */
export function revisionKey(snapshot: WorkspaceSnapshot): string {
  return snapshot.revisionId || snapshot.savedAt
}

/** 旧版（v1 副本式）工作进度记录：不再兼容，列表里会被跳过并计数提示 */
export class LegacyWorkspaceError extends Error {
  constructor() {
    super('旧版工作进度记录已不再支持')
    this.name = 'LegacyWorkspaceError'
  }
}

/** 历史记录扫描结果 */
export interface WorkspaceList {
  items: WorkspaceListItem[]
  /** 因格式过旧被忽略的记录数（v1 副本式） */
  ignored: number
}

export interface SaveWorkspaceInput {
  dataPath: string
  /**
   * 要更新的项目 ID。
   * 传入时在同一个项目目录内写入新版本，旧版本进入历史；
   * 省略时创建一个新项目。
   */
  id?: string
  title: string
  templateType: 'pdf' | 'docx'
  /** 原始模板文件绝对路径 */
  templatePath: string
  /** 原始表格文件绝对路径 */
  excelPath: string
  pdfScale: number
  iconList: WorkspaceSnapshot['iconList']
  loopBlocks: WorkspaceSnapshot['loopBlocks']
  docxStructure: WorkspaceSnapshot['docxStructure']
  nameParts: WorkspaceSnapshot['nameParts']
}

/** history.json 的结构 */
interface WorkspaceHistoryFile {
  projectId: string
  versions: WorkspaceSnapshot[]
}

function isSnapshot(value: unknown): value is WorkspaceSnapshot {
  return !!value && typeof value === 'object' && !!(value as WorkspaceSnapshot).id
}

function assertSnapshot(snapshot: unknown): WorkspaceSnapshot {
  if (!isSnapshot(snapshot)) {
    throw new Error('工作进度文件格式不正确')
  }
  if (snapshot.version !== SNAPSHOT_VERSION) {
    throw new LegacyWorkspaceError()
  }
  return snapshot
}

async function readJsonFile(path: string): Promise<unknown> {
  const bytes = await readFile(path)
  return JSON.parse(decoder.decode(bytes))
}

/** 读取当前版本（progress.json）；不存在或损坏时返回 null */
async function readCurrentSnapshot(dataPath: string, id: string): Promise<WorkspaceSnapshot | null> {
  try {
    if (!(await exists(progressPath(dataPath, id)))) return null
    return assertSnapshot(await readJsonFile(progressPath(dataPath, id)))
  } catch (error) {
    if (error instanceof LegacyWorkspaceError) throw error
    console.warn(`读取项目 ${id} 的当前版本失败:`, error)
    return null
  }
}

/** 读取项目的历史版本（不含当前版本），最新版本在前 */
async function readHistory(dataPath: string, id: string): Promise<WorkspaceSnapshot[]> {
  try {
    if (!(await exists(historyPath(dataPath, id)))) return []
    const raw = (await readJsonFile(historyPath(dataPath, id))) as Partial<WorkspaceHistoryFile> | null
    const versions: unknown[] = Array.isArray(raw?.versions) ? raw.versions : []
    return versions.filter(isSnapshot).filter(v => v.version === SNAPSHOT_VERSION)
  } catch (error) {
    console.warn(`读取项目 ${id} 的历史版本失败:`, error)
    return []
  }
}

async function writeHistory(dataPath: string, id: string, versions: WorkspaceSnapshot[]): Promise<void> {
  const file: WorkspaceHistoryFile = {
    projectId: id,
    versions: versions.slice(0, MAX_HISTORY_VERSIONS),
  }
  await writeFile(historyPath(dataPath, id), encodeJson(file))
}

/**
 * 写入一次工作进度。
 * - 不传 id：创建新项目；
 * - 传 id：沿用同一个项目目录，当前版本被推入历史，再写入新版本。
 * 只记录模板/表格的原始路径，不复制字节；原文件内容改动后恢复即生效。
 */
export async function saveWorkspace(input: SaveWorkspaceInput): Promise<WorkspaceSnapshot> {
  const id = input.id || createWorkspaceId()
  const dir = workspaceDir(input.dataPath, id)
  await mkdir(dir, { recursive: true })

  // 更新已有项目时，先把当前版本归档到历史，避免旧进度被覆盖后无法找回
  if (input.id) {
    let history = await readHistory(input.dataPath, id)
    const current = await readCurrentSnapshot(input.dataPath, id)
    if (current) {
      const currentKey = revisionKey(current)
      history = [current, ...history.filter(v => revisionKey(v) !== currentKey)]
    }
    await writeHistory(input.dataPath, id, history)
  }

  const snapshot: WorkspaceSnapshot = {
    version: SNAPSHOT_VERSION,
    id,
    revisionId: createRevisionId(),
    title: input.title,
    savedAt: new Date().toISOString(),
    templateType: input.templateType,
    templatePath: input.templatePath,
    excelPath: input.excelPath,
    pdfScale: input.pdfScale,
    iconList: input.iconList,
    loopBlocks: input.loopBlocks,
    docxStructure: input.docxStructure,
    nameParts: input.nameParts,
  }

  await writeFile(progressPath(input.dataPath, id), encodeJson(snapshot))
  return snapshot
}

/**
 * 读取工作进度快照。
 * - 不传 revisionId：读取当前版本；
 * - 传 revisionId：读取项目历史中的对应版本。
 */
export async function readWorkspace(
  dataPath: string,
  id: string,
  revisionId?: string,
): Promise<WorkspaceSnapshot> {
  const current = assertSnapshot(await readJsonFile(progressPath(dataPath, id)))

  if (!revisionId || revisionKey(current) === revisionId) {
    return current
  }

  const history = await readHistory(dataPath, id)
  const matched = history.find(v => revisionKey(v) === revisionId)
  if (!matched) {
    throw new Error('该历史版本已不存在')
  }
  return matched
}

/**
 * 列出项目的全部版本，当前版本在最前，其后是历史版本（由新到旧）。
 * 用于项目页 / 历史记录页的「历史版本」弹窗。
 */
export async function listWorkspaceRevisions(dataPath: string, id: string): Promise<WorkspaceSnapshot[]> {
  const current = await readCurrentSnapshot(dataPath, id)
  if (!current) return []
  const currentKey = revisionKey(current)
  const history = await readHistory(dataPath, id)
  return [current, ...history.filter(v => revisionKey(v) !== currentKey)]
}

/** 扫描数据目录，按保存时间倒序列出全部项目（跳过旧版/损坏记录，并统计旧版条数） */
export async function listWorkspaces(dataPath: string): Promise<WorkspaceList> {
  if (!dataPath) return { items: [], ignored: 0 }
  const root = workspacesRoot(dataPath)
  try {
    if (!(await exists(root))) return { items: [], ignored: 0 }
  } catch (error) {
    console.error('读取工作进度目录失败:', error)
    return { items: [], ignored: 0 }
  }

  let entries: Awaited<ReturnType<typeof readDir>> = []
  try {
    entries = await readDir(root)
  } catch (error) {
    console.error('读取工作进度目录失败:', error)
    return { items: [], ignored: 0 }
  }

  const items: WorkspaceListItem[] = []
  let ignored = 0
  for (const entry of entries) {
    if (!entry.isDirectory) continue
    try {
      const snapshot = await readWorkspace(dataPath, entry.name)
      const history = await readHistory(dataPath, entry.name)
      items.push({
        id: snapshot.id,
        title: snapshot.title || snapshot.id,
        savedAt: snapshot.savedAt,
        templateType: snapshot.templateType,
        templatePath: snapshot.templatePath,
        excelPath: snapshot.excelPath,
        iconCount: snapshot.iconList?.length ?? 0,
        revisionCount: 1 + history.length,
      })
    } catch (error) {
      if (error instanceof LegacyWorkspaceError) {
        ignored++
        console.info(`已忽略旧版工作进度记录 ${entry.name}`)
      } else {
        console.warn(`跳过不可用的工作进度记录 ${entry.name}:`, error)
      }
    }
  }

  items.sort((a, b) => (a.savedAt < b.savedAt ? 1 : a.savedAt > b.savedAt ? -1 : 0))
  return { items, ignored }
}

/** 读取本地文件为 File（用于预览 / 上传）；文件不存在时返回 null */
export async function readPathAsFile(path: string): Promise<File | null> {
  try {
    if (!(await exists(path))) return null
    const bytes = await readFile(path)
    const name = path.split(/[/\\]/).pop() || 'file'
    return new File([bytes], name, { type: mimeOf(name) })
  } catch (error) {
    console.error(`读取文件失败 ${path}:`, error)
    return null
  }
}

/** 删除一个项目（连同它的历史版本；模板与表格原文件不受影响） */
export async function deleteWorkspace(dataPath: string, id: string): Promise<void> {
  await remove(workspaceDir(dataPath, id), { recursive: true })
}

/** 将快照导出为一份用户自选的 .json 文件，返回导出路径；用户取消时返回 null */
export async function exportWorkspaceJson(snapshot: WorkspaceSnapshot): Promise<string | null> {
  const base = sanitizeFileName(snapshot.title) || snapshot.id
  const target = await saveFileDialog({
    defaultPath: `${base}.json`,
    filters: [{ name: 'JSON', extensions: ['json'] }],
    title: '导出工作进度',
  })
  if (!target) return null
  await writeFile(target, encodeJson(snapshot))
  return target
}
