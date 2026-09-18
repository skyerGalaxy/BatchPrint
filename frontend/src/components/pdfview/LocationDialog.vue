<script setup lang="ts">
import { ref, watch } from "vue";
import { useBPStore } from "@/stores/bpstore";
import MaterialSettings, { type MaterialKind } from "./MaterialSettings.vue";
import type { Condition, ConditionGroup, IconOption, LogicType, MatchMode, StoreIcon } from "@/types/icon";
const props = defineProps({
  dialog: {
    type: Boolean,
    required: true
  },
  pageIndex: {
    type: Number,
    required: true
  },
  pointer: {
    type: Object as () => { clientX: number; clientY: number },
    required: true
  },
  /** 右键空白新增时的材料类型 */
  initialPanel: {
    type: String as () => MaterialKind,
    default: 'table'
  },
  /** 双击已有材料编辑时传入 */
  initialIcon: {
    type: Object as () => StoreIcon | null,
    default: null
  }
});

const emits = defineEmits(['update:dialog']);

const bpStore = useBPStore();

type DialogTab = 'single' | 'conditional';
const tab = ref<DialogTab>('single');
const step = ref(1);

/** 当前材料类型 */
const kind = ref<MaterialKind>('table');
/** 当前编辑的选项（常规与条件第二步共享同一份） */
const currentOption = ref<IconOption>({} as IconOption);
/** 编辑已有项时的 id；新增为 null */
const editId = ref<number | null>(null);

const ops = ['等于', '不等于', '包含', '不包含', '为空', '不为空'];

const logicType = ref<LogicType>('simple');
const matchMode = ref<MatchMode>('所有');
const conditions = ref<Condition[]>([
  { id: Date.now(), field: null, op: '等于', value: '' }
]);
const groups = ref<ConditionGroup[]>([
  { id: Date.now(), matchMode: '所有', conditions: [{ id: Date.now() + 1, field: null, op: '等于', value: '' }] }
]);
const groupConnectors = ref<MatchMode[]>([]);

let nextId = Date.now();
function genId(): number {
  return ++nextId;
}

const snackbar = ref(false);
const snackbarMsg = ref('');

const KIND_TITLES: Record<MaterialKind, string> = {
  table: '表格字段',
  signature: '签字',
  seal: '印章',
  icon: '图标',
  text: '文本',
};

/* ========= 默认选项 ========= */
/** 各类材料需要记忆的样式字段（排除 fieldName/src/icon/text 等标识字段） */
const STYLE_KEYS: Record<MaterialKind, (keyof IconOption)[]> = {
  table: ['fontFamily', 'fontWeight', 'italic', 'color', 'opacity', 'size'],
  signature: ['size', 'cornerRadius', 'opacity'],
  seal: ['size', 'cornerRadius', 'opacity', 'keepRatio'],
  icon: ['size', 'color', 'opacity'],
  text: ['fontFamily', 'fontWeight', 'italic', 'color', 'opacity', 'size'],
};

function extractStyle(k: MaterialKind, o: IconOption): Partial<IconOption> {
  const style: Partial<IconOption> = {};
  for (const key of STYLE_KEYS[k]) {
    const v = o[key];
    if (v !== undefined && v !== null) (style as Record<string, unknown>)[key] = v;
  }
  return style;
}

function createDefaultOption(k: MaterialKind): IconOption {
  const firstField = bpStore.fieldNames[0] ?? '';
  const firstSignature = bpStore.imageList_signature[0] ?? '';
  const firstSeal = bpStore.imageList_seal[0] ?? '';
  let base: IconOption;
  switch (k) {
    case 'signature':
      base = { type: 'image', imageKind: 'signature', src: firstSignature, size: 120, cornerRadius: 0, opacity: 1 };
      break;
    case 'seal':
      base = { type: 'image', imageKind: 'seal', src: firstSeal, size: 120, cornerRadius: 0, opacity: 1, keepRatio: true };
      break;
    case 'icon':
      base = { type: 'icon', icon: '✓', color: '#000000', opacity: 1, size: 120 };
      break;
    case 'text':
      base = { type: 'text', text: '自定义文本', fontFamily: '楷体', fontWeight: 400, italic: false, color: '#000000', opacity: 1, size: 120 };
      break;
    case 'table':
    default:
      base = { type: 'field', fieldName: firstField, fontFamily: '楷体', fontWeight: 400, italic: false, color: '#000000', opacity: 1, size: 120 };
      break;
  }
  // 同类型材料沿用上次确认的样式，标识字段仍取当前默认
  return bpStore.instantiateOption(k, base);
}

