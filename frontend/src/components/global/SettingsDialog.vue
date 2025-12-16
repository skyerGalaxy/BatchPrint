<script>
    import {ref} from 'vue'

    const dialog = ref(false)
    const selectedItemIndex = ref(0)
    const settingsItems = [
        { title: '通用设置', icon: 'mdi-cog' },
        { title: '存储与路径', icon: 'mdi-folder-settings' },
        { title: '帐户与安全', icon: 'mdi-account-circle' },
        { title: '关于', icon: 'mdi-information' },
    ];

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
            <div class="d-flex flex-row">
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
                    /////////
                </v-card-text>
            </div>
        </v-card>
    </v-dialog>
</template>

