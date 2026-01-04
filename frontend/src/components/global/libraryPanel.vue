<script setup lang="ts">
    import { Store } from '@tauri-apps/plugin-store'
    import { readDir, writeFile, exists, readFile } from '@tauri-apps/plugin-fs'
    import { convertFileSrc } from '@tauri-apps/api/core'
    import { open } from '@tauri-apps/plugin-dialog'
    import { useBPStore } from '@/stores/bpstore'


    const dialog = ref(false)
    let settingsStore: Store | null = null;
    const imagePath = ref('');
    const imageList = ref<string[]>([]);
    const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'];

    const bpStore = useBPStore();

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

            console.log('选择的文件:', files);
            
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
                    console.log('上传文件成功:', finalPath);
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
            imagePath.value = bpStore.imagePath || '';
            console.log('图片存储路径:', imagePath.value);
            await loadImages();
        } catch (error) {
            console.error('无法获取 image_storage_path 的值:', error);
        }
    });

    watch(() => bpStore.imagePath, async (newPath) => {
        console.log('检测到图片存储路径变化:', newPath);
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