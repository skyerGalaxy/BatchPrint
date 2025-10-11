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
              Two
            </v-tabs-window-item>
          </v-tabs-window>
        </v-card-text>
        <v-card-actions>
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