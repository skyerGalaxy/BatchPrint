<template>
  <v-container fluid class="history-shell px-6 py-6">
    <div class="history-card">
      <div class="card-header">
        <v-icon size="20" color="primary" class="mr-2">mdi-history</v-icon>
        <span class="card-title">历史记录</span>
        <span v-if="items.length > 0" class="count-chip">{{ items.length }} 个项目</span>
        <v-spacer></v-spacer>
        <v-btn
          v-if="items.length > 0"
          variant="text"
          size="small"
          rounded="lg"
          color="grey-darken-1"
          @click="openWorkspacesFolder"
        >
          <v-icon size="16" class="mr-1">mdi-folder-open-outline</v-icon>
          打开目录
        </v-btn>
        <v-btn
          variant="text"
          size="small"
          rounded="lg"
          color="grey-darken-1"
          :loading="loading"
          @click="refresh"
        >
          <v-icon size="16" class="mr-1">mdi-refresh</v-icon>
          刷新
        </v-btn>
      </div>

      <div class="history-body">
        <v-alert
          v-if="ignoredCount > 0"
          type="info"
          variant="tonal"
          density="compact"
          class="legacy-alert"
          closable
          @click:close="ignoredCount = 0"
        >
          检测到 {{ ignoredCount }} 条旧版工作进度记录（以文件副本保存），新版已不再支持，已自动忽略。
          如需清理，可点击右上角「打开目录」手动删除对应的子文件夹。
        </v-alert>

        <div v-if="loading && items.length === 0" class="history-state">
          <v-progress-circular indeterminate size="26" color="primary" />
          <span class="state-text">正在读取历史记录…</span>
        </div>

        <div v-else-if="items.length === 0" class="history-state">
          <v-icon size="42" color="#cbd5e1">mdi-folder-clock-outline</v-icon>
          <span class="state-title">暂无历史记录</span>
          <span class="state-text">
            在「批量打印」页点击预览区右上角的「保存工作进度」，项目会保存在这里；
            之后再次保存同一项目，旧进度会收进该项目的历史版本
          </span>
          <v-btn color="primary" variant="tonal" rounded="lg" class="mt-2" @click="goBatchPrint">
            <v-icon size="16" class="mr-1">mdi-printer-outline</v-icon>
            去编辑
          </v-btn>
        </div>

        <div v-else class="history-grid">
          <v-card
            v-for="item in items"
            :key="item.id"
            class="history-item"
            rounded="lg"
            variant="outlined"
            @click="openItem(item)"
          >
            <div class="item-main">
              <div class="item-title-row">
                <v-icon size="18" :color="item.templateType === 'pdf' ? 'primary' : 'teal'">
                  {{ item.templateType === 'pdf' ? 'mdi-file-pdf-box' : 'mdi-file-word-box' }}
                </v-icon>
                <span class="item-title" :title="item.title">{{ item.title }}</span>
                <v-chip size="x-small" variant="tonal" :color="item.templateType === 'pdf' ? 'primary' : 'teal'">
                  {{ item.templateType === 'pdf' ? 'PDF' : 'DOCX' }}
                </v-chip>
              </div>

              <div class="item-meta">
                <div class="meta-row">
                  <v-icon size="13">mdi-file-document-outline</v-icon>
                  <span :title="item.templatePath">{{ basename(item.templatePath) }}</span>
                </div>
                <div class="meta-row">
                  <v-icon size="13">mdi-file-excel</v-icon>
                  <span :title="item.excelPath">{{ basename(item.excelPath) }}</span>
                </div>
                <div class="meta-row">
                  <v-icon size="13">mdi-clock-outline</v-icon>
                  <span>{{ formatTime(item.savedAt) }}</span>
                </div>
                <div class="meta-row">
                  <v-icon size="13">mdi-tag-multiple-outline</v-icon>
                  <span>{{ item.iconCount }} 个标注</span>
                </div>
                <div v-if="item.revisionCount > 1" class="meta-row">
                  <v-icon size="13">mdi-history</v-icon>
                  <span>{{ item.revisionCount }} 个版本</span>
                </div>
              </div>
            </div>

            <div class="item-actions" @click.stop>
              <v-btn
                size="small"
                variant="tonal"
                color="primary"
                rounded="lg"
                :loading="openingId === item.id"
                @click="openItem(item)"
              >
                <v-icon start size="14">mdi-play-circle-outline</v-icon>
                继续编辑
              </v-btn>
              <div class="item-action-row">
                <v-btn
                  icon
                  size="small"
                  variant="text"
                  :color="item.revisionCount > 1 ? 'primary' : 'grey-darken-1'"
                  :disabled="item.revisionCount <= 1"
                  @click="openRevisions(item)"
                >
                  <v-badge
                    v-if="item.revisionCount > 1"
                    :content="item.revisionCount"
                    color="primary"
                    offset-x="-2"
                    offset-y="-2"
                  >
                    <v-icon size="16">mdi-history</v-icon>
                  </v-badge>
                  <v-icon v-else size="16">mdi-history</v-icon>
                  <v-tooltip activator="parent" location="top">
                    {{ item.revisionCount > 1 ? `查看 ${item.revisionCount} 个历史版本` : '暂无历史版本' }}
                  </v-tooltip>
                </v-btn>
                <v-btn
                  icon
                  size="small"
                  variant="text"
                  color="grey-darken-1"
                  @click="askDelete(item)"
                >
                  <v-icon size="16">mdi-delete-outline</v-icon>
                  <v-tooltip activator="parent" location="top">删除项目</v-tooltip>
                </v-btn>
              </div>
            </div>
          </v-card>
        </div>
      </div>
    </div>

    <v-dialog v-model="deleteDialog" max-width="400">
      <v-card rounded="xl">
        <v-card-item>
          <div class="d-flex align-center">
            <v-icon color="error" size="24" class="mr-2">mdi-alert-circle-outline</v-icon>
            <v-card-title class="pa-0">删除项目</v-card-title>
          </div>
        </v-card-item>
        <v-card-text>
          将删除项目「{{ pendingDelete?.title }}」及其全部历史版本。模板与表格的原文件不会被删除。是否继续？
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="text" rounded="lg" @click="deleteDialog = false">取消</v-btn>
          <v-btn variant="flat" color="error" rounded="lg" :loading="deleting" @click="confirmDelete">删除</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 某个项目的历史版本 -->
    <WorkspaceHistoryDialog
      v-model="revisionDialog"
      :data-path="bpStore.dataPath"
      :project-id="revisionProject?.id ?? ''"
      :project-title="revisionProject?.title ?? ''"
      :restoring-key="restoringRevisionKey"
      @restore="restoreRevision"
    />

    <v-snackbar v-model="snackbar" :timeout="3000" location="bottom" rounded="lg">
      {{ snackbarMessage }}
    </v-snackbar>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted, onActivated, watch } from 'vue'
