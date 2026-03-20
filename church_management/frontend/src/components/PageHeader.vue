<script setup>
defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: "" },
});
</script>

<template>
  <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-5">
    <div class="min-w-0">
      <h1 class="text-xl sm:text-2xl font-bold text-gray-900 truncate">{{ title }}</h1>
      <p v-if="subtitle" class="text-xs sm:text-sm text-gray-500 mt-0.5">{{ subtitle }}</p>
    </div>
    <div class="flex items-center gap-2 shrink-0">
      <slot name="actions" />
    </div>
  </div>
</template>
