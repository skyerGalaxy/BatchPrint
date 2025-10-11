import { defineStore } from "pinia";


export const useBPStore = defineStore("bpstore", () => {
  const fieldNames = ref<string[]>([]);

  return { fieldNames };
});