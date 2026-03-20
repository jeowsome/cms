<script setup>
import { computed } from "vue";

const props = defineProps({
  status: { type: String, required: true },
});

const statusConfig = {
  Draft: { bg: "bg-gray-100", text: "text-gray-700", dot: "bg-gray-400" },
  Submitted: { bg: "bg-blue-50", text: "text-blue-700", dot: "bg-blue-400" },
  Cancelled: { bg: "bg-red-50", text: "text-red-700", dot: "bg-red-400" },
};

const config = computed(() => statusConfig[props.status] || statusConfig.Draft);
</script>

<template>
  <span
    class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium"
    :class="[config.bg, config.text]"
  >
    <span class="w-1.5 h-1.5 rounded-full" :class="config.dot" />
    {{ status === "Submitted" ? "Submitted" : status }}
  </span>
</template>
