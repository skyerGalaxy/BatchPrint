<script setup lang="ts">
import { ref, computed } from 'vue';
import { useBPStore } from '@/stores/bpstore';
import type { PropType } from 'vue';

const props = defineProps({
  selectedField: {
    type: String as PropType<string | null>,
    default: null
  }
});

const emits = defineEmits(['select_option']);

const bpStore = useBPStore();

const activeNav = ref('table');
const navItems = [
  { title: '表格', value: 'table' },
  { title: '签字', value: 'signature' },
  { title: '印章', value: 'seal' },
];

const selectedImageType = ref<'signature' | 'seal' | null>(null);
const selectedImageIndex = ref<number | null>(null);

function selectImage(type: 'signature' | 'seal', index: number) {
  selectedImageType.value = type;
  selectedImageIndex.value = index;
  const list = type === 'signature' ? bpStore.imageList_signature : bpStore.imageList_seal;
  emits('select_option', {
    type: 'image',
    src: list[index] ?? ''
  });
}

function selectField(fieldName: string) {
  emits('select_option', {
    type: 'field',
    fieldName
  });
}
</script>

<template>
  <v-row style="height: 100%; margin: 0;">
    <v-col cols="3" class="nav-col" style="padding-top: 12px; padding-bottom: 12px;" >
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
        <div style="max-height: 400px; overflow-y: auto;">
          <v-radio-group
            :model-value="selectedField"
            @update:model-value="(value) => selectField(value as string)"
          >
            <v-radio
              v-for="item in bpStore.fieldNames"
              :key="item"
              :label="item"
              :value="item"
            ></v-radio>
          </v-radio-group>
        </div>
      </div>

      <div v-else-if="activeNav === 'signature'">
        <div v-if="bpStore.imageList_signature.length === 0" class="text-center py-8">
            <p class="text-grey">暂无签名</p>
        </div>
        <div
          v-else
          style="max-height: 400px; overflow-y: auto;"
        >
          <v-row dense>
            <v-col v-for="(imgSrc, index) in bpStore.imageList_signature" :key="index" cols="12" sm="6" md="6">
                <v-img
                  :src="imgSrc"
                  aspect-ratio="1"
                  cover
                  class="rounded img-tile"
                  :class="{ 'is-selected': selectedImageType === 'signature' && selectedImageIndex === index }"
                  @click="selectImage('signature', index)"
                ></v-img>
            </v-col>
          </v-row>
        </div>
      </div>

      <div v-else-if="activeNav === 'seal'">
        <div v-if="bpStore.imageList_seal.length === 0" class="text-center py-8">
            <p class="text-grey">暂无印章</p>
        </div>
        <div
          v-else
          style="max-height: 400px; overflow-y: auto;"
        >
          <v-row dense>
            <v-col v-for="(imgSrc, index) in bpStore.imageList_seal" :key="index" cols="12" sm="6" md="6">
                <v-img
                  :src="imgSrc"
                  aspect-ratio="1"
                  cover
                  class="rounded img-tile"
                  :class="{ 'is-selected': selectedImageType === 'seal' && selectedImageIndex === index }"
                  @click="selectImage('seal', index)"
                ></v-img>
            </v-col>
          </v-row>
        </div>
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

.img-tile {
  cursor: pointer;
  opacity: 0.3;
  transition: opacity 0.15s ease-in-out;
}

.img-tile.is-selected {
  opacity: 1;
}
</style>