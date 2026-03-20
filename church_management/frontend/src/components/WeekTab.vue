<script setup>
import { computed, ref } from "vue";
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
});

const emit = defineEmits(["claimed"]);

const detailItem = ref(null);
const claimItem = ref(null);
const isAddingExpense = ref(false);
const isAddingAllowance = ref(false);

const sectionTitle = (suffix) => {
  const prefix = props.label || `Week ${props.weekNum}`;
  return `${prefix} — ${suffix}`;
};

// Sort: unclaimed first, then claimed
function sorted(arr) {
  return [...arr].sort((a, b) => {
    if (a.status === "Unclaimed" && b.status !== "Unclaimed") return -1;
    if (a.status !== "Unclaimed" && b.status === "Unclaimed") return 1;
    return 0;
  });
}

const sortedItems = computed(() => sorted(props.items));
const sortedExpenses = computed(() => sorted(props.expenses));

function openDetail(item) {
  detailItem.value = item;
}

function openClaim(item, event) {
  event?.stopPropagation();
  claimItem.value = item;
}

function openClaimFromDetail(item) {
  detailItem.value = null;
  setTimeout(() => {
    claimItem.value = item;
  }, 200);
}

function onClaimed() {
  claimItem.value = null;
  emit("claimed");
}
</script>

