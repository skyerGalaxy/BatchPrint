<template>
  <v-container fluid class="notes-shell px-6 py-6">
    <div class="notes-card">
      <div class="card-header">
        <v-icon size="20" color="teal" class="mr-2">mdi-pencil-box-outline</v-icon>
        <span class="card-title">手写笔记</span>
      </div>

      <div class="pa-6">
        <p class="text-body-2 text-medium-emphasis mb-4">
          记录、草稿或临时备注空间，后续将接入编辑器与列表视图。
        </p>

        <div class="d-flex flex-wrap ga-2 mb-4">
          <v-chip color="primary" variant="tonal" size="small">记录</v-chip>
          <v-chip color="teal" variant="tonal" size="small">草稿</v-chip>
          <v-chip color="blue" variant="tonal" size="small">待办</v-chip>
        </div>

        <v-alert type="info" variant="tonal" density="compact" rounded="lg" class="mb-0">
          即将推出，敬请期待。
        </v-alert>
      </div>
    </div>
  </v-container>
</template>

<script setup lang="ts"></script>

<style scoped>
.notes-shell {
  max-width: 900px;
  height: 100%;
}

.notes-card {
  background: #fff;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  overflow: hidden;
}

.card-header {
  display: flex;
  align-items: center;
  padding: 16px 20px 12px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.04);
}

.card-title {
  font-size: 0.82rem;
  font-weight: 600;
  color: rgb(15, 23, 42);
  letter-spacing: -0.01em;
}
</style>
