<script setup>
import { computed } from "vue";

const props = defineProps({
  id: { type: String, default: "" },
  name: { type: String, default: "" },
  size: { type: Number, default: 32 },
  ring: { type: String, default: "" },
});

const COLORS = [
  "from-rose-400 to-rose-600",
  "from-brand-400 to-brand-600",
  "from-violet-400 to-violet-600",
  "from-amber-400 to-amber-600",
  "from-emerald-400 to-emerald-600",
  "from-indigo-400 to-indigo-600",
  "from-fuchsia-400 to-fuchsia-600",
  "from-sky-400 to-sky-600",
];

function hash(s) {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
  return Math.abs(h);
}

const color = computed(() => COLORS[hash(props.id || props.name || "x") % COLORS.length]);
const initials = computed(() => {
  const n = (props.name || props.id || "?").trim();
  return n.split(/\s+/).map(p => p[0]).slice(0, 2).join("").toUpperCase();
});
const fontSize = computed(() => Math.max(9, Math.round(props.size * 0.36)));
</script>

<template>
  <div
    class="rounded-full bg-gradient-to-br text-white flex items-center justify-center font-bold shrink-0"
    :class="[color, ring]"
    :style="{ width: size + 'px', height: size + 'px', fontSize: fontSize + 'px' }"
  >{{ initials }}</div>
</template>
