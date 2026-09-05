<script setup lang="ts">
import { ref, watch } from "vue";
import { useBPStore } from "@/stores/bpstore";
import MaterialPanel from "./MaterialPanel.vue";
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
  initialPanel: {
    type: String,
    default: 'table'
  },
  initialOption: {
    type: Object as () => IconOption | null,
    default: null
  },
  initialField: {
    type: String,
    default: null
  }
});

const emits = defineEmits(['update:dialog']);

const tab = ref('1');
const step = ref(1);

const bpStore = useBPStore();

const selectedOption = ref<IconOption | null>(props.initialOption);

watch(() => props.initialOption, (option) => {
  selectedOption.value = option;
});

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

const iconId = ref<number>(1);

let nextId = Date.now();

function genId(): number {
  return ++nextId;
}

const snackbar = ref(false);
const snackbarMsg = ref('');

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
  conditions.value.push({
    id: genId(),
    field: null,
    op: '等于',
    value: ''
  });
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
  groups.value[groupIndex].conditions.push({
    id: genId(),
    field: null,
    op: '等于',
    value: ''
  });
}

function removeGroupCondition(groupIndex: number, condIndex: number) {
  groups.value[groupIndex].conditions.splice(condIndex, 1);
}

function goNext() {
  if (logicType.value === 'simple' && !validateAllSimple()) return;
  if (logicType.value === 'advanced' && !validateAllAdvanced()) return;
  step.value++;
}

function fieldUsedInSimple(): string[] {
  return conditions.value
    .filter(c => c.field !== null)
    .map(c => c.field!);
}

function fieldUsedInGroup(groupIndex: number): string[] {
  return groups.value[groupIndex].conditions
    .filter(c => c.field !== null)
    .map(c => c.field!);
}

function fieldsForSimple(): string[] {
  const used = fieldUsedInSimple();
  return bpStore.fieldNames.filter(f => !used.includes(f));
}

function fieldsForGroup(groupIndex: number): string[] {
  const used = fieldUsedInGroup(groupIndex);
  return bpStore.fieldNames.filter(f => !used.includes(f));
}

function handleConfirm() {
  let result: StoreIcon;

  if (tab.value === '1') {
    result = {
      id: iconId.value,
      pageIndex: props.pageIndex,
      pointer: props.pointer,
      mode: 'single',
      option: selectedOption.value!,
      size: (selectedOption.value as any)?.size,
      scale: bpStore.pdfScale
    };
  } else {
    result = {
      id: iconId.value,
      pageIndex: props.pageIndex,
      pointer: props.pointer,
      mode: 'conditional',
      option: selectedOption.value!,
      size: (selectedOption.value as any)?.size,
      scale: bpStore.pdfScale,
      logicType: logicType.value,
    };

    if (logicType.value === 'simple') {
      result.conditions = conditions.value;
      result.matchMode = matchMode.value;
    } else {
      result.groups = groups.value;
      result.groupConnectors = groupConnectors.value;
    }
  }

  if (!result.option) {
    snackbarMsg.value = '请至少选择一个选项';
    snackbar.value = true;
    return;
  }

  if (result.mode === 'conditional') {
    if (logicType.value === 'simple' && result.conditions) {
      const valid = result.conditions.filter(c => isConditionValid(c));
      if (valid.length < 1) {
        snackbarMsg.value = '请至少添加一个条件';
        snackbar.value = true;
        return;
      }
    }
    if (logicType.value === 'advanced' && result.groups) {
      const hasAnyCondition = result.groups.some(g =>
        g.conditions.filter(c => isConditionValid(c)).length > 0
      );
      if (!hasAnyCondition) {
        snackbarMsg.value = '请至少添加一个条件';
        snackbar.value = true;
        return;
      }
    }
  }

  bpStore.iconList.push(result);
  if (bpStore.iconList.length === iconId.value) {
    iconId.value++;
  }

  resetDialog();

  emits('update:dialog', false);
}

function resetDialog() {
  tab.value = '1';
  step.value = 1;
  selectedOption.value = null;
  logicType.value = 'simple';
  matchMode.value = '所有';
  nextId = Date.now();
  conditions.value = [{ id: genId(), field: null, op: '等于', value: '' }];
  groups.value = [
    { id: genId(), matchMode: '所有', conditions: [{ id: genId(), field: null, op: '等于', value: '' }] }
  ];
  groupConnectors.value = [];
}

function handleCancel() {
  emits('update:dialog', false);
}
</script>

