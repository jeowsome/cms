<script setup>
import { ref, computed, watch } from "vue";
import { useQuery } from "@pinia/colada";
import { call } from "@/composables/useFrappeApi";
import AppButton from "@/components/AppButton.vue";
import CurrencyDisplay from "@/components/CurrencyDisplay.vue";

const props = defineProps({
  item: { type: Object, default: null },
  disbursementName: { type: String, required: true },
  weekNum: { type: Number, default: 1 },
});

const emit = defineEmits(["close", "claimed"]);

const isOpen = computed(() => !!props.item);
const submitting = ref(false);
const receivedBy = ref("");
const receivedDate = ref("");
const source = ref("");
const remarks = ref("");

// Fetch active workers
const { data: workers } = useQuery({
  key: ["active-workers"],
  query: () => call("church_management.api.disbursement.get_workers"),
});

// Fetch source accounts
const { data: accounts } = useQuery({
  key: ["accounts"],
  query: () => call("church_management.api.disbursement.get_source_accounts"),
});

// Reset form when item changes
watch(
  () => props.item,
  (item) => {
    if (!item) return;
    receivedBy.value = item.received_by || item.worker || "";
    receivedDate.value = item.received_date || getDefaultSunday();
    source.value = item.source || "";
    remarks.value = item.remarks || "";
  },
);

function getDefaultSunday() {
  const parts = props.disbursementName.split("-");
  if (parts.length < 2) return new Date().toISOString().slice(0, 10);

  const monthName = parts[0];
  const year = parseInt(parts[1]);
  const monthIdx = new Date(`${monthName} 1, ${year}`).getMonth();

  // Find first Sunday of the month
  let sunday = new Date(year, monthIdx, 1);
  const dayOfWeek = sunday.getDay();
  if (dayOfWeek !== 0) {
    sunday.setDate(sunday.getDate() + (7 - dayOfWeek));
  }

  // Advance to the correct week
  const weekOffset = Math.max(0, props.weekNum - 1);
  sunday.setDate(sunday.getDate() + weekOffset * 7);

  // If past month end, use last Sunday
  if (sunday.getMonth() !== monthIdx) {
    const lastDay = new Date(year, monthIdx + 1, 0);
    sunday = new Date(lastDay);
    sunday.setDate(sunday.getDate() - sunday.getDay());
  }

  return sunday.toISOString().slice(0, 10);
}

async function submit() {
  if (!receivedBy.value || !receivedDate.value || !source.value) return;

  submitting.value = true;
  try {
    await call("church_management.api.disbursement.claim_item", {
      disbursement_name: props.disbursementName,
      child_doctype: props.item.doctype || props.item.parenttype || "Disbursement Week Item",
      child_name: props.item.name,
      received_by: receivedBy.value,
      received_date: receivedDate.value,
      source: source.value,
      remarks: remarks.value,
    });
    emit("claimed");
  } catch (e) {
    alert(e.message || "Failed to claim item");
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="isOpen"
        class="fixed inset-0 z-[70] flex items-end sm:items-center justify-center"
        @click.self="emit('close')"
      >
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-black/40" @click="emit('close')" />

        <!-- Panel -->
        <div class="relative w-full sm:max-w-sm bg-white rounded-t-2xl sm:rounded-2xl shadow-xl flex flex-col max-h-[90vh]">
          <!-- Drag handle (mobile) -->
          <div class="sm:hidden flex justify-center pt-3 pb-1">
            <div class="w-8 h-1 rounded-full bg-gray-300" />
          </div>

          <!-- Header -->
          <div class="px-5 pt-3 sm:pt-5 pb-3 border-b border-gray-100 shrink-0">
            <h3 class="text-base font-bold text-gray-900">Claim Disbursement</h3>
            <div class="flex items-center gap-2 mt-1.5">
              <span class="text-sm text-gray-600 truncate">{{ item?.worker || item?.description }}</span>
              <span class="text-gray-300">·</span>
              <CurrencyDisplay :value="item?.amount" />
            </div>
          </div>

          <!-- Form -->
          <div class="px-5 py-4 space-y-4 overflow-y-auto flex-1">
            <!-- Received By -->
            <div>
              <label class="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1.5">
                Received By
              </label>
              <select
                v-model="receivedBy"
                class="w-full rounded-xl border border-gray-200 bg-gray-50 px-3.5 py-2.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors appearance-none"
              >
                <option value="" disabled>Select worker...</option>
                <option
                  v-for="w in workers || []"
                  :key="w.name"
                  :value="w.name"
                >
                  {{ w.full_name || w.name }}
                </option>
              </select>
              <p v-if="workers && workers.length === 0" class="mt-1 text-xs text-amber-600">
                No active workers found. Check Church Worker records.
              </p>
            </div>

            <!-- Source -->
            <div>
              <label class="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1.5">
                Source Account <span class="text-red-500">*</span>
              </label>
              <select
                v-model="source"
                class="w-full rounded-xl border border-gray-200 bg-gray-50 px-3.5 py-2.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors appearance-none"
              >
                <option value="" disabled>Select source account...</option>
                <option
                  v-for="a in accounts || []"
                  :key="a.name"
                  :value="a.name"
                >
                  {{ a.account_name || a.name }}
                </option>
              </select>
            </div>

            <!-- Received Date -->
            <div>
              <label class="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1.5">
                Received Date
              </label>
              <input
                v-model="receivedDate"
                type="date"
                class="w-full rounded-xl border border-gray-200 bg-gray-50 px-3.5 py-2.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors"
              />
            </div>

            <!-- Remarks -->
            <div>
              <label class="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1.5">
                Remarks / Description
              </label>
              <textarea
                v-model="remarks"
                rows="3"
                :placeholder="item?.remarks ? '' : 'Add notes...'"
                class="w-full rounded-xl border border-gray-200 bg-gray-50 px-3.5 py-2.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors resize-none"
              />
            </div>
          </div>

          <!-- Actions -->
          <div class="px-5 py-4 border-t border-gray-100 flex gap-3 shrink-0">
            <AppButton variant="secondary" class="flex-1" @click="emit('close')">
              Cancel
            </AppButton>
            <AppButton
              class="flex-1"
              :loading="submitting"
              :disabled="!receivedBy || !receivedDate || !source"
              @click="submit"
            >
              Confirm Claim
            </AppButton>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}
.modal-enter-active > div:last-child,
.modal-leave-active > div:last-child {
  transition: transform 0.2s ease;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
.modal-enter-from > div:last-child {
  transform: translateY(100%);
}
@media (min-width: 640px) {
  .modal-enter-from > div:last-child {
    transform: translateY(16px) scale(0.95);
  }
}
</style>
