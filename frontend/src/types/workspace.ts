import type { StoreIcon, LoopBlock, DocxStructureItem } from './icon'

/** 文件名配置中的一段：字段 / 自增序号 / 自定义文本 / 连接符 */
export interface NamePart {
  type: 'field' | 'seq' | 'text' | 'sep'
  field?: string
  start?: number
  digits?: number
  text?: string
}

/**
 * 工作进度快照，同时也是项目历史中的一个版本。
 *
 * 一个项目对应 `${dataPath}/workspaces/<id>/` 目录：
 * - `progress.json` 保存当前版本；
 * - `history.json` 保存该项目历次保存的版本（最新版本在最前）。
 *
 * 模板与表格只记录原始文件的绝对路径，不再复制字节：恢复时按路径重读，
 * Excel 会重新解析字段，因此原文件内容改动后重新打开即可生效。
 */
export interface WorkspaceSnapshot {
  /** 快照格式版本；v2 起模板/表格以路径引用（v1 的副本式记录不再兼容） */
  version: 2
  /** 项目 ID：同一项目多次保存始终复用这个 ID */
  id: string
  /** 版本 ID：每次保存生成一个新值；旧版记录可能没有该字段 */
  revisionId?: string
  /** 保存时填写的名称 */
  title: string
  /** 保存时间（ISO 字符串） */
  savedAt: string
  templateType: 'pdf' | 'docx'
  /** 原始模板文件绝对路径 */
  templatePath: string
  /** 原始表格文件绝对路径 */
  excelPath: string
  /** PDF 预览缩放倍率，恢复后标注坐标才能对齐 */
  pdfScale: number
  iconList: StoreIcon[]
  loopBlocks: LoopBlock[]
  docxStructure: DocxStructureItem[]
  nameParts: NamePart[]
}

/** 项目列表条目：一个项目只出现一次，历史版本收在项目内部 */
export interface WorkspaceListItem {
  id: string
  title: string
  savedAt: string
  templateType: 'pdf' | 'docx'
  /** 原始模板文件绝对路径 */
  templatePath: string
  /** 原始表格文件绝对路径 */
  excelPath: string
  /** 标注数量，列表里用于一眼看出进度 */
  iconCount: number
  /** 历史版本数量（含当前版本） */
  revisionCount: number
}
