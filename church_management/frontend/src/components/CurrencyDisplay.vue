<script setup>
import { computed } from "vue";

const props = defineProps({
  value: { type: Number, default: 0 },
  currency: { type: String, default: "PHP" },
  colored: { type: Boolean, default: false },
  size: { type: String, default: "sm" }, // xs | sm | lg
  weight: { type: String, default: "" }, // "" | bold
});

const formatted = computed(() => {
  return new Intl.NumberFormat("en-PH", {
    style: "currency",
    currency: props.currency,
    minimumFractionDigits: 2,
  }).format(props.value || 0);
});

const colorClass = computed(() => {
  if (!props.colored) return "text-gray-900";
  return props.value >= 0 ? "text-green-600" : "text-red-600";
});

const sizeClass = computed(() => {
  if (props.size === "lg") return "text-xl font-black";
  if (props.size === "xs") return props.weight === "bold" ? "text-[11px] font-bold" : "text-[11px] font-medium";
  return props.weight === "bold" ? "text-sm font-bold" : "text-sm font-semibold";
});
</script>

<template>
  <span :class="[colorClass, sizeClass]">{{ formatted }}</span>
</template>
