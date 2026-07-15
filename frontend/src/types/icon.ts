export type ConditionOp = '等于' | '不等于' | '包含' | '不包含' | '为空' | '不为空'
export type MatchMode = '所有' | '任一'
export type LogicType = 'simple' | 'advanced'

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
  type: 'field' | 'image' | 'icon'
  fieldName?: string
  fontFamily?: string
  fontWeight?: number
  opacity?: number
  color?: string
  src?: string
  icon?: string
  size?: number
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