import { useRouter } from 'vue-router'
import { invoke } from '@tauri-apps/api/core'
import WorkspaceHistoryDialog from '@/components/WorkspaceHistoryDialog.vue'
import { useBPStore } from '@/stores/bpstore'
import type { WorkspaceListItem, WorkspaceSnapshot } from '@/types/workspace'
import { deleteWorkspace, listWorkspaces, readWorkspace, revisionKey, workspacesRoot } from '@/utils/workspace'

const bpStore = useBPStore()
const router = useRouter()

const items = ref<WorkspaceListItem[]>([])
const loading = ref(false)
const openingId = ref('')
const deleteDialog = ref(false)
const deleting = ref(false)
const pendingDelete = ref<WorkspaceListItem | null>(null)
const revisionDialog = ref(false)
const revisionProject = ref<WorkspaceListItem | null>(null)
const restoringRevisionKey = ref('')
const snackbar = ref(false)
const snackbarMessage = ref('')
/** 被忽略的旧版（副本式）记录数量，仅用于提示 */
const ignoredCount = ref(0)

function notify(message: string) {
  snackbarMessage.value = message
  snackbar.value = true
}

/** 取路径最后一段作为展示文件名 */
function basename(path: string): string {
  return path ? path.split(/[/\\]/).pop() || path : ''
}

