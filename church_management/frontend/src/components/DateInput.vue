<script setup>
import { ref, watch } from "vue";

const props = defineProps({
  modelValue: { type: String, default: "" },   // ISO yyyy-mm-dd
  placeholder: { type: String, default: "mm/dd/yyyy" },
});
const emit = defineEmits(["update:modelValue"]);

const text = ref(toDisplay(props.modelValue));
const picker = ref(null);

function toDisplay(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || "");
  return m ? `${m[2]}/${m[3]}/${m[1]}` : "";
}
function toIso(s) {
  const m = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(s || "");
  if (!m) return "";
  const [_, mm, dd, yyyy] = m;
  const month = +mm, day = +dd, year = +yyyy;
  if (month < 1 || month > 12 || day < 1 || day > 31 || year < 1900) return "";
  return `${yyyy}-${mm}-${dd}`;
}

function onInput(e) {
  // Auto-insert slashes as the user types digits
  let raw = e.target.value.replace(/\D/g, "").slice(0, 8);
  let out = raw;
  if (raw.length > 4) out = `${raw.slice(0, 2)}/${raw.slice(2, 4)}/${raw.slice(4)}`;
  else if (raw.length > 2) out = `${raw.slice(0, 2)}/${raw.slice(2)}`;
  text.value = out;
  emit("update:modelValue", toIso(out));
}

function onPickerChange(e) {
  const iso = e.target.value;
  text.value = toDisplay(iso);
  emit("update:modelValue", iso);
}

function openPicker() {
  if (picker.value?.showPicker) {
    try { picker.value.showPicker(); } catch {}
  } else if (picker.value) {
    picker.value.focus();
  }
}

watch(() => props.modelValue, (v) => {
  const d = toDisplay(v);
  if (d !== text.value) text.value = d;
});
</script>

<template>
  <div class="relative">
    <input
      type="text"
      inputmode="numeric"
      maxlength="10"
      :value="text"
      :placeholder="placeholder"
      @input="onInput"
      class="w-full px-4 py-2.5 pr-11 bg-ink-50 border border-ink-200 rounded-xl text-sm focus:bg-white focus:border-rose-500 focus:ring-2 focus:ring-rose-100 outline-none tabular-nums"
    />
    <button
      type="button"
      @click="openPicker"
      tabindex="-1"
      class="absolute right-1 top-1/2 -translate-y-1/2 w-9 h-9 rounded-lg flex items-center justify-center text-ink-400 hover:text-rose-700 hover:bg-rose-50 transition-colors"
      aria-label="Open date picker"
    >
      <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5" />
      </svg>
    </button>
    <input
      ref="picker"
      type="date"
      :value="modelValue"
      @change="onPickerChange"
      class="absolute right-1 top-1/2 -translate-y-1/2 w-9 h-9 opacity-0 pointer-events-none"
      tabindex="-1"
      aria-hidden="true"
    />
  </div>
</template>
