/**
 * main.ts
 *
 * Bootstraps Vuetify and other plugins then mounts the App`
 */

// Plugins
import { registerPlugins } from '@/plugins'

// Components
import App from './App.vue'

// Composables
import { createApp } from 'vue'
import {createPinia} from "pinia";
import { useBPStore } from './stores/bpstore';
import { invoke } from '@tauri-apps/api/core';


// Styles
import 'unfonts.css'

const app = createApp(App)

registerPlugins(app);
const pinia = createPinia();
app.use(pinia)

//在挂载前初始化应用配置
const bpStore = useBPStore(pinia);
await bpStore.initializeApp();

app.mount('#app')

document.addEventListener('contextmenu', e => e.preventDefault())

async function pollBackend() {
  for (let i = 0; i < 60; i++) {
    try {
      const status = await invoke('get_backend_status') as string;
      if (status.startsWith('ready')) {
        bpStore.backendReady = true;
        bpStore.backendLog = status;
        console.log('backend ready');
        return;
      }
      bpStore.backendLog = status;
    } catch { /* command not available in dev mode */ return; }
    await new Promise(r => setTimeout(r, 1000));
  }
}

pollBackend();
