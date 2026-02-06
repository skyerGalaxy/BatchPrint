<script setup lang="ts">
import { ref } from "vue";
import { useBPStore } from "@/stores/bpstore";
import MaterialPanel from "./MaterialPanel.vue";

const props = defineProps({
  dialog: {
    type: Boolean,
    required: true
  }
});

const emits = defineEmits(['update:dialog']);

const tab = ref('1');
const step = ref(1);

const bpStore = useBPStore();

// 选项数据
type SelectedOption = 
  | { type: 'field'; fieldName: string; fontSize?: number; fontFamily?: string }
  | { type: 'image'; src: string }
  | null;

const selectedOption = ref<SelectedOption>(null);

// 字体配置（仅用于字段类型）
const fontSize = ref(12);
const fontFamily = ref('微软雅黑');
const fontFamilies = ['微软雅黑', '宋体', '黑体', 'Arial', 'Times New Roman'];

// 条件数据
type Condition = { id: number; field: string | null; op: string; value: string };
const ops = ['等于', '不等于', '包含', '不包含', '为空', '不为空'];
const matchMode = ref('所有');
const conditions = ref<Condition[]>([
  { id: Date.now(), field: null, op: '等于', value: '' }
]);

function addCondition() {
  conditions.value.push({
    id: Date.now() + Math.floor(Math.random() * 1000),
    field: null,
    op: '等于',
    value: ''
  });
}

function removeCondition(index: number) {
  conditions.value.splice(index, 1);
}

function handleConfirm() {
  let finalOption = selectedOption.value;
  
  // 如果选择的是字段，添加字体配置
  if (finalOption && finalOption.type === 'field') {
    finalOption = {
      ...finalOption,
      fontSize: fontSize.value,
      fontFamily: fontFamily.value
    };
  }
  
  const result = tab.value === '1'
    ? { mode: 'single', option: finalOption }
    : { mode: 'conditional', conditions: conditions.value, matchMode: matchMode.value, option: finalOption };
  console.log('确定提交:', result);
  emits('update:dialog', false);
}

function handleCancel() {
  emits('update:dialog', false);
}
</script>

