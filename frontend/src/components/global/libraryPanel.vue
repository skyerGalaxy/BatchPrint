<script setup lang="ts">
    import { readDir, writeFile, exists, readFile } from '@tauri-apps/plugin-fs'
    import { convertFileSrc } from '@tauri-apps/api/core'
    import { open } from '@tauri-apps/plugin-dialog'
    import { useBPStore } from '@/stores/bpstore'


    const dialog = ref(false)
    const imagePath = ref('');
    const imageList = ref<string[]>([]);
    const imageList_signature = ref<string[]>([]);
    const imageList_seal = ref<string[]>([]);

    const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'];

    const bpStore = useBPStore();

    const tab = ref("one");

    function openDialog() {
        dialog.value = true;
    }

    async function uploadImage() {
        if (!imagePath.value) {
            alert('请先设置图片存储路径');
            return;
        }

        try {
            // 打开文件选择对话框
            const selected = await open({
                multiple: true,
                filters: [
                    {
                        name: '图片',
                        extensions: ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp']
                    }
                ]
            });

            if (!selected) return;

            const files = Array.isArray(selected) ? selected : [selected];
            
            for (const filePath of files) {
                try {
                    // 读取源文件
                    const fileData = await readFile(filePath);
                    
                    // 提取文件名
                    const fileName = filePath.split('\\').pop() || filePath.split('/').pop() || 'image';
                    const targetPath = `${imagePath.value}/${fileName}`;
                    
                    // 检查文件是否已存在，如果存在则添加时间戳
                    let finalPath = targetPath;
                    if (await exists(targetPath)) {
                        const timestamp = Date.now();
                        const [name, ext] = fileName.split(/\.(?=[^\.]+$)/);
                        finalPath = `${imagePath.value}/${name}_${timestamp}.${ext}`;
                    }
                    
                    // 写入目标文件
                    await writeFile(finalPath, fileData);
                } catch (error) {
                    console.error('上传单个文件失败:', error);
                }
            }
            
            // 刷新图片列表
            await loadImages();
        } catch (error) {
            console.error('上传图片失败:', error);
            alert('上传图片失败');
        }
    }

    async function loadImages() {
        if (!imagePath.value) {
            imageList_signature.value = [];
            imageList_seal.value = [];
            return;
        }

        try {
            const files_signature = await readDir(imagePath.value.concat('/signature'), { recursive: false });
            const files_seal = await readDir(imagePath.value.concat('/seal'), { recursive: false });
            imageList_signature.value = files_signature
                .filter(file => file.isFile)
                .map(file => file.name)
                .filter(name => imageExtensions.some(ext => name.toLowerCase().endsWith(ext)))
                .map(name => convertFileSrc(`${imagePath.value}/signature/${name}`));
        } catch (error) {
            console.error('无法读取图片目录:', error);
            imageList_signature.value = [];
            imageList_seal.value = [];
        }
    }

    defineExpose({
        openDialog
    });
    

    onMounted(async () => {
        try {
            imagePath.value = bpStore.imagePath || '';
            await loadImages();
        } catch (error) {
            console.error('无法获取 image_storage_path 的值:', error);
        }
    });

    watch(() => bpStore.imagePath, async (newPath) => {
        imagePath.value = newPath || '';
        await loadImages();
    });
</script>

<template>
    <v-dialog v-model="dialog" max-width="800" scrollable>
        <v-card>
            <v-toolbar color="primary" title="素材库">
                <v-btn icon @click="uploadImage" title="上传图片">
                    <v-icon>mdi-upload</v-icon>
                </v-btn>
                <v-spacer></v-spacer>
                <v-btn icon @click="dialog = false">
                    <v-icon>mdi-close</v-icon>
                </v-btn>
            </v-toolbar>
            <v-card-text>
                <v-sheet>
                    <v-tabs v-model="tab" background-color="transparent" grow>
                        <v-tab value="one">签字</v-tab>
                        <v-tab value="two">印章</v-tab>
                    </v-tabs>
                    <v-divider></v-divider>
                    <v-tabs-window v-model="tab">
                        <v-tabs-window-item value="one">
                            <v-sheet>
                                <div v-if="imageList.length === 0" class="text-center py-8">
                                    <p class="text-grey">暂无图片</p>
                                </div>
                                <v-row v-else dense>
                                    <v-col v-for="(imgSrc, index) in imageList" :key="index" cols="12" sm="6" md="4">
                                        <v-img :src="imgSrc" aspect-ratio="1" cover class="rounded"></v-img>
                                    </v-col>
                                </v-row>
                            </v-sheet>
                        </v-tabs-window-item>
                        <v-tabs-window-item value="two">
                            <v-sheet>
                                <div v-if="imageList.length === 0" class="text-center py-8">
                                    <p class="text-grey">暂无图片</p>
                                </div>
                                <v-row v-else dense>
                                    <v-col v-for="(imgSrc, index) in imageList" :key="index" cols="12" sm="6" md="4">
                                        <v-img :src="imgSrc" aspect-ratio="1" cover class="rounded"></v-img>
                                    </v-col>
                                </v-row>
                            </v-sheet>
                        </v-tabs-window-item>
                    </v-tabs-window>
                </v-sheet>
            </v-card-text>
        </v-card>
    </v-dialog>
</template>