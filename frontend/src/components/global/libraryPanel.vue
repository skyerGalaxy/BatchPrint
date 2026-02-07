<script setup lang="ts">
    import { readDir, writeFile, exists, readFile, mkdir } from '@tauri-apps/plugin-fs'
    import { convertFileSrc } from '@tauri-apps/api/core'
    import { open } from '@tauri-apps/plugin-dialog'
    import { useBPStore } from '@/stores/bpstore'

    const dialog = ref(false)
    const imagePath = ref('');
    const imageList_signature = ref<string[]>([]);
    const imageList_seal = ref<string[]>([]);
    const uploading = ref(false);
    const snackbar = ref(false);
    const snackbarText = ref('');

    const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'];

    const bpStore = useBPStore();

    const tab = ref("one");

    // 获取当前选中的目录类型
    const currentImageType = computed(() => {
        return tab.value === 'one' ? 'signImg' : 'sealImg';
    });

    // 获取当前选中的图片列表
    const currentImageList = computed(() => {
        return tab.value === 'one' ? imageList_signature.value : imageList_seal.value;
    });

    function openDialog() {
        dialog.value = true;
    }

    function showMessage(message: string) {
        snackbarText.value = message;
        snackbar.value = true;
    }

    async function uploadImage() {
        if (!imagePath.value) {
            showMessage('请先设置图片存储路径');
            return;
        }

        try {
            uploading.value = true;
            
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
            
            // 确定目标目录
            const targetDir = `${imagePath.value}/${currentImageType.value}`;
            
            // 确保目标目录存在
            if (!await exists(targetDir)) {
                await mkdir(targetDir, { recursive: true });
            }
            
            let successCount = 0;
            let failCount = 0;

            for (const filePath of files) {
                try {
                    // 读取源文件
                    const fileData = await readFile(filePath);
                    
                    // 提取文件名
                    const fileName = filePath.split('\\').pop() || filePath.split('/').pop() || 'image';
                    
                    let targetPath = `${targetDir}/${fileName}`;
                    
                    // 检查文件是否已存在,如果存在则添加时间戳
                    if (await exists(targetPath)) {
                        const timestamp = Date.now();
                        const dotIndex = fileName.lastIndexOf('.');
                        if (dotIndex > 0) {
                            const name = fileName.substring(0, dotIndex);
                            const ext = fileName.substring(dotIndex);
                            targetPath = `${targetDir}/${name}_${timestamp}${ext}`;
                        } else {
                            targetPath = `${targetDir}/${fileName}_${timestamp}`;
                        }
                    }
                    
                    // 写入目标文件
                    await writeFile(targetPath, fileData);
                    successCount++;
                } catch (error) {
                    console.error('上传单个文件失败:', error);
                    failCount++;
                }
            }
            
            // 刷新图片列表
            await loadImages();
            
            if (failCount === 0) {
                showMessage(`成功上传 ${successCount} 张图片`);
            } else {
                showMessage(`上传完成: 成功 ${successCount} 张, 失败 ${failCount} 张`);
            }
        } catch (error) {
            console.error('上传图片失败:', error);
            showMessage('上传图片失败');
        } finally {
            uploading.value = false;
        }
    }

    async function loadImagesFromDir(dirPath: string): Promise<string[]> {
        try {
            if (!await exists(dirPath)) {
                return [];
            }

            const files = await readDir(dirPath);
            return files
                .filter(file => file.isFile)
                .map(file => file.name)
                .filter(name => imageExtensions.some(ext => name.toLowerCase().endsWith(ext)))
                .map(name => convertFileSrc(`${dirPath}/${name}`));
        } catch (error) {
            console.error(`无法读取图片目录 ${dirPath}:`, error);
            return [];
        }
    }

    async function loadImages() {
        if (!imagePath.value) {
            imageList_signature.value = [];
            imageList_seal.value = [];
            bpStore.imageList_signature = [];
            bpStore.imageList_seal = [];
            return;
        }

        try {
            [imageList_signature.value, imageList_seal.value] = await Promise.all([
                loadImagesFromDir(`${imagePath.value}/signImg`),
                loadImagesFromDir(`${imagePath.value}/sealImg`)
            ]);
            bpStore.imageList_signature = imageList_signature.value;
            bpStore.imageList_seal = imageList_seal.value;
        } catch (error) {
            console.error('加载图片列表失败:', error);
            imageList_signature.value = [];
            imageList_seal.value = [];
            bpStore.imageList_signature = [];
            bpStore.imageList_seal = [];
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
            console.error('初始化失败:', error);
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
                <v-btn 
                    icon 
                    @click="uploadImage" 
                    title="上传图片"
                    :loading="uploading"
                    :disabled="uploading"
                >
                    <v-icon>mdi-upload</v-icon>
                </v-btn>
                <v-spacer></v-spacer>
                <v-btn 
                    icon 
                    @click="loadImages" 
                    title="刷新"
                >
                    <v-icon>mdi-refresh</v-icon>
                </v-btn>
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
                    <v-tabs-window v-model="tab" class="overflow-y-auto" style="height: 600px;">
                        <v-tabs-window-item v-for="tabValue in ['one', 'two']" :key="tabValue" :value="tabValue">
                            <v-sheet class="pa-4">
                                <div v-if="currentImageList.length === 0" class="text-center py-8">
                                    <p class="text-grey">暂无图片</p>
                                </div>
                                <v-row v-else dense>
                                    <v-col v-for="(imgSrc, index) in currentImageList" :key="index" cols="12" sm="6" md="4">
                                        <v-img :src="imgSrc" aspect-ratio="1" cover class="rounded"></v-img>
                                    </v-col>
                                </v-row>
                            </v-sheet>
                        </v-tabs-window-item>
                    </v-tabs-window>
                </v-sheet>
            </v-card-text>
        </v-card>
        
        <v-snackbar v-model="snackbar" :timeout="3000">
            {{ snackbarText }}
        </v-snackbar>
    </v-dialog>
</template>