<template>
  <v-dialog v-model="props.dialog" max-width="650">
      <!-- 固定高度，保持列布局 -->
      <v-card style="height: 40vh; min-height: 40vh; max-height: 40vh; display: flex; flex-direction: column;">
        <v-card-item>
          <v-tabs
            v-model="tab"
            fixed-tabs
            grow
            color="primary"
            bg-color="blue-lighten-5"
          >
            <v-tab value="1" active-color="#2a72c5">单一选项</v-tab>
            <v-tab value="2" active-color="#2a72c5">条件选项</v-tab>
          </v-tabs>
        </v-card-item>

        <!-- 主内容区域 -->
        <v-card-text style="flex: 1; overflow: hidden; padding: 0 12px;">
          <v-tabs-window v-model="tab" style="height: 100%;">
            <!-- Tab 1: 单一选项 - 直接显示选项选择 -->
            <v-tabs-window-item value="1" style="height: 100%;">
              <v-row style="height: 100%; margin: 0;">
                <v-col :cols="selectedOption?.type === 'field' ? 8 : 12" style="height: 100%; padding-right: 8px;">
                  <material-panel
                    @select_option="selectedOption = $event"
                  />
                </v-col>
                <v-col v-if="selectedOption?.type === 'field'" cols="4" style="height: 100%; border-left: 1px solid #e0e0e0; padding-left: 12px; overflow-y: auto;">
                  <div style="padding-top: 12px;">
                    <h4 style="margin-bottom: 16px; font-size: 14px;">字体设置</h4>
                    <v-select
                      v-model="fontFamily"
                      :items="fontFamilies"
                      label="字体"
                      density="compact"
                      style="margin-bottom: 12px;"
                    ></v-select>
                    <v-text-field
                      v-model.number="fontSize"
                      label="字号"
                      type="number"
                      density="compact"
                      :min="8"
                      :max="72"
                    ></v-text-field>
                  </div>
                </v-col>
              </v-row>
            </v-tabs-window-item>

            <!-- Tab 2: 条件选项 - 两步流程 -->
            <v-tabs-window-item value="2" style="height: 100%;">
              <v-window v-model="step" style="height: 100%;">
                <v-window-item :value="1" style="height: 100%;">
                  <div style="display:flex; align-items:center; margin-bottom:8px; height:32px; min-height:32px; padding:4px 0;">
                    <div style="font-size:13px; line-height:32px;">查找条件</div>
                    <v-spacer></v-spacer>
                    <div style="display:flex; align-items:center; gap:8px;">
                      <div style="font-size:13px; line-height:32px;">符合以下</div>
                      <v-select
                        :items="['所有','任一']"
                        v-model="matchMode"
                        dense
                        outlined
                        height="10"
                        hide-details
                      />
                    </div>
                  </div>

                  <!-- 条件列表 -->
                  <div style="display:flex; flex-direction:column; gap:8px; max-height: calc(40vh - 140px); overflow:auto; padding-right:8px;">
                    <div
                      v-for="(cond, idx) in conditions"
                      :key="cond.id"
                      style="display:flex; align-items:center; gap:8px;"
                    >
                      <v-select
                        :items="bpStore.fieldNames.filter(f => !conditions.some(c => c.field === f))"
                        v-model="cond.field"
                        dense
                        style="width:200px"
                        :placeholder="'请选择字段'"
                      />
                      <v-select
                        :items="ops"
                        v-model="cond.op"
                        dense
                        style="width:120px"
                      />
                      <v-text-field
                        v-model="cond.value"
                        dense
                        placeholder="值"
                        :disabled="cond.op === '为空' || cond.op === '不为空'"
                        style="flex:1; min-width:120px;"
                      />
                      <v-btn icon variant="flat" color="error" @click="removeCondition(idx)" :title="'删除条件'">
                        <v-icon>mdi-close</v-icon>
                      </v-btn>
                    </div>
                  </div>
                </v-window-item>
                <!-- Step 2: 选项选择 -->
                <v-window-item :value="2" style="height: 100%;">
                  <v-row style="height: 100%; margin: 0;">
                    <v-col :cols="selectedOption?.type === 'field' ? 8 : 12" style="height: 100%; padding-right: 8px;">
                      <material-panel
                        @select_option="selectedOption = $event"
                      />
                    </v-col>
                    <v-col v-if="selectedOption?.type === 'field'" cols="4" style="height: 100%; border-left: 1px solid #e0e0e0; padding-left: 12px; overflow-y: auto;">
                      <div style="padding-top: 12px;">
                        <h4 style="margin-bottom: 16px; font-size: 14px;">字体设置</h4>
                        <v-select
                          v-model="fontFamily"
                          :items="fontFamilies"
                          label="字体"
                          density="compact"
                          style="margin-bottom: 12px;"
                        ></v-select>
                        <v-text-field
                          v-model.number="fontSize"
                          label="字号"
                          type="number"
                          density="compact"
                          :min="8"
                          :max="72"
                        ></v-text-field>
                      </div>
                    </v-col>
                  </v-row>
                </v-window-item>
              </v-window>
            </v-tabs-window-item>
            
          </v-tabs-window>
        </v-card-text>

        <!-- 单一选项底部按钮 -->
        <v-card-actions v-if="tab=='1'">
          <v-spacer></v-spacer>
          <v-btn text @click="handleCancel">取消</v-btn>
          <v-btn color="primary" @click="handleConfirm">确定</v-btn>
        </v-card-actions>

        <!-- 条件选项第一步：编辑条件 -->
        <v-card-actions v-if="tab=='2'&&step==1">
          <v-btn text small color="primary" @click="addCondition">
            <v-icon left>mdi-plus</v-icon>添加条件
          </v-btn>
          <v-spacer></v-spacer>
          <v-btn color="primary" @click="step++">下一步</v-btn>
        </v-card-actions>

        <!-- 条件选项第二步：选择选项 -->
        <v-card-actions v-if="tab=='2'&&step==2">
          <v-btn text @click="step--">上一步</v-btn>
          <v-spacer></v-spacer>
          <v-btn text @click="handleCancel">取消</v-btn>
          <v-btn color="primary" @click="handleConfirm">确定</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
</template>

<style scoped >
/* 左侧保持固定显示（可按需微调） */
.nav-col {
  /* 确保左侧不出现滚动条并垂直铺满 */
  overflow: visible;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.v-text-field--box .v-input__slot,
.v-text-field--outline .v-input__slot {
  min-height: auto!important;
  display: flex!important;
  align-items: center!important;
}

</style>
// ...existing code...