<template>
  <v-dialog v-model="props.dialog" max-width="560">
    <v-card class="loc-card" rounded="xl" elevation="8">
      <v-card-item class="loc-card-header">
        <v-tabs
          v-model="tab"
          fixed-tabs
          grow
          color="#4f8cff"
          slider-color="#4f8cff"
          class="bento-tabs"
        >
          <v-tab value="1">单一选项</v-tab>
          <v-tab value="2">条件选项</v-tab>
        </v-tabs>
      </v-card-item>

      <v-card-text class="loc-card-body">
        <v-tabs-window v-model="tab" class="loc-tabs-window">
          <v-tabs-window-item value="1">
            <material-panel
              :active-nav="props.initialPanel"
              :initial-field="props.initialField"
              :initial-option="props.initialOption"
              @select_option="selectedOption = $event"
            />
          </v-tabs-window-item>

          <v-tabs-window-item value="2">
            <v-window v-model="step" class="loc-step-window">
              <v-window-item :value="1" class="loc-step-panel">
                <div class="cond-header">
                  <div class="cond-header-left">
                    <v-icon color="#4f8cff" size="18" class="cond-header-icon">mdi-filter-variant</v-icon>
                    <span class="cond-header-title">查找条件</span>
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
                        :items="fieldsForSimple()"
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
                                :items="fieldsForGroup(gIdx)"
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
              </v-window-item>
              <v-window-item :value="2">
                <material-panel
                  :active-nav="props.initialPanel"
                  :initial-field="props.initialField"
                  :initial-option="props.initialOption"
                  @select_option="selectedOption = $event"
                />
              </v-window-item>
            </v-window>
          </v-tabs-window-item>
        </v-tabs-window>
      </v-card-text>

      <v-card-actions v-if="tab=='1'" class="dialog-actions">
        <v-spacer></v-spacer>
        <v-btn variant="text" rounded="lg" @click="handleCancel">取消</v-btn>
        <v-btn variant="flat" rounded="lg" color="#4f8cff" :disabled="!selectedOption" @click="handleConfirm">确定</v-btn>
      </v-card-actions>

      <v-card-actions v-if="tab=='2'&&step==1" class="dialog-actions">
        <v-chip variant="text" size="small" color="#4f8cff" v-if="logicType==='simple'" @click="addCondition">
          <v-icon start size="14">mdi-plus</v-icon>条件
        </v-chip>
        <v-spacer></v-spacer>
        <v-btn variant="text" rounded="lg" @click="handleCancel">取消</v-btn>
        <v-btn variant="flat" rounded="lg" color="#4f8cff" @click="goNext">下一步</v-btn>
      </v-card-actions>

      <v-card-actions v-if="tab=='2'&&step==2" class="dialog-actions">
        <v-btn variant="text" rounded="lg" @click="step--">上一步</v-btn>
        <v-spacer></v-spacer>
        <v-btn variant="text" rounded="lg" @click="handleCancel">取消</v-btn>
        <v-btn variant="flat" rounded="lg" color="#4f8cff" :disabled="!selectedOption" @click="handleConfirm">确定</v-btn>
      </v-card-actions>

      <v-snackbar v-model="snackbar" :timeout="2500" color="error" location="top" class="bento-snackbar">
        {{ snackbarMsg }}
      </v-snackbar>
    </v-card>
  </v-dialog>
</template>

<style scoped>
.loc-card {
  height: 40vh;
  min-height: 40vh;
  max-height: 40vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.loc-card-header {
  flex-shrink: 0;
  padding: 0 16px;
}

.loc-card-body {
  flex: 1;
  min-height: 0;
  padding: 0 16px !important;
  overflow: hidden;
  position: relative;
}

/* ========= tabs ========= */
.bento-tabs {
  --v-tabs-height: 44px;
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

/* ========= layout ========= */
.loc-tabs-window {
  position: absolute;
  inset: 0;
  height: 100% !important;
}

.loc-step-window {
  height: 100% !important;
}

.loc-step-panel {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 0 8px;
}

.dialog-actions {
  padding: 10px 16px;
  border-top: 1px solid rgba(0,0,0,0.05);
}

:deep(.v-window__container) {
  height: 100% !important;
}

:deep(.v-window-item) {
  height: 100%;
  overflow: hidden;
}

/* ========= cond header ========= */
.cond-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 0 10px;
}

.cond-header-left {
  display: flex;
  align-items: center;
  gap: 6px;
}

.cond-header-icon {
  flex-shrink: 0;
}

.cond-header-title {
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
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
  box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
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
  background: rgba(0,0,0,0.04);
  flex-shrink: 0;
}

.mode-toggle-pills-sm {
  border-radius: 6px;
  overflow: hidden;
  background: rgba(0,0,0,0.04);
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
  box-shadow: 0 1px 3px rgba(79,140,255,0.3);
}

/* ========= input refinements ========= */
:deep(.bento-field .v-field),
:deep(.bento-op .v-field),
:deep(.bento-value .v-field) {
  border-radius: 8px !important;
  box-shadow: none !important;
  border-color: rgba(0,0,0,0.1) !important;
}

:deep(.bento-field .v-field:hover),
:deep(.bento-op .v-field:hover),
:deep(.bento-value .v-field:hover) {
  border-color: rgba(79,140,255,0.35) !important;
}

:deep(.bento-field .v-field--focused),
:deep(.bento-op .v-field--focused),
:deep(.bento-value .v-field--focused) {
  border-color: #4f8cff !important;
  box-shadow: 0 0 0 2px rgba(79,140,255,0.12) !important;
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
  background: rgba(0,0,0,0.12);
  border-radius: 4px;
}
</style>
