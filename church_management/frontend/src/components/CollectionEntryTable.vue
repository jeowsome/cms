<script setup>
import { computed, nextTick, ref } from "vue";
import CurrencyDisplay from "@/components/CurrencyDisplay.vue";

/**
 * Fast keyboard-first entry table for tithes / offering / mission rows.
 * Flow: type envelope # → Tab → amount → Tab → new row is created and the
 * cursor lands on its envelope field. Member names resolve instantly from
 * the cached member map. Account selects are skipped by Tab (mouse only).
 */
const props = defineProps({
  rows: { type: Array, required: true },
  membersMap: { type: Object, required: true }, // Map: uppercased envelope → member
  title: { type: String, required: true },
  disabled: { type: Boolean, default: false },
  accent: { type: String, default: "brand" }, // brand | violet | teal
});
const emit = defineEmits(["dirty", "create-member"]);

const envelopeEls = ref([]);
const amountEls = ref([]);

const ACCENTS = {
  brand: { chip: "bg-brand-50 text-brand-700 border-brand-100", dot: "bg-brand-500" },
  violet: { chip: "bg-violet-50 text-violet-700 border-violet-100", dot: "bg-violet-500" },
  teal: { chip: "bg-teal-50 text-teal-700 border-teal-100", dot: "bg-teal-500" },
};
const accentCls = computed(() => ACCENTS[props.accent] || ACCENTS.brand);

function lookup(envelope) {
  if (!envelope) return null;
  return props.membersMap.get(String(envelope).trim().toUpperCase()) || null;
}

function memberFor(row) {
  return lookup(row.number);
}

function newRow() {
  return { number: "", first_name: "", last_name: "", amount: null, account_type: "Cash" };
}

function addRow(focus = true) {
  props.rows.push(newRow());
  emit("dirty");
  if (focus) {
    nextTick(() => envelopeEls.value[props.rows.length - 1]?.focus());
  }
}

function removeRow(idx) {
  props.rows.splice(idx, 1);
  emit("dirty");
}

function onEnvelopeInput(row, e) {
  row.number = e.target.value.trim();
  const member = lookup(row.number);
  row.first_name = member?.firstname || "";
  row.last_name = member?.lastname || "";
  emit("dirty");
}

function onEnvelopeEnter(idx) {
  amountEls.value[idx]?.focus();
}

function onAmountInput(row, e) {
  const v = parseFloat(e.target.value);
  row.amount = Number.isFinite(v) ? v : null;
  emit("dirty");
}

// Tab or Enter on the amount of the LAST row spawns the next row.
// Tab on earlier rows falls through to the next row's envelope naturally
// (selects and delete buttons are tabindex -1).
function onAmountTab(idx, e) {
  if (e.shiftKey) return;
  if (idx === props.rows.length - 1) {
    e.preventDefault();
    addRow();
  }
}

function onAmountEnter(idx, e) {
  e.preventDefault();
  if (idx === props.rows.length - 1) addRow();
  else envelopeEls.value[idx + 1]?.focus();
}

const stats = computed(() => {
  let cash = 0, cls = 0, cashCount = 0, clsCount = 0;
  for (const row of props.rows) {
    const amt = row.amount || 0;
    if (row.account_type === "Cash") {
      cash += amt;
      cashCount++;
    } else {
      cls += amt;
      clsCount++;
    }
  }
  return { cash, cls, cashCount, clsCount, total: cash + cls };
});

defineExpose({ addRow });
</script>

