<script setup lang="ts">
    import {ref, onMounted} from 'vue'
    import { open } from '@tauri-apps/plugin-dialog'
    import { Store } from '@tauri-apps/plugin-store'
    import { invoke } from '@tauri-apps/api/core'

    import { useBPStore } from '@/stores/bpstore'
    import { mkdir } from '@tauri-apps/plugin-fs'

    const dialog = ref(false)
    const selectedItemIndex = ref(0)
    const imagePath = ref('')
    let settingsStore: Store | null = null
    const settingsItems = [
        { title: '通用设置', icon: 'mdi-cog' },
        { title: '存储与路径', icon: 'mdi-folder-settings' },
        { title: '帐户与安全', icon: 'mdi-account-circle' },
        { title: '关于', icon: 'mdi-information' },
    ];

    const selectedPath = ref<string>('');

    //控制是否移动选项对话框
    const isMovingDialog = ref(false)

    const bpStore = useBPStore();

    async function openPathDialog() {
        try {
            const result = await open({
                directory: true,
                multiple: false,
                title: '选择图片存储路径'
            });
            if (result) {
                // 如果选择的路径与当前路径相同，直接返回
                if (result === bpStore.imagePath) {
                    console.info('选择的路径与当前路径相同');
                    return;
                }
                selectedPath.value = result;
                isMovingDialog.value = true;
                console.log('选择的路径:', result);
            }
        } catch (error) {
            console.error('打开文件对话框失败:', error);
        }
    }

    function saveSettings() {
        // 这里可以添加保存设置的逻辑
        console.log('保存设置');
        dialog.value = false;
    }

    function openDialog() {
        console.log('打开设置对话框');
        dialog.value = true;
        selectedItemIndex.value = 0;
    }

    // 公共函数：更新路径到所有存储位置
    async function updateImagePath(newPath: string) {
        imagePath.value = newPath;
        if (!settingsStore) {
            settingsStore = await Store.load('settings.json');
        }
        await settingsStore.set('image_storage_path', newPath);
        await settingsStore.save();
        bpStore.imagePath = newPath;
    }

    async function createFolder(path: string) {
        try {
            await Promise.all([
                mkdir(`${path}/sealImg`, { recursive: true }),
                mkdir(`${path}/signImg`, { recursive: true }),
            ]);
            await updateImagePath(path);
            isMovingDialog.value = false;
            console.log('文件夹创建并路径已更新');
        } catch (error) {
            console.error('创建文件夹失败:', error);
        }
    }

    async function moveFolders(newPath: string) {
        try {
            const result = await invoke('move_folder_with_extra', {
                src: bpStore.imagePath,
                dest: newPath
            });
            console.log('移动结果:', result);
            
            await updateImagePath(newPath);
            isMovingDialog.value = false;
            console.log('文件夹移动成功');
        } catch (error) {
            console.error('移动文件夹失败:', error);
        }
    }

    async function initStore() {
        try {
            settingsStore = await Store.load('settings.json')
            const val = await settingsStore.get<string>('image_storage_path')
            if (typeof val === 'string') {
                imagePath.value = val
            }
        } catch (e) {
            console.warn('初始化设置存储失败:', e)
        }
    }

    onMounted(() => {
        initStore()
    })


    defineExpose({
        openDialog,
    });

</script>

<template>
    <v-dialog
        v-model="dialog"
        max-width="800"
        scrollable
    >
        <v-card>
            <v-toolbar color="primary" title="应用设置">
                <v-btn icon @click="dialog = false">
                    <v-icon>mdi-close</v-icon>
                </v-btn>
            </v-toolbar>
            <div class="d-flex flex-row" style="max-height: 600px;height: 300px; overflow-y: auto;">
                <v-list density="comfortable" nav class="flex-grow-0 flex-shrink-0" style ="width: 250px;">
                    <v-list-item
                        v-for="(item,i) in settingsItems"
                        :key="i"
                        :value="i"
                        :active="selectedItemIndex === i"
                        active-color="primary"
                        @click="selectedItemIndex = i"
                        :prepend-icon="item.icon"
                    >
                        <v-list-item-title>{{ item.title }}</v-list-item-title>
                    </v-list-item>
                </v-list>
                <v-card-text class="flex-grow-1 pa-4">
                    <v-window v-model="selectedItemIndex"direction="vertical">
                        <v-window-item :value="0">
                            <div>通用设置</div>
                        </v-window-item>

                        <v-window-item :value="1">
                            <h2 class="text-h6 mb-4">存储与路径</h2>
                            <p class="text-subtitle-1 mb-2">图片存储路径:</p>
                            <v-text-field
                                label="当前路径"
                                density="compact"
                                readonly
                                append-icon="mdi-folder-open"
                                v-model="imagePath"
                            />
                            <v-btn color="success" class="mt-2" @click="openPathDialog">更改路径</v-btn>
                            <v-alert type="info" class="mt-4">
                                推荐将图片路径更改到非系统盘，以节省 C 盘空间
                            </v-alert>
                        </v-window-item>

                        <v-window-item :value="2">
                            <div>帐户与安全</div>
                        </v-window-item>

                        <v-window-item :value="3">
                            <div>关于</div>
                        </v-window-item>
                    </v-window>
                </v-card-text>
            </div>

            <v-card-actions class="d-flex justify-end bg-grey-lighten-4">
                <v-btn color="primary" @click="saveSettings">保存</v-btn>
                <v-btn text @click="dialog = false">关闭</v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
    <v-dialog
        v-model="isMovingDialog"
        persistent
        max-width="400"
    >
        <v-card>
            <v-card-text>
                是否要移动原有图片到新路径？
            </v-card-text>
            <v-card-actions class="d-flex justify-end">
                <v-btn text @click="createFolder(selectedPath)">否</v-btn>
                <v-btn color="primary" @click="moveFolders(selectedPath)">是</v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
</template>

