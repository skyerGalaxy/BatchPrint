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

  const tab = ref(1);

  const bpStore = useBPStore();

  const selectedField = ref<string | null>(bpStore.fieldNames.length > 0 ? bpStore.fieldNames[0] : null);


  const step = ref(1);

  // ---------- 新增：条件行状态与方法 ----------

const matchMode = ref('所有'); // '所有' 或 '任一'

type Condition = { id: number; field: string | null; op: string; value: string };

const ops = ['等于','不等于','包含','不包含','为空','不为空'];

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
  nextTick(() => {});
}

function removeCondition(index: number) {
  conditions.value.splice(index, 1);
}
</script>

<template>
  <v-dialog v-model="props.dialog" max-width="500">
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

        <!-- 将外层隐藏滚动，内部左右两栏分别控制滚动 -->
        <v-card-text style="flex: 1; overflow: hidden; padding: 0 12px;">
          <v-tabs-window v-model="tab" style="height: 100%;">
            <v-tabs-window-item value="1" style="height: 100%;">
              <material-panel v-model:selected-field="selectedField"/>
            </v-tabs-window-item>

            <v-tabs-window-item value="2">
              <v-window v-model="step">
                <v-window-item :value="1">
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
                <v-window-item :value="2">
                  <material-panel v-model:selected-field="selectedField"/>
                </v-window-item>
              </v-window>
            </v-tabs-window-item>
            
          </v-tabs-window>
        </v-card-text>

        <v-card-actions v-if="tab==1">
          <v-spacer></v-spacer>
          <v-btn color="primary" text @click="emits('update:dialog',false)">Disagree</v-btn>
          <v-btn color="primary" text @click="emits('update:dialog',false)">Agree</v-btn>
        </v-card-actions>
        <v-card-actions v-if="tab==2&&step==1">
          <!-- 添加条件 -->
            <v-btn text small color="primary" @click="addCondition">
              <v-icon left>mdi-plus</v-icon> 添加条件
            </v-btn>
            <v-spacer></v-spacer>
            <v-btn
              color="primary"
              variant="flat"
              @click="step++; console.log(conditions)"
            >
              下一步
            </v-btn>
        </v-card-actions>
        <v-card-actions v-if="tab==2&&step==2">
            <v-btn
              variant="flat"
              @click="step--"
            >
              上一步
            </v-btn>
            <v-spacer></v-spacer>
            <v-btn color="primary" text @click="emits('update:dialog',false)">Disagree</v-btn>
            <v-btn color="primary" text @click="emits('update:dialog',false)">Agree</v-btn>
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