<template>
  <div class="max-w-3xl">
    <!-- Column headers (desktop) -->
    <div class="hidden sm:flex items-center gap-2 px-1 pb-2 text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
      <span class="w-8 text-center shrink-0">#</span>
      <span class="w-24 text-center shrink-0">Envelope</span>
      <span class="flex-1 min-w-0">Member</span>
      <span class="w-28 text-right shrink-0">Amount</span>
      <span class="w-24 shrink-0">Type</span>
      <span class="w-8 shrink-0" />
    </div>

    <!-- Rows -->
    <div class="space-y-1.5">
      <div v-for="(row, idx) in rows" :key="idx" class="flex items-start sm:items-center gap-2">
        <span class="w-6 sm:w-8 text-center text-xs text-gray-400 font-semibold tabular shrink-0 pt-3 sm:pt-0">{{ idx + 1 }}</span>

        <!-- Envelope number -->
        <input
          :ref="(el) => (envelopeEls[idx] = el)"
          type="text"
          inputmode="numeric"
          :value="row.number"
          :disabled="disabled"
          placeholder="No."
          autocomplete="off"
          class="cm-field !h-10 !w-20 sm:!w-24 text-center tabular font-semibold shrink-0"
          :class="row.number && !memberFor(row) ? '!border-amber-300 !bg-amber-50/50' : ''"
          @input="onEnvelopeInput(row, $event)"
          @keydown.enter.prevent="onEnvelopeEnter(idx)"
        />

        <!-- Member + (mobile) amount/type stacked -->
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-1.5 min-w-0 h-10 sm:h-auto">
            <template v-if="memberFor(row)">
              <span class="w-1.5 h-1.5 rounded-full shrink-0" :class="accentCls.dot" />
              <span class="text-sm font-medium text-gray-800 truncate">
                {{ memberFor(row).firstname }} {{ memberFor(row).lastname }}
              </span>
            </template>
            <template v-else-if="row.number">
              <svg class="w-3.5 h-3.5 text-amber-500 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m0 3h.008v.008H12v-.008zM21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span class="text-xs text-amber-600 font-medium truncate">Unknown envelope</span>
              <button
                v-if="!disabled"
                type="button"
                tabindex="-1"
                class="inline-flex items-center gap-1 shrink-0 px-2 py-1 rounded-lg text-[11px] font-bold text-brand-700 bg-brand-50 border border-brand-100 hover:bg-brand-100 transition-colors"
                :title="`Register a new church member with envelope ${row.number}`"
                @click="emit('create-member', row)"
              >
                <svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                </svg>
                New member
              </button>
            </template>
            <span v-else class="text-xs text-gray-300 italic hidden sm:inline">—</span>
          </div>
          <!-- Mobile-only amount + type inline -->
          <div class="flex sm:hidden items-center gap-2 mt-1">
            <input
              type="number"
              step="0.01"
              min="0"
              :value="row.amount ?? ''"
              :disabled="disabled"
              placeholder="0.00"
              class="cm-field !h-9 flex-1 text-right tabular"
              @input="onAmountInput(row, $event)"
            />
            <select
              :value="row.account_type"
              :disabled="disabled"
              tabindex="-1"
              class="cm-field cm-select !h-9 !w-24 text-xs shrink-0"
              @change="row.account_type = $event.target.value; emit('dirty')"
            >
              <option>Cash</option>
              <option>GCash</option>
              <option>Bank</option>
            </select>
          </div>
        </div>

        <!-- Amount (desktop) -->
        <input
          :ref="(el) => (amountEls[idx] = el)"
          type="number"
          step="0.01"
          min="0"
          :value="row.amount ?? ''"
          :disabled="disabled"
          placeholder="0.00"
          class="cm-field !h-10 !w-28 text-right tabular hidden sm:block shrink-0"
          @input="onAmountInput(row, $event)"
          @focus="$event.target.select()"
          @keydown.tab="onAmountTab(idx, $event)"
          @keydown.enter="onAmountEnter(idx, $event)"
        />

        <!-- Account type (desktop, mouse-only in the tab flow) -->
        <select
          :value="row.account_type"
          :disabled="disabled"
          tabindex="-1"
          title="Payment channel — Tab skips this; click to change. Defaults to Cash."
          class="cm-field cm-select !h-10 !w-24 text-xs hidden sm:block shrink-0"
          :class="row.account_type !== 'Cash' ? '!border-sky-300 !bg-sky-50/50 font-semibold text-sky-800' : ''"
          @change="row.account_type = $event.target.value; emit('dirty')"
        >
          <option>Cash</option>
          <option>GCash</option>
          <option>Bank</option>
        </select>

        <!-- Delete -->
        <button
          v-if="!disabled"
          type="button"
          tabindex="-1"
          class="w-8 h-8 rounded-lg flex items-center justify-center text-gray-300 hover:text-red-600 hover:bg-red-50 transition-colors shrink-0"
          :aria-label="`Remove row ${idx + 1}`"
          @click="removeRow(idx)"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
          </svg>
        </button>
        <span v-else class="w-8 shrink-0" />
      </div>
    </div>

    <!-- Empty state -->
    <div v-if="!rows.length" class="py-8 text-center">
      <p class="text-sm text-gray-400">No {{ title.toLowerCase() }} entries yet</p>
    </div>

    <!-- Footer: add row + totals -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mt-4 pt-3 border-t border-gray-100">
      <button
        v-if="!disabled"
        type="button"
        class="inline-flex items-center gap-1.5 text-sm font-semibold text-brand-600 hover:text-brand-700 transition-colors self-start"
        @click="addRow()"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
        </svg>
        Add row
        <span class="hidden sm:inline text-[11px] font-medium text-gray-400 ml-1">or press Tab after an amount</span>
      </button>
      <span v-else />

      <div class="flex items-center gap-2 flex-wrap">
        <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border bg-gray-50 text-gray-600 border-gray-200">
          Cash · {{ stats.cashCount }}
          <CurrencyDisplay :value="stats.cash" size="xs" weight="bold" />
        </span>
        <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border bg-sky-50 text-sky-700 border-sky-100">
          Cashless · {{ stats.clsCount }}
          <CurrencyDisplay :value="stats.cls" size="xs" weight="bold" />
        </span>
        <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold border" :class="accentCls.chip">
          Total
          <CurrencyDisplay :value="stats.total" size="xs" weight="bold" />
        </span>
      </div>
    </div>
  </div>
</template>