<template>
  <div class="space-y-5">
    <!-- Disbursement Items -->
    <div>
      <div class="flex items-center justify-between group mb-2.5">
        <h3 class="text-xs font-semibold text-gray-500 uppercase tracking-wider">
          {{ sectionTitle("Allowances & Disbursements") }}
        </h3>
        <button
          @click="isAddingAllowance = true"
          class="opacity-0 group-hover:opacity-100 flex items-center gap-1 text-[10px] font-bold text-brand-600 uppercase tracking-wider bg-brand-50 hover:bg-brand-100 px-2.5 py-1 rounded transition-all"
        >
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 4v16m8-8H4"/></svg>
          Add 
        </button>
      </div>

      <div v-if="sortedItems.length === 0" class="py-8 text-center text-sm text-gray-400">
        No items for this period.
      </div>

      <!-- Mobile cards -->
      <div v-if="sortedItems.length" class="sm:hidden space-y-2">
        <div
          v-for="item in sortedItems"
          :key="item.name"
          class="bg-gray-50 rounded-xl p-3.5 transition-all active:bg-gray-100 active:scale-[0.99] cursor-pointer"
          @click="openDetail(item)"
        >
          <div class="flex items-start justify-between">
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2">
                <p class="text-sm font-semibold text-gray-900 truncate">{{ item.worker || "—" }}</p>
                <svg v-if="item.status === 'Claimed'" class="w-4 h-4 text-green-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
              </div>
              <div class="flex flex-col gap-0.5">
                <p class="text-xs text-gray-500">{{ item.purpose || "No purpose" }}</p>
                <p class="text-[11px] text-gray-400 font-mono">{{ item.source || "No source" }}</p>
              </div>
            </div>
            <div class="flex items-center gap-2 shrink-0 ml-2">
              <CurrencyDisplay :value="item.amount" />
              <button
                v-if="item.status !== 'Claimed'"
                class="px-2.5 py-1 text-[11px] font-semibold text-brand-600 bg-brand-50 rounded-lg active:bg-brand-100 transition-colors"
                @click="openClaim(item, $event)"
              >
                Claim
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Desktop table -->
      <div v-if="sortedItems.length" class="hidden sm:block overflow-x-auto">
        <table class="min-w-full text-sm">
          <thead>
            <tr class="text-left text-[11px] text-gray-400 font-medium uppercase tracking-wider border-b border-gray-100">
              <th class="pb-2 pr-4">Worker</th>
              <th class="pb-2 pr-4">Purpose</th>
              <th class="pb-2 pr-4">Source</th>
              <th class="pb-2 pr-4 text-right">Amount</th>
              <th class="pb-2 text-center">Status</th>
              <th class="pb-2 w-10"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50">
            <tr
              v-for="item in sortedItems"
              :key="item.name"
              class="group text-gray-600 hover:bg-gray-50 cursor-pointer transition-colors"
              @click="openDetail(item)"
            >
              <td class="py-2.5 pr-4 font-medium text-gray-900">{{ item.worker || "—" }}</td>
              <td class="py-2.5 pr-4">{{ item.purpose || "—" }}</td>
              <td class="py-2.5 pr-4 text-xs text-gray-400">{{ item.source || "—" }}</td>
              <td class="py-2.5 pr-4 text-right">
                <CurrencyDisplay :value="item.amount" />
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

    <!-- Expense Items -->
    <div>
      <div class="flex items-center justify-between group mb-2.5">
        <h3 class="text-xs font-semibold text-gray-500 uppercase tracking-wider">
          {{ sectionTitle("Expenses") }}
        </h3>
        <button
          @click="isAddingExpense = true"
          class="opacity-0 group-hover:opacity-100 flex items-center gap-1 text-[10px] font-bold text-brand-600 uppercase tracking-wider bg-brand-50 hover:bg-brand-100 px-2.5 py-1 rounded transition-all"
        >
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 4v16m8-8H4"/></svg>
          Add 
        </button>
      </div>

      <div v-if="sortedExpenses.length === 0" class="py-8 text-center text-sm text-gray-400">
        No expense items for this period.
      </div>

      <!-- Mobile cards -->
      <div v-if="sortedExpenses.length" class="sm:hidden space-y-2">
        <div
          v-for="item in sortedExpenses"
          :key="item.name"
          class="bg-gray-50 rounded-xl p-3.5 transition-all active:bg-gray-100 active:scale-[0.99] cursor-pointer"
          @click="openDetail(item)"
        >
          <div class="flex items-start justify-between">
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2">
                <p class="text-sm font-semibold text-gray-900 truncate">{{ item.description || "—" }}</p>
                <svg v-if="item.status === 'Claimed'" class="w-4 h-4 text-green-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
              </div>
              <div class="flex flex-col gap-0.5">
                <p class="text-xs text-gray-500">{{ item.purpose || "No purpose" }}</p>
                <p class="text-[11px] text-gray-400 font-mono">{{ item.source || "No source" }}</p>
              </div>
            </div>
            <div class="flex items-center gap-2 shrink-0 ml-2">
              <CurrencyDisplay :value="item.amount" />
              <button
                v-if="item.status !== 'Claimed'"
                class="px-2.5 py-1 text-[11px] font-semibold text-brand-600 bg-brand-50 rounded-lg active:bg-brand-100 transition-colors"
                @click="openClaim(item, $event)"
              >
                Claim
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Desktop table -->
      <div v-if="sortedExpenses.length" class="hidden sm:block overflow-x-auto">
        <table class="min-w-full text-sm">
          <thead>
            <tr class="text-left text-[11px] text-gray-400 font-medium uppercase tracking-wider border-b border-gray-100">
              <th class="pb-2 pr-4">Description</th>
              <th class="pb-2 pr-4">Purpose</th>
              <th class="pb-2 pr-4">Source</th>
              <th class="pb-2 pr-4 text-right">Amount</th>
              <th class="pb-2 text-center">Status</th>
              <th class="pb-2 w-10"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50">
            <tr
              v-for="item in sortedExpenses"
              :key="item.name"
              class="group text-gray-600 hover:bg-gray-50 cursor-pointer transition-colors"
              @click="openDetail(item)"
            >
              <td class="py-2.5 pr-4 font-medium text-gray-900">{{ item.description || "—" }}</td>
              <td class="py-2.5 pr-4">{{ item.purpose || "—" }}</td>
              <td class="py-2.5 pr-4 text-xs text-gray-400">{{ item.source || "—" }}</td>
              <td class="py-2.5 pr-4 text-right">
                <CurrencyDisplay :value="item.amount" />
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

    <!-- Detail Modal -->
    <ItemDetailModal
      :item="detailItem"
      :disbursement-name="disbursementName"
      @close="detailItem = null"
      @claim="openClaimFromDetail"
      @updated="emit('claimed')"
    />

    <!-- Claim Modal -->
    <ClaimModal
      :item="claimItem"
      :disbursement-name="disbursementName"
      :week-num="weekNum"
      @close="claimItem = null"
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
