import { defineStore } from "pinia";


export const useBPStore = defineStore("bpstore", () => {
  const pdfPath = ref<string | null>(null);
  const pdfName = ref<string | null>(null);


  return { pdfPath, pdfName };
});