function formatTime(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

async function refresh() {
  if (!bpStore.dataPath) return
  loading.value = true
  try {
    const result = await listWorkspaces(bpStore.dataPath)
    items.value = result.items
    ignoredCount.value = result.ignored
  } catch (error) {
    console.error('读取历史记录失败:', error)
    notify(`读取历史记录失败：${(error as Error)?.message || '未知错误'}`)
  } finally {
    loading.value = false
  }
}

/** 把快照交给 /batch-print 页面，由它在激活时恢复现场 */
async function openItem(item: WorkspaceListItem) {
  if (openingId.value) return
  openingId.value = item.id
  try {
    const snapshot = await readWorkspace(bpStore.dataPath, item.id)
    bpStore.requestRestore(snapshot)
    router.push('/batch-print')
  } catch (error) {
    console.error('打开历史记录失败:', error)
    notify(`打开失败：${(error as Error)?.message || '未知错误'}`)
  } finally {
    openingId.value = ''
  }
}

function openRevisions(item: WorkspaceListItem) {
  revisionProject.value = item
  revisionDialog.value = true
}

/** 从项目历史弹窗恢复某个旧版本：交给 /batch-print 页面重建现场 */
async function restoreRevision(snapshot: WorkspaceSnapshot) {
  const key = revisionKey(snapshot)
  if (restoringRevisionKey.value) return
  const ok = window.confirm(
    `将把项目恢复到 ${formatTime(snapshot.savedAt)} 的版本：\n${snapshot.title}\n\n当前未保存的改动会丢失（已保存的版本不受影响），是否继续？`,
  )
  if (!ok) return
  restoringRevisionKey.value = key
  try {
    bpStore.requestRestore(snapshot)
    revisionDialog.value = false
    router.push('/batch-print')
  } catch (error) {
    console.error('恢复历史版本失败:', error)
    notify(`恢复失败：${(error as Error)?.message || '未知错误'}`)
  } finally {
    restoringRevisionKey.value = ''
  }
}

function askDelete(item: WorkspaceListItem) {
  pendingDelete.value = item
  deleteDialog.value = true
}

async function confirmDelete() {
  const target = pendingDelete.value
  if (!target) return
  deleting.value = true
  try {
    await deleteWorkspace(bpStore.dataPath, target.id)
    deleteDialog.value = false
    pendingDelete.value = null
    // 删除的正是当前编辑的项目时，解除关联，避免下次保存写回已删除的目录
    if (bpStore.currentProjectId === target.id) bpStore.clearCurrentProject()
    bpStore.bumpWorkspaces()
    await refresh()
    notify('已删除该项目及其历史版本')
  } catch (error) {
    console.error('删除历史记录失败:', error)
    notify(`删除失败：${(error as Error)?.message || '未知错误'}`)
  } finally {
    deleting.value = false
  }
}

async function openWorkspacesFolder() {
  try {
    await invoke('open_folder', { path: workspacesRoot(bpStore.dataPath) })
  } catch (error) {
    console.error('打开目录失败:', error)
    notify('打开目录失败，请检查存储路径是否可用')
  }
}

function goBatchPrint() {
  router.push('/batch-print')
}

onMounted(refresh)
// 本页被 keep-alive 缓存：每次回到本页都重新扫描，保证刚保存 / 删除的记录即时可见
onActivated(refresh)
watch(() => bpStore.workspacesVersion, refresh)
watch(() => bpStore.dataPath, refresh)
</script>

<style scoped>
.history-shell {
  height: 100%;
  overflow: hidden;
}

.history-card {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: #fff;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  overflow: hidden;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 20px 12px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.04);
}

.card-title {
  font-size: 0.82rem;
  font-weight: 600;
  color: rgb(15, 23, 42);
  letter-spacing: -0.01em;
}

.count-chip {
  font-size: 0.7rem;
  font-weight: 600;
  color: rgb(100, 116, 139);
  background: rgba(15, 23, 42, 0.05);
  border-radius: 999px;
  padding: 2px 10px;
}

.history-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 16px 20px 20px;
}

.legacy-alert {
  margin-bottom: 12px;
  font-size: 0.76rem;
}

.history-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 100%;
  min-height: 240px;
  text-align: center;
  color: #94a3b8;
}

.state-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: rgb(71, 85, 105);
}

.state-text {
  max-width: 360px;
  font-size: 0.78rem;
  line-height: 1.6;
}

.history-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 12px;
}

.history-item {
  display: flex;
  align-items: stretch;
  gap: 12px;
  padding: 14px 16px;
  cursor: pointer;
  transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.15s ease;
}

.history-item:hover {
  border-color: rgba(24, 103, 192, 0.45);
  box-shadow: 0 4px 14px rgba(24, 103, 192, 0.12);
  transform: translateY(-1px);
}

.item-main {
  flex: 1;
  min-width: 0;
}

.item-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.item-title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.88rem;
  font-weight: 600;
  color: rgb(15, 23, 42);
}

.item-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 10px;
  font-size: 0.74rem;
  color: rgb(100, 116, 139);
}

.meta-row {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.meta-row span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  justify-content: space-between;
  gap: 8px;
}

.item-action-row {
  display: flex;
  align-items: center;
  gap: 2px;
}
</style>
