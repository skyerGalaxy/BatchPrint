import { ref } from "vue";
import { defineStore } from "pinia";
import { invoke } from '@tauri-apps/api/core';

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

interface AppConfig {
  image_storage_path: string;
}

export const useBPStore = defineStore("bpstore", () => {
  const fieldNames = ref<string[]>([]);
  const pointers = ref<PointerType[]>([]);
  const imageStoragePath = ref<string>("/user/images");
  const configPath = ref<string>("config.json");

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

  async function loadConfig() {
    try {
      const config = await invoke<AppConfig>('load_config', { 
        configPath: configPath.value 
      });
      imageStoragePath.value = config.image_storage_path;
    } catch (error) {
      console.error('加载配置失败:', error);
    }
  }

  async function saveConfig(newPath: string) {
    try {
      await invoke('save_config', { 
        configPath: configPath.value,
        imagePath: newPath 
      });
      imageStoragePath.value = newPath;
      return true;
    } catch (error) {
      console.error('保存配置失败:', error);
      return false;
    }
  }

  return { 
    fieldNames, 
    pointers, 
    imageStoragePath,
    configPath,
    addRegularPointer, 
    addConditionalPointer, 
    removePointer,
    loadConfig,
    saveConfig
  };
});