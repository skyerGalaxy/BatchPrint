import { ref, shallowRef } from "vue";
import { defineStore } from "pinia";
import {Store} from '@tauri-apps/plugin-store'
import { mkdir } from "@tauri-apps/plugin-fs";
import { appLocalDataDir } from '@tauri-apps/api/path';
import type { StoreIcon, IconOption, MaterialKind, LoopBlock, DocxStructureItem } from '@/types/icon';
import type { WorkspaceSnapshot } from '@/types/workspace';

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

  /** 模板类型：PDF / DOCX */
  const templateType = ref<'pdf' | 'docx'>('pdf');
  const docxFile = ref<File | null>(null);
  const docxStructure = ref<DocxStructureItem[]>([]);
  const loopBlocks = ref<LoopBlock[]>([]);

  /**
   * 模板 / 表格的原始文件绝对路径，作为工作进度的唯一持久化引用。
   * pdfFile / docxFile / excelFile 是由这些路径派生出的临时对象，仅用于预览与上传。
   */
  const pdfPath = ref<string>('');
  const docxPath = ref<string>('');
  const excelPath = ref<string>('');

  /** 各材料类型最近一次确认的样式（不含 fieldName/src/icon/text 等标识字段），新拖入的同类材料沿用 */
  const materialStyles = ref<Record<MaterialKind, Partial<IconOption>>>({
    table: {},
    signature: {},
    seal: {},
    icon: {},
    text: {},
  });
  let materialStyleStore: Store | null = null;

  /**
   * 历史记录页请求恢复的现场快照。
   * 用 shallowRef 避免把快照里大量嵌套对象/图标数据做成响应式代理。
   * 由 /batch-print 页面在激活时消费（consumeRestore），恢复环境后再写入各业务字段。
   */
  const pendingRestore = shallowRef<WorkspaceSnapshot | null>(null);
  /** 工作进度列表版本号：保存 / 删除后自增，历史记录页据此刷新 */
  const workspacesVersion = ref(0);

  /**
   * 当前正在编辑的项目。
   * 再次保存时沿用这个 ID，在同一项目里追加版本，而不是每保存一次就新建一个项目。
   * 为空表示当前内容尚未保存成项目（下次保存会创建新项目）。
   */
  const currentProjectId = ref('');
  const currentProjectTitle = ref('');
  /** 当前项目的版本数量（含当前版本）；<=1 表示还没有历史版本 */
  const currentProjectRevisionCount = ref(0);

  function setCurrentProject(id: string, title: string, revisionCount = 0) {
    currentProjectId.value = id;
    currentProjectTitle.value = title;
    currentProjectRevisionCount.value = revisionCount;
  }

  function clearCurrentProject() {
    currentProjectId.value = '';
    currentProjectTitle.value = '';
    currentProjectRevisionCount.value = 0;
  }

  function requestRestore(snapshot: WorkspaceSnapshot) {
    pendingRestore.value = snapshot;
  }

  function consumeRestore(): WorkspaceSnapshot | null {
    const snapshot = pendingRestore.value;
    pendingRestore.value = null;
    return snapshot;
  }

  function bumpWorkspaces() {
    workspacesVersion.value++;
  }

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
    templateType,
    docxFile,
    docxStructure,
    loopBlocks,
    pdfPath,
    docxPath,
    excelPath,
    materialStyles,
    pendingRestore,
    workspacesVersion,
    currentProjectId,
    currentProjectTitle,
    currentProjectRevisionCount,
    setCurrentProject,
    clearCurrentProject,
    addRegularPointer,
    addConditionalPointer,
    removePointer,
    initializeApp,
    loadMaterialStyles,
    saveMaterialStyle,
    instantiateOption,
    requestRestore,
    consumeRestore,
    bumpWorkspaces,
  };
});