<template>
  <v-navigation-drawer
    v-model="drawerOpen"
    :rail="rail"
    width="280"
    rail-width="72"
    class="gemini-sidebar"
  >
    <div class="sidebar-wrapper">
      <!-- Header Section -->
      <div class="sidebar-header" :class="{ 'is-rail': rail }">
        <div v-if="!rail" class="expanded-header">
          <div class="logo-container">
            <img src="@/assets/logo.svg" class="logo-img" />
            <span class="brand-title">BatchPrint</span>
          </div>
          <v-btn
            icon
            variant="text"
            density="comfortable"
            class="toggle-btn"
            @click="toggleRail"
          >
            <v-icon size="20" class="ma-0">mdi-arrow-collapse-left</v-icon>
            <v-tooltip activator="parent" location="right">关闭边栏</v-tooltip>
          </v-btn>
        </div>
        <div v-else class="collapsed-header">
          <v-btn
            icon
            variant="text"
            density="comfortable"
            class="toggle-btn mb-4"
            @click="toggleRail"
          >
            <img src="@/assets/logo.svg" class="logo-img collapsed-logo" />
            <v-tooltip activator="parent" location="right">展开边栏</v-tooltip>
          </v-btn>
        </div>
      </div>


      <!-- Scrollable Content Section -->
      <div class="sidebar-content">
        <v-list nav density="compact" class="main-list pa-0">
          <v-list-item
            prepend-icon="mdi-printer-outline"
            title="批量打印"
            value="batch-print"
            to="/batch-print"
            class="nav-item"
            rounded="pill"
          />
          <v-list-item
            prepend-icon="mdi-pencil-outline"
            title="手写笔记"
            value="hand-notes"
            to="/hand-notes"
            class="nav-item"
            rounded="pill"
          />
        </v-list>

        <!-- Divider -->
        <v-divider v-if="!rail" class="my-3 mx-2" />
      </div>

      <!-- Footer Section -->
      <div class="sidebar-footer" :class="{ 'is-rail': rail }">
        <v-list class="pa-0" density="compact" nav>
          <!-- Settings Item -->
          <v-list-item
            v-if="!rail"
            prepend-icon="mdi-cog-outline"
            title="设置"
            value="settings"
            class="footer-item"
            rounded="pill"
            @click="openSettings"
          />
          <v-list-item
            v-else
            class="footer-item justify-center text-center pa-0"
            rounded="pill"
            @click="openSettings"
          >
            <template #prepend>
              <v-icon size="20" class="ma-0">mdi-cog-outline</v-icon>
            </template>
            <v-tooltip activator="parent" location="right">设置</v-tooltip>
          </v-list-item>
        </v-list>

        <!-- Profile Item -->
        <div class="profile-container mt-2" :class="{ 'is-rail': rail }">
          <v-avatar class="profile-avatar" size="32">
            <span class="profile-initials">XW</span>
          </v-avatar>
          <div v-if="!rail" class="profile-info ml-3">
            <div class="profile-name">Xinghe Wu</div>
            <div class="profile-role">管理员</div>
          </div>
          <v-tooltip v-if="rail" activator="parent" location="right">Xinghe Wu (管理员)</v-tooltip>
        </div>
      </div>
    </div>
  </v-navigation-drawer>

  <v-main class="main-wrap">
    <router-view v-slot="{ Component }">
      <keep-alive>
        <component :is="Component" />
      </keep-alive>
    </router-view>
  </v-main>

  <AppFooter />

  <SettingsDialog ref="settingsDialog" />
</template>

<script setup lang="ts">
import SettingsDialog from '@/components/SettingsDialog.vue'

const rail = ref(true)
const drawerOpen = ref(true)

const settingsDialog = ref<InstanceType<typeof SettingsDialog> | null>(null)

const recentItems = ref([
  { title: 'OpenCode 快捷键配置指南', to: '/hand-notes' },
  { title: 'VS Code 快捷键速查指南', to: '/hand-notes' },
  { title: '命令行找不到的排查指南', to: '/hand-notes' },
  { title: 'OpenCode 安装到 D 盘指南', to: '/hand-notes' },
  { title: '手写图片生成专属字体方法', to: '/hand-notes' },
])

function toggleRail() {
  rail.value = !rail.value
}

function openSettings() {
  settingsDialog.value?.openDialog()
}
</script>

