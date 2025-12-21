<script setup lang="ts">
    const dialog = ref(false)

    function openDialog() {
        dialog.value = true;
    }

    defineExpose({
        openDialog
    });
</script>

<template>
    <v-dialog v-model="dialog" max-width="800" scrollable>
        <v-card>
            <v-card-title class="text-h5">图书馆面板</v-card-title>
            <v-card-text>
                <!-- 图书馆面板的内容 -->
                <p>这里是图书馆面板的内容。</p>
            </v-card-text>
        </v-card>
    </v-dialog>
</template>