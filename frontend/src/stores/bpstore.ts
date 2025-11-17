import { defineStore } from "pinia";


export const useBPStore = defineStore("bpstore", () => {
  const fieldNames = ref<string[]>([]);
  const pointer = ref<{ pageIndex: number; x: number; y: number } | null>(null);

  function setPointer(pageIndex:number, x: number, y: number) {
    pointer.value = { pageIndex, x, y };
  }

  return { fieldNames, pointer, setPointer };
});