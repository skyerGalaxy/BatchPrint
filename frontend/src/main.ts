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
