<script setup>
import { computed } from "vue";

/** ‹ 2026 › — steps through the years that have records (newest last). */
const props = defineProps({
  modelValue: { type: Number, default: null },
  years: { type: Array, required: true },
});
const emit = defineEmits(["update:modelValue"]);

const sorted = computed(() => [...props.years].sort((a, b) => a - b));
const idx = computed(() => sorted.value.indexOf(props.modelValue));
const prev = computed(() => (idx.value > 0 ? sorted.value[idx.value - 1] : null));
const next = computed(() => (idx.value >= 0 && idx.value < sorted.value.length - 1 ? sorted.value[idx.value + 1] : null));
</script>

<template>
  <div class="inline-flex items-center rounded-xl bg-white border border-gray-200 shadow-sm text-sm" role="group" aria-label="Year">
    <button
      type="button"
      class="w-9 h-9 flex items-center justify-center rounded-l-xl text-gray-500 hover:bg-gray-50 hover:text-gray-900 disabled:text-gray-200 disabled:hover:bg-transparent cursor-pointer disabled:cursor-default focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
      :disabled="prev === null"
      :aria-label="prev ? `Show ${prev}` : 'No earlier year'"
      @click="emit('update:modelValue', prev)"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" /></svg>
    </button>
    <span class="min-w-[3.5rem] text-center font-bold text-gray-900 tabular-nums" aria-live="polite">{{ modelValue }}</span>
    <button
      type="button"
      class="w-9 h-9 flex items-center justify-center rounded-r-xl text-gray-500 hover:bg-gray-50 hover:text-gray-900 disabled:text-gray-200 disabled:hover:bg-transparent cursor-pointer disabled:cursor-default focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
      :disabled="next === null"
      :aria-label="next ? `Show ${next}` : 'No later year'"
      @click="emit('update:modelValue', next)"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" /></svg>
    </button>
  </div>
</template>
