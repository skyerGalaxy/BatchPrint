import { ref } from "vue";
import { defineStore } from "pinia";
import {Store} from '@tauri-apps/plugin-store'
import { mkdir } from "@tauri-apps/plugin-fs";
import { appLocalDataDir } from '@tauri-apps/api/path';

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
  const dataPath = ref<string>("");
  const imageList_signature = ref<string[]>([]);
  const imageList_seal = ref<string[]>([]);

  const excelContent = ref<any[][]>([]); 

  const iconList = ref<{}[]>([]);

  const pdfSrc = ref<string>("");
  const excelSrc = ref<string>(""); 
  const pdfFile = ref<File | null>(null);
  const excelFile = ref<File | null>(null);
  const pdfScale = ref<number>(2);


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
    try {
      const store = await Store.load('settings.json');
      
      let path = await store.get('data_storage_path') as string | null;

      if (!path) {
        path = await appLocalDataDir();
        await store.set('data_storage_path', path);
        
        await Promise.all([
          mkdir(`${path}/sealImg`, { recursive: true }),
          mkdir(`${path}/signImg`, { recursive: true }),
          mkdir(`${path}/generatePdf`, { recursive: true }),
        ]);
      }
      
      dataPath.value = path;
    } catch (error) {
      console.error('Failed to initialize app:', error);
    }
  }



  return { 
    fieldNames, 
    pointers, 
    dataPath,
    imageList_signature,
    imageList_seal,
    iconList,
    excelContent,
    pdfSrc,
    excelSrc,
    pdfFile,
    excelFile,
    pdfScale,
    addRegularPointer, 
    addConditionalPointer, 
    removePointer,
    initializeApp,
  };
});