<style scoped>
.gemini-sidebar {
  border-right: none !important;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

/* Light theme styles */
.v-theme--light .gemini-sidebar {
  background-color: #f0f4f9 !important;
  color: #1f1f1f;
}
.v-theme--light .gemini-action-btn {
  background-color: #e9eef6 !important;
  color: #041e49 !important;
}
.v-theme--light .gemini-action-btn:hover {
  background-color: #dbe3f1 !important;
}
/* Selected / Active navigation item in Light Theme */
.v-theme--light .nav-item.v-list-item--active,
.v-theme--light .recent-item.v-list-item--active {
  background-color: #dbe3f1 !important;
  color: #041e49 !important;
}

/* Dark theme styles */
.v-theme--dark .gemini-sidebar {
  background-color: #131314 !important;
  color: #e3e3e3;
}
.v-theme--dark .gemini-action-btn {
  background-color: #333538 !important;
  color: #e3e3e3 !important;
}
.v-theme--dark .gemini-action-btn:hover {
  background-color: #3e4043 !important;
}
/* Selected / Active navigation item in Dark Theme */
.v-theme--dark .nav-item.v-list-item--active,
.v-theme--dark .recent-item.v-list-item--active {
  background-color: #2d2f31 !important;
  color: #e3e3e3 !important;
}

.sidebar-wrapper {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  padding: 0;
  overflow: hidden;
}

.sidebar-header {
  padding: 16px;
  display: flex;
  flex-direction: column;
  align-items: stretch;
}
.sidebar-header.is-rail {
  padding: 12px 0;
  align-items: center;
}
.expanded-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}
.collapsed-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
}
.logo-container {
  display: flex;
  align-items: center;
  gap: 12px;
}
.logo-img {
  width: 24px;
  height: 24px;
  object-fit: contain;
}
.logo-img.collapsed-logo {
  margin-top: 8px;
}
.brand-title {
  font-size: 20px;
  font-weight: 500;
  color: inherit;
  font-family: "Google Sans", "Product Sans", "Segoe UI", sans-serif;
  letter-spacing: -0.02em;
}
.toggle-btn {
  color: inherit !important;
}

.action-btn-container {
  padding: 4px 12px 16px;
}
.action-btn-container.is-rail {
  padding: 8px 0 16px;
  display: flex;
  justify-content: center;
  width: 100%;
}
.gemini-action-btn {
  text-transform: none !important;
  font-weight: 500 !important;
  letter-spacing: normal !important;
  transition: all 0.2s ease !important;
}
.gemini-action-btn.expanded {
  width: 100%;
  height: 48px !important;
  border-radius: 24px !important;
  font-size: 14px !important;
  justify-content: flex-start !important;
  padding-left: 18px !important;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05), 0 1px 3px rgba(0,0,0,0.1) !important;
}
.gemini-action-btn.collapsed {
  width: 48px !important;
  height: 48px !important;
  border-radius: 24px !important;
  min-width: 0 !important;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05), 0 1px 3px rgba(0,0,0,0.1) !important;
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 0 12px;
}
.sidebar-content::-webkit-scrollbar {
  width: 6px;
}
.sidebar-content::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.08);
  border-radius: 3px;
}
.sidebar-content:hover::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.15);
}
:deep(.v-theme--dark) .sidebar-content::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.08);
}

.nav-item {
  height: 40px !important;
  min-height: 40px !important;
  margin-bottom: 4px !important;
  font-size: 14px !important;
  font-weight: 500 !important;
  color: #444746 !important;
  border-radius: 20px !important;
  padding: 0 16px !important;
  transition: background-color 0.2s ease, color 0.2s ease !important;
}
.v-theme--dark .nav-item {
  color: #c4c7c5 !important;
}
:deep(.nav-item .v-list-item-title) {
  font-size: 14px !important;
  font-weight: 500 !important;
}
:deep(.nav-item .v-list-item__prepend) {
  margin-inline-end: 16px !important;
}

.recent-section {
  animation: fadeIn 0.3s ease;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}
.recent-title {
  font-size: 12px;
  font-weight: 600;
  color: #444746;
  padding: 12px 12px 8px;
  letter-spacing: 0.05em;
}
.v-theme--dark .recent-title {
  color: #c4c7c5;
}
.recent-list-container {
  max-height: 300px;
  overflow-y: auto;
}
.recent-item {
  height: 36px !important;
  min-height: 36px !important;
  margin-bottom: 2px !important;
  color: #444746 !important;
  border-radius: 18px !important;
  padding: 0 12px !important;
}
.v-theme--dark .recent-item {
  color: #c4c7c5 !important;
}
:deep(.recent-item .v-list-item-title) {
  font-size: 13px !important;
  font-weight: 400 !important;
}
:deep(.recent-item .v-list-item__prepend) {
  margin-inline-end: 12px !important;
}

.sidebar-footer {
  padding: 12px;
  border-top: none;
}
.sidebar-footer.is-rail {
  padding: 12px 0;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.footer-item {
  height: 40px !important;
  min-height: 40px !important;
  color: #444746 !important;
  border-radius: 20px !important;
  font-weight: 500 !important;
  transition: background-color 0.2s ease, color 0.2s ease !important;
}
.v-theme--dark .footer-item {
  color: #c4c7c5 !important;
}
:deep(.footer-item .v-list-item__prepend) {
  margin-inline-end: 16px !important;
}

.profile-container {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  border-radius: 24px;
  transition: background-color 0.2s ease;
  cursor: pointer;
}
.profile-container:hover {
  background-color: rgba(0, 0, 0, 0.04);
}
.v-theme--dark .profile-container:hover {
  background-color: rgba(255, 255, 255, 0.04);
}
.profile-container.is-rail {
  padding: 8px 0;
  justify-content: center;
  width: 100%;
}
.main-wrap {
  flex: 1 1 0% !important;
  overflow: hidden !important;
}

.profile-avatar {
  background: linear-gradient(135deg, #1697F6 0%, #1867C0 100%);
  box-shadow: 0 2px 6px rgba(24, 103, 192, 0.2);
}
.profile-initials {
  font-size: 12px;
  font-weight: 600;
  color: white;
}
.profile-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.profile-name {
  font-size: 13px;
  font-weight: 600;
  color: inherit;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.profile-role {
  font-size: 11px;
  color: #757575;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.v-theme--dark .profile-role {
  color: #9e9e9e;
}
</style>