function kindForIcon(icon: StoreIcon): MaterialKind {
  const t = icon.option?.type;
  if (t === 'field') return 'table';
  if (t === 'icon') return 'icon';
  if (t === 'text') return 'text';
  if (t === 'image') {
    if (icon.option.imageKind) return icon.option.imageKind;
    // 兼容旧数据：按 src 出现在哪个列表推导
    const src = icon.option.src ?? '';
    if (src && bpStore.imageList_signature.includes(src)) return 'signature';
    return 'seal';
  }
  return 'table';
}

/* ========= 初始化 / 重置 ========= */
function freshConditions(): Condition[] {
  return [{ id: genId(), field: null, op: '等于', value: '' }];
}

function initDialog() {
  const editing = props.initialIcon;
  step.value = 1;
  nextId = Date.now();

  if (editing) {
    editId.value = editing.id;
    kind.value = kindForIcon(editing);
    currentOption.value = JSON.parse(JSON.stringify(editing.option ?? {}));
    tab.value = editing.mode === 'conditional' ? 'conditional' : 'single';
    logicType.value = editing.logicType ?? 'simple';
    matchMode.value = editing.matchMode ?? '所有';
    conditions.value = editing.conditions?.length
      ? JSON.parse(JSON.stringify(editing.conditions))
      : freshConditions();
    groups.value = editing.groups?.length
      ? JSON.parse(JSON.stringify(editing.groups))
      : [{ id: genId(), matchMode: '所有', conditions: freshConditions() }];
    groupConnectors.value = editing.groupConnectors?.length
      ? JSON.parse(JSON.stringify(editing.groupConnectors))
      : [];
  } else {
    editId.value = null;
    kind.value = props.initialPanel;
    currentOption.value = createDefaultOption(props.initialPanel);
    tab.value = 'single';
    logicType.value = 'simple';
    matchMode.value = '所有';
    conditions.value = freshConditions();
    groups.value = [{ id: genId(), matchMode: '所有', conditions: freshConditions() }];
    groupConnectors.value = [];
  }
}

watch(() => props.dialog, (open) => {
  if (open) initDialog();
});

watch(tab, () => {
  step.value = 1;
});

/* ========= 条件校验（沿用原逻辑） ========= */
function isConditionValid(cond: Condition): boolean {
  if (!cond.field) return false;
  if (cond.op !== '为空' && cond.op !== '不为空' && !cond.value.trim()) return false;
  return true;
}

function validateBeforeAdd(condList: Condition[]): boolean {
  if (condList.length === 0) return true;
  const last = condList[condList.length - 1];
  if (!isConditionValid(last)) {
    const reason = !last.field ? '请选择字段' : '请填写值';
    snackbarMsg.value = `上一条条件不完整：${reason}`;
    snackbar.value = true;
    return false;
  }
  return true;
}

function validateAllSimple(): boolean {
  for (const c of conditions.value) {
    if (!isConditionValid(c)) {
      snackbarMsg.value = '请确保所有条件的字段和值均已填写完整';
      snackbar.value = true;
      return false;
    }
  }
  return true;
}

function validateAllAdvanced(): boolean {
  for (const group of groups.value) {
    for (const c of group.conditions) {
      if (!isConditionValid(c)) {
        snackbarMsg.value = '请确保所有条件组的字段和值均已填写完整';
        snackbar.value = true;
        return false;
      }
    }
  }
  return true;
}

