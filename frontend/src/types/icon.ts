export type ConditionOp = '等于' | '不等于' | '包含' | '不包含' | '为空' | '不为空'
export type MatchMode = '所有' | '任一'
export type LogicType = 'simple' | 'advanced'

/** 材料类型：表格字段 / 签字 / 印章 / 图标 / 文本 */
export type MaterialKind = 'table' | 'signature' | 'seal' | 'icon' | 'text'

export interface Condition {
  id: number
  field: string | null
  op: ConditionOp
  value: string
}

export interface ConditionGroup {
  id: number
  matchMode: MatchMode
  conditions: Condition[]
}

export interface IconOption {
  type: 'field' | 'image' | 'icon' | 'text'
  fieldName?: string
  fontFamily?: string
  fontWeight?: number
  /** 斜体（字段 / 文本类型） */
  italic?: boolean
  /** 是否对文字应用字体扰动，缺省视为 true */
  applyJitter?: boolean
  opacity?: number
  color?: string
  src?: string
  icon?: string
  text?: string
  size?: number
  /** image 类型的子分类：签字 / 印章 */
  imageKind?: 'signature' | 'seal'
  /** 图片圆角，取值 0-50，表示短边尺寸的百分比 */
  cornerRadius?: number
  /** 是否锁定纵横比（印章）：false 时拉伸填满正方形区域，缺省视为 true */
  keepRatio?: boolean
}

export interface StoreIcon {
  id: number
  mode: 'single' | 'conditional'
  pageIndex: number
  pointer: { clientX: number; clientY: number }
  option: IconOption
  logicType?: LogicType
  conditions?: Condition[]
  matchMode?: MatchMode
  groups?: ConditionGroup[]
  groupConnectors?: MatchMode[]
  size?: number
  scale?: number
  rotation?: number
}
