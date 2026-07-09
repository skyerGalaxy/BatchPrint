<template>
  <v-navigation-drawer
    v-model="drawerOpen"
    :rail="rail"
    width="220"
    class="app-drawer"
  >
    <div class="drawer-brand">
      <v-icon size="26" color="primary">mdi-layers-triple</v-icon>
      <span v-if="!rail" class="brand-text">AutoFiller</span>
    </div>

    <v-list nav density="compact" class="drawer-nav pa-3 pt-0">
      <v-list-item
        prepend-icon="mdi-printer"
        title="批量打印"
        value="batch-print"
        to="/batch-print"
        active-color="primary"
        rounded="lg"
        class="nav-item mb-1"
      />
      <v-list-item
        prepend-icon="mdi-pencil"
        title="手写笔记"
        value="hand-notes"
        to="/hand-notes"
        active-color="primary"
        rounded="lg"
        class="nav-item mb-1"
      />
    </v-list>

    <template #append>
      <div class="px-3 pb-3">
        <v-divider class="mb-2" />
        <v-list nav density="compact">
          <v-list-item
            prepend-icon="mdi-cog-outline"
            title="设置"
            value="settings"
            @click="openSettings"
            rounded="lg"
            class="nav-item"
          />
        </v-list>
      </div>
    </template>
  </v-navigation-drawer>

  <div
    class="drawer-toggle-wrapper"
    :style="{ left: rail ? '44px' : '208px' }"
  >
    <v-btn
      icon
      size="36"
      variant="elevated"
      color="white"
      class="drawer-toggle-btn"
      @click="toggleRail"
    >
      <v-icon size="22" color="grey-darken-1">
        {{ rail ? 'mdi-chevron-right' : 'mdi-chevron-left' }}
      </v-icon>
    </v-btn>
  </div>

  <v-app-bar density="compact" elevation="0" class="app-bar">
    <v-icon :icon="pageIcon" size="18" color="primary" class="mr-3" />
    <span class="text-body-2 font-weight-medium">{{ pageTitle }}</span>
  </v-app-bar>

  <v-main class="app-main">
    <router-view />
  </v-main>

  <SettingsDialog ref="settingsDialog" />
</template>

<script setup lang="ts">
import SettingsDialog from '@/components/SettingsDialog.vue'

const rail = ref(true)
const drawerOpen = ref(true)
const route = useRoute()

const settingsDialog = ref<InstanceType<typeof SettingsDialog> | null>(null)

const pageMap: Record<string, { title: string; icon: string }> = {
  '/batch-print': { title: '批量打印', icon: 'mdi-printer' },
  '/hand-notes': { title: '手写笔记', icon: 'mdi-pencil' },
}

const pageTitle = computed(() => pageMap[route.path]?.title || 'AutoFiller')
const pageIcon = computed(() => pageMap[route.path]?.icon || 'mdi-layers-triple')

function toggleRail() {
  rail.value = !rail.value
}

function openSettings() {
  settingsDialog.value?.openDialog()
}
</script>

<style scoped>
.app-drawer {
  background: rgb(252, 252, 253);
  border-right: 1px solid rgba(0, 0, 0, 0.06);
}

.app-drawer :deep(.v-navigation-drawer__content) {
  display: flex;
  flex-direction: column;
}

.drawer-brand {
  display: flex;
  align-items: center;
  padding: 16px 16px 12px;
  min-height: 48px;
}

.brand-text {
  font-size: 1rem;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: rgb(15, 23, 42);
  margin-left: 10px;
}

.drawer-nav {
  flex: 1;
  overflow-y: auto;
}

.nav-item {
  border-radius: 10px;
  margin-bottom: 2px;
}

.nav-item :deep(.v-list-item--active) {
  background: rgba(var(--v-theme-primary), 0.08);
}

/* ---- toggle button ---- */
.drawer-toggle-wrapper {
  position: fixed;
  top: 14px;
  z-index: 1000;
  transition: left 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.drawer-toggle-btn {
  box-shadow: 0 2px 16px rgba(0, 0, 0, 0.08), 0 0 0 1px rgba(0, 0, 0, 0.04) !important;
  transition: box-shadow 0.2s, transform 0.2s;
}

.drawer-toggle-btn:hover {
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12), 0 0 0 1px rgba(0, 0, 0, 0.06) !important;
  transform: scale(1.06);
}

/* ---- app bar ---- */
.app-bar {
  background: rgba(255, 255, 255, 0.96) !important;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  padding-left: 20px !important;
}

/* ---- main ---- */
.app-main {
  background: rgb(246, 247, 249) !important;
}
</style>