function addCondition() {
  if (!validateBeforeAdd(conditions.value)) return;
  conditions.value.push({ id: genId(), field: null, op: '等于', value: '' });
}

function removeCondition(index: number) {
  conditions.value.splice(index, 1);
}

function addGroup() {
  if (!validateBeforeAdd(groups.value[groups.value.length - 1]?.conditions || [])) return;
  groups.value.push({
    id: genId(),
    matchMode: '所有',
    conditions: [{ id: genId(), field: null, op: '等于', value: '' }]
  });
  groupConnectors.value.push('所有');
}

function removeGroup(index: number) {
  groups.value.splice(index, 1);
  if (groups.value.length > 0 && groupConnectors.value.length > 0) {
    const connectorIdx = index >= groupConnectors.value.length ? groupConnectors.value.length - 1 : index;
    groupConnectors.value.splice(connectorIdx, 1);
  }
}

function addGroupCondition(groupIndex: number) {
  if (!validateBeforeAdd(groups.value[groupIndex].conditions)) return;
  groups.value[groupIndex].conditions.push({ id: genId(), field: null, op: '等于', value: '' });
}

function removeGroupCondition(groupIndex: number, condIndex: number) {
  groups.value[groupIndex].conditions.splice(condIndex, 1);
}

function goNext() {
  if (logicType.value === 'simple' && !validateAllSimple()) return;
  if (logicType.value === 'advanced' && !validateAllAdvanced()) return;
  step.value++;
}

/* ========= 材料设置校验 ========= */
function validateOption(): boolean {
  const o = currentOption.value;
  if (kind.value === 'table' && !o.fieldName) {
    snackbarMsg.value = '请选择 Excel 字段';
    snackbar.value = true;
    return false;
  }
  if ((kind.value === 'signature' || kind.value === 'seal') && !o.src) {
    snackbarMsg.value = `请选择${KIND_TITLES[kind.value]}图片`;
    snackbar.value = true;
    return false;
  }
  if (kind.value === 'text' && !o.text?.trim()) {
    snackbarMsg.value = '请输入文本内容';
    snackbar.value = true;
    return false;
  }
  if (kind.value === 'icon' && !o.icon) {
    snackbarMsg.value = '请选择图标';
    snackbar.value = true;
    return false;
  }
  return true;
}

function validateConditional(): boolean {
  if (logicType.value === 'simple') {
    if (conditions.value.filter(c => isConditionValid(c)).length < 1) {
      snackbarMsg.value = '请至少添加一个完整条件';
      snackbar.value = true;
      return false;
    }
  } else {
    const hasAny = groups.value.some(g => g.conditions.some(c => isConditionValid(c)));
    if (!hasAny) {
      snackbarMsg.value = '请至少添加一个完整条件';
      snackbar.value = true;
      return false;
    }
  }
  return true;
}

/* ========= 确认 ========= */
function buildIcon(id: number): StoreIcon {
  const option = JSON.parse(JSON.stringify(currentOption.value)) as IconOption;
  const result: StoreIcon = {
    id,
    pageIndex: props.pageIndex,
    pointer: props.pointer,
    mode: tab.value === 'conditional' ? 'conditional' : 'single',
    option,
    size: option.size ?? 120,
    scale: bpStore.pdfScale,
  };

  if (result.mode === 'conditional') {
    result.logicType = logicType.value;
    if (logicType.value === 'simple') {
      result.conditions = JSON.parse(JSON.stringify(conditions.value));
      result.matchMode = matchMode.value;
    } else {
      result.groups = JSON.parse(JSON.stringify(groups.value));
      result.groupConnectors = JSON.parse(JSON.stringify(groupConnectors.value));
    }
  }
  return result;
}

