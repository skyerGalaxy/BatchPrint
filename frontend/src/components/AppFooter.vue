<template>
  <v-footer app height="32" class="app-footer">
    <span class="text-caption text-medium-emphasis">
      &copy; {{ new Date().getFullYear() }} AutoFiller
    </span>
  </v-footer>
</template>

<script setup lang="ts">
  //
</script>

<style scoped>
.app-footer {
  background: transparent !important;
  border-top: 1px solid rgba(0, 0, 0, 0.04);
  justify-content: center;
}
</style>
