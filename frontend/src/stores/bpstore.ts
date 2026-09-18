import { ref } from "vue";
import { defineStore } from "pinia";
import {Store} from '@tauri-apps/plugin-store'
import { mkdir } from "@tauri-apps/plugin-fs";
import { appLocalDataDir } from '@tauri-apps/api/path';
import type { StoreIcon, IconOption, MaterialKind } from '@/types/icon';

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

  const iconList = ref<StoreIcon[]>([]);
  const backendReady = ref(false);
  const backendLog = ref('');
  const fontsVersion = ref(0);

  const pdfSrc = ref<string>("");
  const excelSrc = ref<string>(""); 
  const pdfFile = ref<File | null>(null);
  const excelFile = ref<File | null>(null);
  const pdfScale = ref<number>(2);

  /** 各材料类型最近一次确认的样式（不含 fieldName/src/icon/text 等标识字段），新拖入的同类材料沿用 */
  const materialStyles = ref<Record<MaterialKind, Partial<IconOption>>>({
    table: {},
    signature: {},
    seal: {},
    icon: {},
    text: {},
  });
  let materialStyleStore: Store | null = null;

  async function loadMaterialStyles() {
    try {
      materialStyleStore = await Store.load('material_styles.json');
      const saved = await materialStyleStore.get<Partial<Record<MaterialKind, Partial<IconOption>>>>('styles');
      if (saved && typeof saved === 'object') {
        materialStyles.value = {
          table: saved.table ?? {},
          signature: saved.signature ?? {},
          seal: saved.seal ?? {},
          icon: saved.icon ?? {},
          text: saved.text ?? {},
        };
      }
    } catch (error) {
      console.error('加载材料样式失败:', error);
    }
  }

  async function saveMaterialStyle(kind: MaterialKind, style: Partial<IconOption>) {
    materialStyles.value = {
      ...materialStyles.value,
      [kind]: { ...materialStyles.value[kind], ...style },
    };
    try {
      if (!materialStyleStore) {
        materialStyleStore = await Store.load('material_styles.json');
      }
      await materialStyleStore.set('styles', materialStyles.value);
      await materialStyleStore.save();
    } catch (error) {
      console.error('保存材料样式失败:', error);
    }
  }

  /** 各类型的"身份字段"：这些字段跟随具体材料，不参与样式记忆 */
  const IDENTITY_KEYS: Record<MaterialKind, (keyof IconOption)[]> = {
    table: ['type', 'fieldName'],
    signature: ['type', 'imageKind', 'src'],
    seal: ['type', 'imageKind', 'src'],
    icon: ['type', 'icon'],
    text: ['type', 'text'],
  };

  /**
   * 新建/拖入材料时生成完整 option：
   * - 字段/签字/印章/图标：载荷仅提供身份字段，样式一律沿用同类型已记忆设置
   * - 文本：文本预设自带显式样式，预设样式优先于记忆样式
   */
  function instantiateOption(kind: MaterialKind, option: IconOption): IconOption {
    if (kind === 'text') {
      return { ...materialStyles.value.text, ...option };
    }
    // 该类型从未保存过样式时，直接使用载荷/默认值
    if (Object.keys(materialStyles.value[kind]).length === 0) {
      return { ...option };
    }
    const identity: Record<string, unknown> = {};
    for (const key of IDENTITY_KEYS[kind]) {
      const v = option[key];
      if (v !== undefined && v !== null) identity[key] = v;
    }
    return { ...identity, ...materialStyles.value[kind] } as IconOption;
  }


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
    backendReady,
    backendLog,
    fontsVersion,
    excelContent,
    pdfSrc,
    excelSrc,
    pdfFile,
    excelFile,
    pdfScale,
    materialStyles,
    addRegularPointer,
    addConditionalPointer,
    removePointer,
    initializeApp,
    loadMaterialStyles,
    saveMaterialStyle,
    instantiateOption,
  };
});