function handleConfirm() {
  if (!validateOption()) return;
  if (tab.value === 'conditional' && !validateConditional()) return;

  // 记忆本类型材料的样式，后续新拖入/新建的同类材料沿用，直到再次变更
  bpStore.saveMaterialStyle(kind.value, extractStyle(kind.value, currentOption.value));

  if (editId.value !== null) {
    // 编辑已有项：保留 id/位置/旋转，更新其余字段
    const idx = bpStore.iconList.findIndex(i => i.id === editId.value);
    if (idx >= 0) {
      const old = bpStore.iconList[idx] as StoreIcon;
      const rotation = old.rotation;
      const built = buildIcon(editId.value);
      built.rotation = rotation;
      bpStore.iconList.splice(idx, 1, built);
    }
  } else {
    const maxId = bpStore.iconList.reduce((max, i) => Math.max(max, i.id), 0);
    bpStore.iconList.push(buildIcon(maxId + 1));
  }

  emits('update:dialog', false);
}

function handleCancel() {
  emits('update:dialog', false);
}
</script>

<template>
  <v-dialog :model-value="dialog" @update:model-value="emits('update:dialog', $event)" max-width="560">
    <v-card class="loc-card" rounded="xl" elevation="8">
      <v-card-item class="loc-card-header">
        <div class="loc-title-row">
          <span class="loc-title">{{ KIND_TITLES[kind] }}设置</span>
          <span v-if="editId !== null" class="loc-edit-badge">编辑</span>
        </div>
        <v-tabs
          v-model="tab"
          fixed-tabs
          grow
          color="#4f8cff"
          slider-color="#4f8cff"
          class="bento-tabs"
        >
          <v-tab value="single">常规</v-tab>
          <v-tab value="conditional">条件</v-tab>
        </v-tabs>
      </v-card-item>

      <v-card-text class="loc-card-body">
        <!-- ============ 常规 ============ -->
        <div v-show="tab === 'single'" class="loc-pane">
          <MaterialSettings v-model:option="currentOption" :kind="kind" />
        </div>

        <!-- ============ 条件：两步 ============ -->
        <div v-show="tab === 'conditional'" class="loc-pane">
          <!-- 第一步：条件 -->
          <div v-if="step === 1" class="cond-step">
            <div class="cond-header">
              <div class="cond-steps">
                <span class="step-dot active">1</span>
                <span class="step-name active">设置条件</span>
                <span class="step-sep">→</span>
                <span class="step-dot">2</span>
                <span class="step-name">{{ KIND_TITLES[kind] }}设置</span>
              </div>
              <v-chip
                size="x-small"
                variant="outlined"
                color="grey"
                class="adv-chip"
                @click="logicType = logicType === 'simple' ? 'advanced' : 'simple'"
              >
                {{ logicType === 'simple' ? '高级筛选' : '简易筛选' }}
              </v-chip>
            </div>

            <div class="cond-body-simple" v-if="logicType === 'simple'">
              <div class="cond-match-mode">
                <span class="mode-label-text">符合以下</span>
                <v-btn-toggle v-model="matchMode" mandatory density="compact" class="mode-toggle-pills">
                  <v-btn value="所有" size="x-small" variant="flat" class="toggle-pill">且</v-btn>
                  <v-btn value="任一" size="x-small" variant="flat" class="toggle-pill">或</v-btn>
                </v-btn-toggle>
                <span class="mode-label-text">条件</span>
              </div>

              <div class="cond-scroll">
                <div v-for="(cond, idx) in conditions" :key="cond.id" class="cond-row-bento">
                  <v-select
                    :items="bpStore.fieldNames"
                    v-model="cond.field"
                    density="compact"
                    variant="outlined"
                    hide-details
                    placeholder="字段"
                    class="bento-field"
                  />
                  <v-select
                    :items="ops"
                    v-model="cond.op"
                    density="compact"
                    variant="outlined"
                    hide-details
                    class="bento-op"
                  />
                  <v-text-field
                    v-model="cond.value"
                    density="compact"
                    variant="outlined"
                    hide-details
                    placeholder="值"
                    :disabled="cond.op === '为空' || cond.op === '不为空'"
                    class="bento-value"
                  />
                  <v-btn
                    icon="mdi-close"
                    variant="text"
                    size="x-small"
                    color="grey"
                    @click="removeCondition(idx)"
                  />
                </div>
              </div>
            </div>

            <div class="cond-body-advanced" v-else>
              <div class="adv-scroll">
                <template v-for="(group, gIdx) in groups" :key="group.id">
                  <div class="bento-group-card">
                    <div class="group-card-accent"></div>
                    <div class="group-card-body">
                      <div class="group-head-row">
                        <div class="group-badge">G{{ gIdx + 1 }}</div>
                        <v-btn-toggle v-model="group.matchMode" mandatory density="compact" class="mode-toggle-pills-sm">
                          <v-btn value="所有" size="x-small" variant="flat" class="toggle-pill-sm">且</v-btn>
                          <v-btn value="任一" size="x-small" variant="flat" class="toggle-pill-sm">或</v-btn>
                        </v-btn-toggle>
                        <v-spacer />
                        <v-btn
                          icon="mdi-trash-can-outline"
                          variant="text"
                          size="x-small"
                          color="grey-darken-1"
                          :disabled="groups.length <= 1"
                          @click="removeGroup(gIdx)"
                        />
                      </div>

                      <div class="group-cond-list">
                        <div v-for="(cond, cIdx) in group.conditions" :key="cond.id" class="cond-row-bento">
                          <v-select
                            :items="bpStore.fieldNames"
                            v-model="cond.field"
                            density="compact"
                            variant="outlined"
                            hide-details
                            placeholder="字段"
                            class="bento-field"
                          />
                          <v-select
                            :items="ops"
                            v-model="cond.op"
                            density="compact"
                            variant="outlined"
                            hide-details
                            class="bento-op"
                          />
                          <v-text-field
                            v-model="cond.value"
                            density="compact"
                            variant="outlined"
                            hide-details
                            placeholder="值"
                            :disabled="cond.op === '为空' || cond.op === '不为空'"
                            class="bento-value"
                          />
                          <v-btn
                            icon="mdi-close"
                            variant="text"
                            size="x-small"
                            color="grey"
                            @click="removeGroupCondition(gIdx, cIdx)"
                          />
                        </div>
                        <v-chip
                          variant="text"
                          size="small"
                          color="#4f8cff"
                          class="add-chip"
                          @click="addGroupCondition(gIdx)"
                        >
                          <v-icon start size="14">mdi-plus</v-icon>条件
                        </v-chip>
                      </div>
                    </div>
                  </div>

                  <div v-if="gIdx < groups.length - 1" class="connector-row">
                    <v-btn-toggle v-model="groupConnectors[gIdx]" mandatory density="compact" class="mode-toggle-pills">
                      <v-btn value="所有" size="x-small" variant="flat" class="toggle-pill">且</v-btn>
                      <v-btn value="任一" size="x-small" variant="flat" class="toggle-pill">或</v-btn>
                    </v-btn-toggle>
                  </div>
                </template>

                <v-chip
                  variant="tonal"
                  size="small"
                  color="#4f8cff"
                  class="add-group-chip"
                  @click="addGroup"
                >
                  <v-icon start size="14">mdi-plus-box-outline</v-icon>添加条件组
                </v-chip>
              </div>
            </div>
          </div>

          <!-- 第二步：常规设置 -->
          <div v-else class="cond-step">
            <div class="cond-header">
              <div class="cond-steps">
                <span class="step-dot done">✓</span>
                <span class="step-name done" @click="step = 1">设置条件</span>
                <span class="step-sep">→</span>
                <span class="step-dot active">2</span>
                <span class="step-name active">{{ KIND_TITLES[kind] }}设置</span>
              </div>
            </div>
            <div class="settings-wrap">
              <MaterialSettings v-model:option="currentOption" :kind="kind" />
            </div>
          </div>
        </div>
      </v-card-text>

      <v-card-actions class="dialog-actions">
        <v-chip
          v-if="tab === 'conditional' && step === 1 && logicType === 'simple'"
          variant="text"
          size="small"
          color="#4f8cff"
          @click="addCondition"
        >
          <v-icon start size="14">mdi-plus</v-icon>条件
        </v-chip>
        <v-spacer />

        <v-btn variant="text" rounded="lg" @click="handleCancel">取消</v-btn>
        <v-btn
          v-if="tab === 'conditional' && step === 2"
          variant="text"
          rounded="lg"
          @click="step = 1"
        >上一步</v-btn>
        <v-btn
          v-if="tab === 'conditional' && step === 1"
          variant="flat"
          rounded="lg"
          color="#4f8cff"
          @click="goNext"
        >下一步</v-btn>
        <v-btn
          v-if="tab === 'single' || step === 2"
          variant="flat"
          rounded="lg"
          color="#4f8cff"
          @click="handleConfirm"
        >确定</v-btn>
      </v-card-actions>

      <v-snackbar v-model="snackbar" :timeout="2500" color="error" location="top" class="bento-snackbar">
        {{ snackbarMsg }}
      </v-snackbar>
    </v-card>
  </v-dialog>
