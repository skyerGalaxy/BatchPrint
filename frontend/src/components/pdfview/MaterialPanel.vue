<script setup lang="ts">
import { ref, computed } from 'vue';
import { defineProps, defineEmits } from 'vue';
import { useBPStore } from '@/stores/bpstore';
import type { PropType } from 'vue';

const props = defineProps({
  selectedField: {
    type: String as PropType<string | null>,
    default: null
  }
});

const emits = defineEmits(['update:selectedField']);

const bpStore = useBPStore();

const activeNav = ref('table');
const navItems = [
  { title: '表格', value: 'table' },
  { title: '签字', value: 'signature' },
  { title: '印章', value: 'seal' },
];

const localSelected = computed<string | null>({
  get: () => props.selectedField ?? (bpStore.fieldNames.length > 0 ? bpStore.fieldNames[0] : null),
  set: (v) => emits('update:selectedField', v)
});
</script>

<template>
  <v-row style="height: 100%; margin: 0;">
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

    <v-col cols="9" style="overflow: auto; max-height: 100%;">
      <div v-if="activeNav === 'table'">
        <v-radio-group v-model="localSelected" column>
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
</template>

<style scoped>
.nav-col {
  overflow: visible;
  display: flex;
  flex-direction: column;
  height: 100%;
}
</style>