<script setup lang="ts">
import { ref } from "vue";
import { useBPStore } from "@/stores/bpstore";
import MaterialPanel from "./MaterialPanel.vue";

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
  }
});

const emits = defineEmits(['update:dialog']);

const tab = ref('1');
const step = ref(1);

const bpStore = useBPStore();

// 选项数据
type SelectedOption = 
  | { type: 'field'; fieldName: string; fontFamily?: string; size?: number }
  | { type: 'image'; src: string }
  | null;

const selectedOption = ref<SelectedOption>(null);


// 条件数据
type Condition = { id: number; field: string | null; op: string; value: string };
const ops = ['等于', '不等于', '包含', '不包含', '为空', '不为空'];
const matchMode = ref('所有');
const conditions = ref<Condition[]>([
  { id: Date.now(), field: null, op: '等于', value: '' }
]);
const iconId = ref<number>(1);

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

  const result = tab.value === '1'
    ? {id: iconId.value, pageIndex: props.pageIndex, pointer: props.pointer, mode: 'single', option: selectedOption.value, size: (selectedOption.value as any)?.size }
    : {id: iconId.value, pageIndex: props.pageIndex, pointer: props.pointer, mode: 'conditional', conditions: conditions.value, matchMode: matchMode.value, option: selectedOption.value, size: (selectedOption.value as any)?.size };

    console.log('最终结果:', result);
    if(!result.option) {
      alert('请至少选择一个选项');
      return;
    }

    if(result.mode === 'conditional'&& result.conditions!.length <1) {
      alert('请至少添加一个条件');
      return;
    }

    bpStore.iconList.push(result);
    if (bpStore.iconList.length = iconId.value) {
      iconId.value++;
    }

    console.log('当前图标列表:', bpStore.iconList);

    //重置所有状态
    tab.value = '1';
    step.value = 1;
    selectedOption.value = null;
    conditions.value = [{ id: Date.now(), field: null, op: '等于', value: '' }];
    matchMode.value = '所有';
    

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
              <material-panel
                @select_option="selectedOption = $event;console.log('选项更新:', $event)"
              />
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
                  <material-panel
                    @select_option="selectedOption = $event;console.log('选项更新:', $event)"
                  />
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