</template>

<style scoped>
.loc-card {
  height: 70vh;
  max-height: 640px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.loc-card-header {
  flex-shrink: 0;
  padding: 12px 16px 0;
}

.loc-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.loc-title {
  font-size: 15px;
  font-weight: 700;
  color: #1e293b;
}

.loc-edit-badge {
  font-size: 10px;
  font-weight: 600;
  color: #4f8cff;
  background: rgba(79, 140, 255, 0.1);
  border-radius: 6px;
  padding: 2px 7px;
}

.loc-card-body {
  flex: 1;
  min-height: 0;
  padding: 8px 16px 0 !important;
  overflow: hidden;
  position: relative;
}

.loc-pane {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ========= tabs ========= */
.bento-tabs {
  --v-tabs-height: 40px;
}
.bento-tabs :deep(.v-tab) {
  font-size: 13px;
  font-weight: 600;
  text-transform: none;
  letter-spacing: 0;
  opacity: 0.45;
  transition: opacity 0.2s;
}
.bento-tabs :deep(.v-tab--selected) {
  opacity: 1;
}
.bento-tabs :deep(.v-tab__slider) {
  height: 2.5px;
  border-radius: 2px;
}

.dialog-actions {
  flex-shrink: 0;
  padding: 10px 16px;
  border-top: 1px solid rgba(0, 0, 0, 0.05);
}

/* ========= condition steps ========= */
.cond-step {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.settings-wrap {
  flex: 1;
  min-height: 0;
  display: flex;
}

.settings-wrap > :deep(*) {
  flex: 1;
  min-width: 0;
}

.cond-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 0 10px;
  flex-shrink: 0;
}

.cond-steps {
  display: flex;
  align-items: center;
  gap: 6px;
}

.step-dot {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #e2e8f0;
  color: #94a3b8;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.step-dot.active {
  background: #4f8cff;
  color: #fff;
}

.step-dot.done {
  background: rgba(79, 140, 255, 0.12);
  color: #4f8cff;
}

.step-name {
  font-size: 12.5px;
  font-weight: 600;
  color: #94a3b8;
}

.step-name.active {
  color: #1e293b;
}

.step-name.done {
  color: #4f8cff;
  cursor: pointer;
}

.step-sep {
  font-size: 12px;
  color: #cbd5e1;
  margin: 0 2px;
}

.adv-chip {
  cursor: pointer;
  font-weight: 500;
}

/* ========= simple mode ========= */
.cond-body-simple {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.cond-match-mode {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 0 10px;
}

.mode-label-text {
  font-size: 12.5px;
  color: #64748b;
  font-weight: 500;
  white-space: nowrap;
}

.cond-scroll {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow-y: auto;
  padding: 2px 4px 8px;
}

/* ========= advanced mode ========= */
.cond-body-advanced {
  flex: 1;
  overflow: hidden;
}

.adv-scroll {
  display: flex;
  flex-direction: column;
  gap: 0;
  overflow-y: auto;
  height: 100%;
  padding: 2px 4px 8px;
}

/* ========= group card ========= */
.bento-group-card {
  position: relative;
  border-radius: 12px;
  overflow: hidden;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04);
  flex-shrink: 0;
  margin: 6px 0;
}

.group-card-accent {
  position: absolute;
  left: 0;
  top: 0;
  width: 100%;
  height: 3px;
  background: linear-gradient(90deg, #4f8cff, #a78bfa);
}

.group-card-body {
  padding: 10px 12px 8px;
}

.group-head-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.group-badge {
  width: 26px;
  height: 26px;
  border-radius: 8px;
  background: linear-gradient(135deg, #4f8cff, #6c5ce7);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.group-cond-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.add-chip {
  cursor: pointer;
  align-self: flex-start;
}

/* ========= connector ========= */
.connector-row {
  display: flex;
  justify-content: center;
  padding: 4px 0;
  flex-shrink: 0;
}

.add-group-chip {
  cursor: pointer;
  align-self: flex-start;
  margin-top: 4px;
}

/* ========= condition row ========= */
.cond-row-bento {
  display: flex;
  align-items: center;
  gap: 6px;
}

.bento-field {
  flex: 0 0 150px;
  min-width: 110px;
}

.bento-op {
  flex: 0 0 105px;
}

.bento-value {
  flex: 1;
  min-width: 70px;
}

/* ========= toggle pills ========= */
.mode-toggle-pills {
  border-radius: 8px;
  overflow: hidden;
  background: rgba(0, 0, 0, 0.04);
  flex-shrink: 0;
}

.mode-toggle-pills-sm {
  border-radius: 6px;
  overflow: hidden;
  background: rgba(0, 0, 0, 0.04);
  flex-shrink: 0;
}

.toggle-pill {
  min-width: 36px !important;
  padding: 0 12px !important;
  height: 28px !important;
  font-weight: 600 !important;
  font-size: 12px !important;
  text-transform: none !important;
  letter-spacing: 0 !important;
  border-radius: 0 !important;
  color: #64748b !important;
  background: transparent !important;
  transition: all 0.15s;
}

.toggle-pill-sm {
  min-width: 32px !important;
  padding: 0 10px !important;
  height: 24px !important;
  font-weight: 600 !important;
  font-size: 11px !important;
  text-transform: none !important;
  letter-spacing: 0 !important;
  border-radius: 0 !important;
  color: #64748b !important;
  background: transparent !important;
  transition: all 0.15s;
}

:deep(.mode-toggle-pills .v-btn--active),
:deep(.mode-toggle-pills-sm .v-btn--active) {
  background: #4f8cff !important;
  color: #fff !important;
  box-shadow: 0 1px 3px rgba(79, 140, 255, 0.3);
}

/* ========= input refinements ========= */
:deep(.bento-field .v-field),
:deep(.bento-op .v-field),
:deep(.bento-value .v-field) {
  border-radius: 8px !important;
  box-shadow: none !important;
  border-color: rgba(0, 0, 0, 0.1) !important;
}

:deep(.bento-field .v-field:hover),
:deep(.bento-op .v-field:hover),
:deep(.bento-value .v-field:hover) {
  border-color: rgba(79, 140, 255, 0.35) !important;
}

:deep(.bento-field .v-field--focused),
:deep(.bento-op .v-field--focused),
:deep(.bento-value .v-field--focused) {
  border-color: #4f8cff !important;
  box-shadow: 0 0 0 2px rgba(79, 140, 255, 0.12) !important;
}

:deep(.bento-field .v-field__input),
:deep(.bento-op .v-field__input),
:deep(.bento-value .v-field__input) {
  font-size: 12.5px !important;
  padding: 6px 10px !important;
  min-height: auto !important;
}

/* ========= snackbar ========= */
.bento-snackbar :deep(.v-snackbar__content) {
  font-size: 13px;
  font-weight: 500;
}

/* ========= scrollbar ========= */
.cond-scroll::-webkit-scrollbar,
.adv-scroll::-webkit-scrollbar {
  width: 4px;
}

.cond-scroll::-webkit-scrollbar-thumb,
.adv-scroll::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.12);
  border-radius: 4px;
}
</style>
