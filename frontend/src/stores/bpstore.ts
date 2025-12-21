import { ref } from "vue";
import { defineStore } from "pinia";

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



  return { 
    fieldNames, 
    pointers, 
    addRegularPointer, 
    addConditionalPointer, 
    removePointer,
  };
});