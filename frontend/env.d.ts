/// <reference types="vite/client" />
/// <reference types="unplugin-vue-router/client" />
/// <reference types="vite-plugin-vue-layouts-next/client" />

/////告诉TypeScript编译器如何处理以.vue结尾的文件
//匹配所有.vue文件
declare module '*.vue' {
  //这是vue定义组件的标准类型
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  //将这个组件作为默认导出,这样在导入的时候,typeScript就把.vue文件看做一个vue组件对象
  export default component
}