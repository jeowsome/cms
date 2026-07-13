<script setup>
import { computed, ref } from "vue";
import { evaluateExpression, isExpression } from "@/utils/mathExpr";

/**
 * Currency input that accepts math expressions: "5+5", "20*3+(100/2)".
 * Enter or blur evaluates the expression into a plain amount — built for
 * counting mixed denominations without reaching for a calculator.
 */
const props = defineProps({
  modelValue: { type: Number, default: 0 },
  placeholder: { type: String, default: "0.00" },
  disabled: { type: Boolean, default: false },
});
const emit = defineEmits(["update:modelValue"]);

const text = ref("");
const focused = ref(false);
const invalid = ref(false);
const justCalculated = ref(false);

const peso = new Intl.NumberFormat("en-PH", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function format(v) {
  return v ? peso.format(v) : "";
}

// While editing, show the raw text being typed; otherwise always derive the
// display from modelValue so late-loaded documents render their values.
const displayed = computed(() =>
  focused.value || invalid.value ? text.value : format(props.modelValue)
);

// Live preview while an expression is being typed ("5+5" → "= 10.00")
const preview = computed(() => {
  if (!focused.value || !isExpression(text.value)) return null;
  const result = evaluateExpression(text.value);
  return result === null ? null : peso.format(result);
});

const showInvalid = computed(() => invalid.value && !!text.value);

function onFocus(e) {
  focused.value = true;
  invalid.value = false;
  // Edit the raw number, not the formatted string
  const raw = String(props.modelValue || "");
  text.value = props.modelValue ? raw : "";
  requestAnimationFrame(() => e.target.select());
}

function commit() {
  const result = evaluateExpression(text.value);
  if (text.value && result === null) {
    invalid.value = true;
    return false;
  }
  invalid.value = false;
  const value = result === null ? 0 : Math.round(result * 100) / 100;
  if (isExpression(text.value)) {
    justCalculated.value = true;
    setTimeout(() => (justCalculated.value = false), 900);
  }
  emit("update:modelValue", value);
  text.value = String(value || "");
  return true;
}

function onEnter(e) {
  if (commit()) e.target.select();
}

function onBlur() {
  focused.value = false;
  // On failure `invalid` stays set, keeping the bad expression visible to fix
  commit();
}
</script>

<template>
  <div class="relative group/math">
    <span class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm text-gray-400">₱</span>
    <input
      type="text"
      inputmode="decimal"
      :value="displayed"
      :placeholder="placeholder"
      :disabled="disabled"
      autocomplete="off"
      spellcheck="false"
      class="cm-field pl-7 pr-9 text-right tabular"
      :class="[
        showInvalid ? '!border-red-300 !ring-2 !ring-red-100' : '',
        justCalculated ? '!border-green-400 !ring-2 !ring-green-100' : '',
      ]"
      @focus="onFocus"
      @input="text = $event.target.value; invalid = false"
      @keydown.enter.prevent="onEnter"
      @blur="onBlur"
    />

    <!-- Calculator affordance + tooltip -->
    <span
      class="absolute right-2.5 top-1/2 -translate-y-1/2 transition-colors"
      :class="justCalculated ? 'text-green-500' : 'text-gray-300 group-hover/math:text-gray-400'"
    >
      <svg v-if="!justCalculated" class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 15.75V18m-7.5-6.75h.008v.008H8.25v-.008zm0 2.25h.008v.008H8.25V13.5zm0 2.25h.008v.008H8.25v-.008zm0 2.25h.008v.008H8.25V18zm2.498-6.75h.007v.008h-.007v-.008zm0 2.25h.007v.008h-.007V13.5zm0 2.25h.007v.008h-.007v-.008zm0 2.25h.007v.008h-.007V18zm2.504-6.75h.008v.008h-.008v-.008zm0 2.25h.008v.008h-.008V13.5zm0 2.25h.008v.008h-.008v-.008zm2.498-4.5h.008v.008h-.008v-.008zm0 2.25h.008v.008h-.008V13.5zM8.25 6h7.5v2.25h-7.5V6zM12 2.25c-1.892 0-3.758.11-5.593.322C5.307 2.7 4.5 3.65 4.5 4.757V19.5a2.25 2.25 0 002.25 2.25h10.5a2.25 2.25 0 002.25-2.25V4.757c0-1.108-.806-2.057-1.907-2.185A48.507 48.507 0 0012 2.25z" />
      </svg>
      <svg v-else class="w-4 h-4 anim-pop" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
      </svg>
    </span>

    <!-- Hover/focus tooltip (desktop) -->
    <span
      class="pointer-events-none absolute left-1/2 -translate-x-1/2 bottom-[calc(100%+6px)] z-30 hidden sm:block whitespace-nowrap rounded-lg bg-gray-900/95 px-3 py-1.5 text-[11px] font-medium text-white shadow-xl opacity-0 invisible group-hover/math:visible group-hover/math:opacity-100 transition-all duration-150"
      :class="focused ? '!invisible !opacity-0' : ''"
      role="presentation"
    >
      Type math like <span class="font-bold text-amber-300">5+5</span> or <span class="font-bold text-amber-300">(20*4)+100</span>, press Enter
      <span class="absolute -bottom-1 left-1/2 -translate-x-1/2 w-2 h-2 rotate-45 bg-gray-900/95" />
    </span>

    <!-- Live "= result" preview while typing an expression -->
    <span
      v-if="preview"
      class="pointer-events-none absolute right-0 top-[calc(100%+4px)] z-20 rounded-lg bg-brand-600 px-2.5 py-1 text-xs font-bold text-white shadow-lg anim-fadein tabular"
    >
      = {{ preview }}
    </span>
    <span
      v-else-if="showInvalid"
      class="pointer-events-none absolute right-0 top-[calc(100%+4px)] z-20 rounded-lg bg-red-600 px-2.5 py-1 text-[11px] font-semibold text-white shadow-lg anim-fadein"
    >
      Can't calculate — check the expression
    </span>
  </div>
</template>
