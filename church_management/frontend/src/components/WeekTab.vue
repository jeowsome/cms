<script setup>
import { computed, ref, watch } from "vue";
import CurrencyDisplay from "@/components/CurrencyDisplay.vue";
import AppButton from "@/components/AppButton.vue";
import AddExpenseModal from "@/components/AddExpenseModal.vue";
import AddAllowanceModal from "@/components/AddAllowanceModal.vue";
import ItemDetailModal from "@/components/ItemDetailModal.vue";
import ClaimModal from "@/components/ClaimModal.vue";

const props = defineProps({
  weekNum: { type: Number, required: true },
  items: { type: Array, default: () => [] },
  expenses: { type: Array, default: () => [] },
  label: { type: String, default: "" },
  disbursementName: { type: String, default: "" },
  sundayIso: { type: String, default: "" },
  sundayLabel: { type: String, default: "" },
  overdue: { type: Boolean, default: false },
});

const emit = defineEmits(["claimed"]);

const detailItem = ref(null);
const claimItem = ref(null);
const claimItems = ref(null); // for bulk
const isAddingExpense = ref(false);
const isAddingAllowance = ref(false);
const showFabOptions = ref(false);
const selectedNames = ref(new Set());

const sectionTitle = (suffix) => {
  const prefix = props.label || `Week ${props.weekNum}`;
  return `${prefix} — ${suffix}`;
};

function sorted(arr) {
  return [...arr].sort((a, b) => {
    if (a.status === "Unclaimed" && b.status !== "Unclaimed") return -1;
    if (a.status !== "Unclaimed" && b.status === "Unclaimed") return 1;
    return 0;
  });
}

const sortedItems = computed(() => sorted(props.items));
const sortedExpenses = computed(() => sorted(props.expenses));

const allUnclaimed = computed(() =>
  [...props.items, ...props.expenses].filter((i) => i.status !== "Claimed")
);
const selectedCount = computed(() => selectedNames.value.size);
const selectedRows = computed(() =>
  allUnclaimed.value.filter((i) => selectedNames.value.has(i.name))
);

watch(
  () => props.disbursementName + ":" + props.weekNum,
  () => selectedNames.value = new Set()
);

function toggleSelect(item, ev) {
  ev?.stopPropagation();
  const next = new Set(selectedNames.value);
  if (next.has(item.name)) next.delete(item.name);
  else next.add(item.name);
  selectedNames.value = next;
}

function isOverdueRow(item) {
  const claimed =
    item.status === "Claimed" || (!!item.received_by && !!item.received_date);
  return props.overdue && !claimed;
}

function openDetail(item) { detailItem.value = item; }
function openClaim(item, event) { event?.stopPropagation(); claimItem.value = item; }
function openClaimFromDetail(item) {
  detailItem.value = null;
  setTimeout(() => { claimItem.value = item; }, 200);
}
function openBulkClaim() {
  if (!selectedRows.value.length) return;
  claimItems.value = selectedRows.value;
}
function onClaimed() {
  claimItem.value = null;
  claimItems.value = null;
  selectedNames.value = new Set();
  emit("claimed");
}
</script>

