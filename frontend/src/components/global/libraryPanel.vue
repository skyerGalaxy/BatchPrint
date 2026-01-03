<script setup lang="ts">
    import { Store } from '@tauri-apps/plugin-store'
    import { readDir } from '@tauri-apps/plugin-fs'
    import { convertFileSrc } from '@tauri-apps/api/core'

    const dialog = ref(false)
    let settingsStore: Store | null = null;
    const imagePath = ref('');
    const imageList = ref<string[]>([]);
    const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'];

    function openDialog() {
        dialog.value = true;
    }

    async function loadImages() {
        if (!imagePath.value) {
            imageList.value = [];
            return;
        }

        try {
            const files = await readDir(imagePath.value);
            imageList.value = files
                .filter(file => file.isFile)
                .map(file => file.name)
                .filter(name => imageExtensions.some(ext => name.toLowerCase().endsWith(ext)))
                .map(name => convertFileSrc(`${imagePath.value}/${name}`));

            console.log('加载图片:', imageList.value);
        } catch (error) {
            console.error('无法读取图片目录:', error);
            imageList.value = [];
        }
    }

    defineExpose({
        openDialog
    });

    onMounted(async () => {
        try {
            settingsStore = await Store.load('settings.json')
            imagePath.value = await settingsStore.get<string>('image_storage_path') || '';
            console.log('图片存储路径:', imagePath.value);
            await loadImages();
        } catch (error) {
            console.error('无法获取 image_storage_path 的值:', error);
        }
    });

    watch(imagePath, async (newPath) => {
        await loadImages();
    });
</script>

<template>
    <v-dialog v-model="dialog" max-width="800" scrollable>
        <v-card>
            <v-toolbar color="primary" title="素材库">
            </v-toolbar>
            <v-card-text>
                <div v-if="imageList.length === 0" class="text-center py-8">
                    <p class="text-grey">暂无图片</p>
                </div>
                <v-row v-else>
                    <v-col v-for="(imgSrc, index) in imageList" :key="index" cols="12" sm="6" md="4">
                        <v-img :src="imgSrc" aspect-ratio="1" cover class="rounded"></v-img>
                    </v-col>
                </v-row>
            </v-card-text>
        </v-card>
    </v-dialog>
</template>