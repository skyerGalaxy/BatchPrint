// ...existing code...
<script setup lang="ts">

  import { defineProps,defineEmits,ref } from "vue";
  import { useBPStore } from "@/stores/bpstore";

  const props = defineProps({
    dialog: {
      type: Boolean,
      required: true
    }
  });

  const emits = defineEmits(['update:dialog']);

  const tab = ref(1);

  const activeNav = ref("table");
  const navItems = [
  { title:"表格", value:"table" },
  { title: "签字", value: "signature" },
  { title: "印章", value: "seal" },
];

  const bpStore = useBPStore();

  const selectedField = ref<string | null>(bpStore.fieldNames.length > 0 ? bpStore.fieldNames[0] : null);


  const step = ref(1);

  // ---------- 新增：条件行状态与方法 ----------
type Condition = { id: number; field: string | null; op: string; value: string };

const ops = ['等于','不等于','包含','不包含','为空','不为空'];

const conditions = ref<Condition[]>([
  { id: Date.now(), field: bpStore.fieldNames[0] ?? null, op: '等于', value: '' }
]);

function addCondition() {
  conditions.value.push({
    id: Date.now() + Math.floor(Math.random() * 1000),
    field: bpStore.fieldNames[0] ?? null,
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
              <!-- 横向布局：左侧固定，右侧可滚动 -->
              <v-row style="height: 100%; margin: 0;">
                <!-- 左侧导航栏（固定，不随右侧内容滚动） -->
                <v-col cols="3" class="nav-col" style="padding-top: 12px; padding-bottom: 12px;">
                  <v-list density="compact" nav>
                    <v-list-item
                      v-for="item in navItems"
                      :key="item.value"
                      :title="item.title"
                      :active="activeNav === item.value"
                      @click="activeNav = item.value"
                    ></v-list-item>
                  </v-list>
                </v-col>

                <!-- 右侧内容展示（超出时内部滚动） -->
                <v-col cols="9" style="overflow: auto; max-height: 100%;">
                    <div v-if="activeNav === 'table'">
                    <v-radio-group v-model="selectedField" column>
                      <v-virtual-scroll
                      :items="bpStore.fieldNames"
                      :height="300"
                      item-height="40"
                      >
                      <template #default="{ item }">
                        <v-radio
                        :key="item"
                        :label="item"
                        :value="item"
                        ></v-radio>
                      </template>
                      </v-virtual-scroll>
                    </v-radio-group>
                    </div>

                    <div v-else-if="activeNav === 'signature'">
                    <h3>签字</h3>
                    <v-virtual-scroll
                      :items="Array.from({length: 20}, (_, i) => i + 1)"
                      :height="300"
                      item-height="24"
                    >
                      <template #default="{ item }">
                      <p :key="item">示例占位内容行 {{ item }}</p>
                      </template>
                    </v-virtual-scroll>
                    </div>

                    <div v-else-if="activeNav === 'seal'">
                    <h3>印章</h3>
                    <v-virtual-scroll
                      :items="Array.from({length: 2}, (_, i) => i + 1)"
                      :height="300"
                      item-height="24"
                    >
                      <template #default="{ item }">
                      <p :key="item">示例占位内容行 {{ item }}</p>
                      </template>
                    </v-virtual-scroll>
                    </div>
                </v-col>
              </v-row>
            </v-tabs-window-item>

            <v-tabs-window-item value="2">
              <v-window v-model="step">
                <v-window-item :value="1">
                  <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
                    <div style="font-size:14px;">查找条件</div>
                    <v-spacer></v-spacer>
                    <div style="display:flex; align-items:center; gap:8px;">
                      <div style="font-size:13px;">符合以下</div>
                      <v-select
                        :items="['所有','任一']"
                        model-value="所有"
                        dense
                        style="width:100px"
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
                        :items="bpStore.fieldNames"
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
                        style="flex:1; min-width:120px;"
                      />
                      <v-btn icon variant="flat" color="error" @click="removeCondition(idx)" :title="'删除条件'">
                        <v-icon>mdi-close</v-icon>
                      </v-btn>
                    </div>

                    <!-- 添加条件 -->
                    <div>
                      <v-btn text small color="primary" @click="addCondition">
                        <v-icon left>mdi-plus</v-icon> 添加条件
                      </v-btn>
                    </div>
                  </div>
                </v-window-item>
                <v-window-item :value="2">
                  <div>条件选项 - 步骤 2 内容</div>
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
            <v-spacer></v-spacer>
            <v-btn
              color="primary"
              variant="flat"
              @click="step++"
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

</style>
// ...existing code...