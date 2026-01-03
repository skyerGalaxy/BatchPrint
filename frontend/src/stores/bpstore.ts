import { ref } from "vue";
import { defineStore } from "pinia";
import {Store} from '@tauri-apps/plugin-store'
import { image } from "@tauri-apps/api";

interface Pointer {
  pageIndex: number;  
  x: number;
  y: number;
  path: string;
  size: number;
}

interface RegularPointer extends Pointer {  
  type: "regular";
}

interface ConditionalPointer extends Pointer {
  type: "conditional";
  condition: string;
}

type PointerType = RegularPointer | ConditionalPointer;



export const useBPStore = defineStore("bpstore", () => {
  const fieldNames = ref<string[]>([]);
  const pointers = ref<PointerType[]>([]);
  const imagePath = ref<string>("");
  let settingsStore: Store | null = null;

  function addRegularPointer(pageIndex: number, x: number, y: number, path: string, size: number) {
    const newPointer: RegularPointer = {
      type: "regular",
      pageIndex,
      x,
      y,
      path,
      size,
    };
    pointers.value.push(newPointer);
  }

  function addConditionalPointer(condition: string, pageIndex: number, x: number, y: number, path: string, size: number) {
    const newPointer: ConditionalPointer = {
      type: "conditional",
      condition,
      pageIndex,
      x,
      y,
      path,
      size,
    };
    pointers.value.push(newPointer);
  }

  function removePointer(index: number) {
    if (index >= 0 && index < pointers.value.length) {
      pointers.value.splice(index, 1);
    }
  }

  async function initializeApp() {
    if (!settingsStore) {
      settingsStore = await Store.load('settings.json')
    }
    imagePath.value = await settingsStore.get('image_storage_path') || "";
    console.log("Image path loaded:", imagePath.value);
  }



  return { 
    fieldNames, 
    pointers, 
    imagePath,
    addRegularPointer, 
    addConditionalPointer, 
    removePointer,
    initializeApp,
  };
});