<script setup lang="ts">

  import { defineProps,defineEmits,ref } from "vue";

  const props = defineProps({
    dialog: {
      type: Boolean,
      required: true
    }
  });

  const emits = defineEmits(['update:dialog']);

  const tab = ref(1);

  const activeNav = ref("signature");
  const navItems = [
  { title: "签字", value: "signature" },
  { title: "印章", value: "seal" },
  { title:"表格", value:"table" }
];
</script>

<template>
  <v-dialog v-model="props.dialog" max-width="500">
      <v-card style="height: 40vh;min-height: 40vh;max-height: 40vh; display: flex; flex-direction: column;">
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

        <v-card-text style="flex: 1; overflow-y: auto; ">
          <v-tabs-window v-model="tab">
            <v-tabs-window-item value="1">
              <v-row>
                <!-- 左侧导航栏 -->
                <v-col cols="3">
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

                <!-- 右侧内容展示 -->
                <v-col cols="9">
                  <div v-if="activeNav === 'signature'">
                    <h3>签字</h3>
                    <p>这里是“签字”的详细信息。</p>
                  </div>

                  <div v-else-if="activeNav === 'seal'">
                    <h3>印章</h3>
                    <p>这里是“印章”的详细信息。</p>
                  </div>

                  <div v-else-if="activeNav === 'table'">
                    <h3>表格</h3>
                    <p>这里是“表格”的详细信息。</p>
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

</style>