<template>
  <div class="space-y-5">
    <!-- Sunday header + bulk toolbar -->
    <div v-if="sundayLabel || selectedCount" class="flex items-center justify-between gap-3 -mt-1 mb-1">
      <div v-if="sundayLabel" class="flex items-center gap-2">
        <span
          class="inline-flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full"
          :class="overdue ? 'bg-red-50 text-red-700 border border-red-200' : 'bg-brand-50 text-brand-700 border border-brand-100'"
        >
          <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M8 7V3m8 4V3M3 11h18M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
          </svg>
          {{ sundayLabel }}
          <span v-if="overdue" class="ml-1 text-[10px] font-black">· OVERDUE</span>
        </span>
      </div>
      <div v-if="selectedCount" class="flex items-center gap-2">
        <span class="text-[11px] font-semibold text-gray-500">{{ selectedCount }} selected</span>
        <button
          @click="selectedNames = new Set()"
          class="text-[11px] font-semibold text-gray-500 hover:text-gray-700 px-2 py-1 rounded"
        >Clear</button>
        <button
          @click="openBulkClaim"
          class="text-[11px] font-bold text-white bg-brand-600 hover:bg-brand-700 px-3 py-1.5 rounded-lg uppercase tracking-wider"
        >Claim {{ selectedCount }}</button>
      </div>
    </div>

    <!-- Disbursement Items -->
    <div>
      <div class="flex items-center justify-between group mb-2.5">
        <h3 class="text-[11px] font-black text-gray-400 uppercase tracking-widest pl-1">
          {{ sectionTitle("Allowances & Disbursements") }}
        </h3>
        <button
          @click="isAddingAllowance = true"
          class="flex items-center gap-1 text-[10px] font-bold text-brand-600 uppercase tracking-wider bg-brand-50 hover:bg-brand-100 px-2.5 py-1 rounded transition-all sm:opacity-0 sm:group-hover:opacity-100"
        >
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 4v16m8-8H4"/></svg>
          Add
        </button>
      </div>

      <div v-if="sortedItems.length === 0" class="py-8 text-center text-sm text-gray-400 bg-gray-50/50 rounded-xl border border-dashed border-gray-200">
        No items for this period.
      </div>

      <!-- Mobile cards -->
      <div v-if="sortedItems.length" class="sm:hidden space-y-2.5">
        <div
          v-for="item in sortedItems"
          :key="item.name"
          class="bg-white border rounded-xl p-3.5 shadow-sm active:bg-gray-50 active:scale-[0.98] transition-all cursor-pointer relative"
          :class="[
            selectedNames.has(item.name) ? 'border-brand-400 ring-2 ring-brand-200' : 'border-gray-100',
            isOverdueRow(item) ? 'overdue-blink' : ''
          ]"
          @click="openDetail(item)"
        >
          <div class="flex items-start gap-3">
            <input
              v-if="item.status !== 'Claimed'"
              type="checkbox"
              :checked="selectedNames.has(item.name)"
              @click.stop="toggleSelect(item, $event)"
              class="mt-1 w-4 h-4 accent-brand-600 cursor-pointer"
            />
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2">
                <p class="text-sm font-bold text-gray-900 truncate">{{ item.worker || "—" }}</p>
                <div v-if="item.status === 'Claimed'" class="flex items-center gap-1 px-1.5 py-0.5 bg-green-50 rounded-full">
                  <svg class="w-3 h-3 text-green-600 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M4.5 12.75l6 6 9-13.5" />
                  </svg>
                  <span class="text-[9px] font-black text-green-700 uppercase">Claimed</span>
                </div>
              </div>
              <div class="flex flex-col gap-0.5 mt-0.5">
                <p class="text-xs text-gray-500 font-medium">{{ item.purpose || "No purpose" }}</p>
                <p class="text-[10px] text-gray-400 font-mono">{{ item.source || "No source" }}</p>
              </div>
            </div>
            <div class="flex flex-col items-end gap-2 shrink-0 ml-1">
              <div class="flex flex-col items-end leading-none">
                <span v-if="item.amount_edited" class="text-[10px] text-gray-400 line-through">
                  <CurrencyDisplay :value="item.original_amount" size="xs" />
                </span>
                <CurrencyDisplay :value="item.amount" size="sm" weight="bold" />
              </div>
              <button
                v-if="item.status !== 'Claimed'"
                class="px-3 py-1.5 text-[10px] font-bold text-brand-600 bg-brand-50 rounded-lg active:bg-brand-100 transition-colors uppercase tracking-wider border border-brand-100"
                @click="openClaim(item, $event)"
              >
                Claim
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Desktop table -->
      <div v-if="sortedItems.length" class="hidden sm:block overflow-x-auto bg-white border border-gray-100/80 rounded-2xl shadow-sm">
        <table class="min-w-full text-sm">
          <thead>
            <tr class="text-left text-[10px] text-gray-400 font-black uppercase tracking-widest border-b border-gray-100/80 bg-gray-50/50">
              <th class="py-3 pl-4 pr-2 rounded-tl-xl w-8"></th>
              <th class="py-3 pr-4 w-[22%]">Worker</th>
              <th class="py-3 pr-4 w-[22%]">Purpose</th>
              <th class="py-3 pr-4 w-[15%]">Source</th>
              <th class="py-3 pr-4 text-right w-[18%]">Amount</th>
              <th class="py-3 text-center w-[10%]">Status</th>
              <th class="py-3 rounded-tr-xl w-16"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50">
            <tr
              v-for="item in sortedItems"
              :key="item.name"
              class="group text-gray-600 hover:bg-gray-50 transition-colors cursor-pointer"
              :class="[
                selectedNames.has(item.name) ? 'bg-brand-50/40' : '',
                isOverdueRow(item) ? 'overdue-blink' : ''
              ]"
              @click="openDetail(item)"
            >
              <td class="py-3.5 pl-4 pr-2">
                <input
                  v-if="item.status !== 'Claimed'"
                  type="checkbox"
                  :checked="selectedNames.has(item.name)"
                  @click.stop="toggleSelect(item, $event)"
                  class="w-4 h-4 accent-brand-600 cursor-pointer"
                />
              </td>
              <td class="py-3.5 pr-4 font-bold text-gray-900">{{ item.worker || "—" }}</td>
              <td class="py-3.5 pr-4 font-medium">{{ item.purpose || "—" }}</td>
              <td class="py-3.5 pr-4 text-[11px] text-gray-400 font-mono">{{ item.source || "—" }}</td>
              <td class="py-3.5 pr-4 text-right">
                <div class="flex flex-col items-end leading-tight">
                  <span v-if="item.amount_edited" class="text-[11px] text-gray-400 line-through">
                    <CurrencyDisplay :value="item.original_amount" size="xs" />
                  </span>
                  <CurrencyDisplay :value="item.amount" />
                </div>
              </td>
              <td class="py-2.5 text-center">
                <svg v-if="item.status === 'Claimed'" class="w-5 h-5 text-green-500 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
                <span v-else class="inline-block w-2 h-2 rounded-full bg-gray-300" />
              </td>
              <td class="py-2.5">
                <button
                  v-if="item.status !== 'Claimed'"
                  class="opacity-0 group-hover:opacity-100 px-2.5 py-1 text-[11px] font-semibold text-brand-600 bg-brand-50 hover:bg-brand-100 rounded-lg transition-all"
                  @click="openClaim(item, $event)"
                >
                  Claim
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="mt-8">
      <div class="flex items-center justify-between group mb-2.5">
        <h3 class="text-[11px] font-black text-gray-400 uppercase tracking-widest pl-1">
          {{ sectionTitle("Expenses") }}
        </h3>
        <button
          @click="isAddingExpense = true"
          class="flex items-center gap-1 text-[10px] font-bold text-brand-600 uppercase tracking-wider bg-brand-50 hover:bg-brand-100 px-2.5 py-1 rounded transition-all sm:opacity-0 sm:group-hover:opacity-100"
        >
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 4v16m8-8H4"/></svg>
          Add
        </button>
      </div>

      <div v-if="sortedExpenses.length === 0" class="py-8 text-center text-sm text-gray-400 bg-gray-50/50 rounded-xl border border-dashed border-gray-200">
        No expense items for this period.
      </div>

      <!-- Mobile cards -->
      <div v-if="sortedExpenses.length" class="sm:hidden space-y-2.5">
        <div
          v-for="item in sortedExpenses"
          :key="item.name"
          class="bg-white border rounded-xl p-3.5 shadow-sm active:bg-gray-50 active:scale-[0.98] transition-all cursor-pointer"
          :class="[
            selectedNames.has(item.name) ? 'border-brand-400 ring-2 ring-brand-200' : 'border-gray-100',
            isOverdueRow(item) ? 'overdue-blink' : ''
          ]"
          @click="openDetail(item)"
        >
          <div class="flex items-start gap-3">
            <input
              v-if="item.status !== 'Claimed'"
              type="checkbox"
              :checked="selectedNames.has(item.name)"
              @click.stop="toggleSelect(item, $event)"
              class="mt-1 w-4 h-4 accent-brand-600 cursor-pointer"
            />
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2">
                <p class="text-sm font-bold text-gray-900 truncate">{{ item.description || "—" }}</p>
                <div v-if="item.status === 'Claimed'" class="flex items-center gap-1 px-1.5 py-0.5 bg-green-50 rounded-full">
                  <svg class="w-3 h-3 text-green-600 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M4.5 12.75l6 6 9-13.5" />
                  </svg>
                  <span class="text-[9px] font-black text-green-700 uppercase">Claimed</span>
                </div>
              </div>
              <div class="flex flex-col gap-0.5 mt-0.5">
                <p class="text-xs text-gray-500 font-medium">{{ item.purpose || "No purpose" }}</p>
                <p class="text-[10px] text-gray-400 font-mono">{{ item.source || "No source" }}</p>
              </div>
            </div>
            <div class="flex flex-col items-end gap-2 shrink-0 ml-1">
              <div class="flex flex-col items-end leading-none">
                <span v-if="item.amount_edited" class="text-[10px] text-gray-400 line-through">
                  <CurrencyDisplay :value="item.original_amount" size="xs" />
                </span>
                <CurrencyDisplay :value="item.amount" size="sm" weight="bold" />
              </div>
              <button
                v-if="item.status !== 'Claimed'"
                class="px-3 py-1.5 text-[10px] font-bold text-brand-600 bg-brand-50 rounded-lg active:bg-brand-100 transition-colors uppercase tracking-wider border border-brand-100"
                @click="openClaim(item, $event)"
              >
                Claim
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Desktop table -->
      <div v-if="sortedExpenses.length" class="hidden sm:block overflow-x-auto bg-white border border-gray-100/80 rounded-2xl shadow-sm">
        <table class="min-w-full text-sm">
          <thead>
            <tr class="text-left text-[10px] text-gray-400 font-black uppercase tracking-widest border-b border-gray-100/80 bg-gray-50/50">
              <th class="py-3 pl-4 pr-2 rounded-tl-xl w-8"></th>
              <th class="py-3 pr-4 w-[22%]">Description</th>
              <th class="py-3 pr-4 w-[22%]">Purpose</th>
              <th class="py-3 pr-4 w-[15%]">Source</th>
              <th class="py-3 pr-4 text-right w-[18%]">Amount</th>
              <th class="py-3 text-center w-[10%]">Status</th>
              <th class="py-3 rounded-tr-xl w-16"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50">
            <tr
               v-for="item in sortedExpenses"
              :key="item.name"
              class="group text-gray-600 hover:bg-gray-50 transition-colors cursor-pointer"
              :class="[
                selectedNames.has(item.name) ? 'bg-brand-50/40' : '',
                isOverdueRow(item) ? 'overdue-blink' : ''
              ]"
              @click="openDetail(item)"
            >
              <td class="py-3.5 pl-4 pr-2">
                <input
                  v-if="item.status !== 'Claimed'"
                  type="checkbox"
                  :checked="selectedNames.has(item.name)"
                  @click.stop="toggleSelect(item, $event)"
                  class="w-4 h-4 accent-brand-600 cursor-pointer"
                />
              </td>
              <td class="py-3.5 pr-4 font-bold text-gray-900">{{ item.description || "—" }}</td>
              <td class="py-3.5 pr-4 font-medium">{{ item.purpose || "—" }}</td>
              <td class="py-3.5 pr-4 text-[11px] text-gray-400 font-mono">{{ item.source || "—" }}</td>
              <td class="py-3.5 pr-4 text-right">
                <div class="flex flex-col items-end leading-tight">
                  <span v-if="item.amount_edited" class="text-[11px] text-gray-400 line-through">
                    <CurrencyDisplay :value="item.original_amount" size="xs" />
                  </span>
                  <CurrencyDisplay :value="item.amount" />
                </div>
              </td>
              <td class="py-2.5 text-center">
                <svg v-if="item.status === 'Claimed'" class="w-5 h-5 text-green-500 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
                <span v-else class="inline-block w-2 h-2 rounded-full bg-gray-300" />
              </td>
              <td class="py-2.5">
                <button
                  v-if="item.status !== 'Claimed'"
                  class="opacity-0 group-hover:opacity-100 px-2.5 py-1 text-[11px] font-semibold text-brand-600 bg-brand-50 hover:bg-brand-100 rounded-lg transition-all"
                  @click="openClaim(item, $event)"
                >
                  Claim
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Mobile Floating Action Button -->
    <div class="sm:hidden fixed bottom-20 right-6 z-[60] flex flex-col items-end gap-3 pointer-events-none">
      <div v-if="showFabOptions" class="flex flex-col items-end gap-3 mb-2 animate-in fade-in slide-in-from-bottom-4 duration-200 pointer-events-auto">
        <button
          @click="isAddingAllowance = true; showFabOptions = false"
          class="flex items-center gap-2 bg-white text-brand-600 px-4 py-2.5 rounded-full shadow-lg border border-brand-100 text-sm font-bold active:scale-95 transition-all"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 4v16m8-8H4"/></svg>
          Add Allowance
        </button>
        <button
          @click="isAddingExpense = true; showFabOptions = false"
          class="flex items-center gap-2 bg-white text-brand-600 px-4 py-2.5 rounded-full shadow-lg border border-brand-100 text-sm font-bold active:scale-95 transition-all"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 4v16m8-8H4"/></svg>
          Add Expense
        </button>
      </div>
      <button
        @click="showFabOptions = !showFabOptions"
        class="w-14 h-14 bg-brand-600 text-white rounded-full shadow-2xl flex items-center justify-center active:scale-90 active:bg-brand-700 transition-all pointer-events-auto"
      >
        <svg
          class="w-7 h-7 transition-transform duration-200"
          :class="showFabOptions ? 'rotate-45' : ''"
          fill="none" stroke="currentColor" viewBox="0 0 24 24"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M12 4v16m8-8H4" />
        </svg>
      </button>
    </div>

    <!-- Detail Modal -->
    <ItemDetailModal
      :item="detailItem"
      :disbursement-name="disbursementName"
      @close="detailItem = null"
      @claim="openClaimFromDetail"
      @updated="emit('claimed')"
    />

    <!-- Claim Modal (single or bulk) -->
    <ClaimModal
      :item="claimItem"
      :items="claimItems"
      :disbursement-name="disbursementName"
      :week-num="weekNum"
      :default-date="sundayIso"
      @close="claimItem = null; claimItems = null"
      @claimed="onClaimed"
    />

    <!-- Add Expense Modal -->
    <AddExpenseModal
      :is-open="isAddingExpense"
      :disbursement-name="disbursementName"
      :week-num="weekNum"
      :table-field="weekNum === 0 ? 'monthly_expense_items' : 'expense_item_week_' + weekNum"
      @close="isAddingExpense = false"
      @added="emit('claimed')"
    />

    <!-- Add Allowance Modal -->
    <AddAllowanceModal
      :is-open="isAddingAllowance"
      :disbursement-name="disbursementName"
      :week-num="weekNum"
      :table-field="weekNum === 0 ? 'monthly_disbursement_items' : 'disbursement_item_week_' + weekNum"
      @close="isAddingAllowance = false"
      @added="emit('claimed')"
    />
  </div>
</template>
