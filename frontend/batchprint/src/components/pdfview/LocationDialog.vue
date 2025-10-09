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

  const activeNav = ref("overview");
  const navItems = [
  { title: "概览", value: "overview" },
  { title: "设置", value: "settings" },
  { title: "帮助", value: "help" },
];
</script>

<template>
  <v-dialog v-model="props.dialog" max-width="500">
      <v-card style="height: 70vh;display: flex; flex-direction: column;">
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
                  <div v-if="activeNav === 'overview'">
                    <h3>概览内容</h3>
                    <p>这里是“概览”的详细信息。</p>
                  </div>

                  <div v-else-if="activeNav === 'settings'">
                    <h3>设置内容</h3>
                    <p>这里是“设置”的具体内容。</p>
                  </div>

                  <div v-else-if="activeNav === 'help'">
                    <h3>帮助内容</h3>
                    <p>这里是“帮助”的说明。</p>
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


