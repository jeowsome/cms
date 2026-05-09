<script setup>
import { ref, computed, watch } from "vue";
import { useQuery } from "@pinia/colada";
import { call } from "@/composables/useFrappeApi";
import AppButton from "@/components/AppButton.vue";
import CurrencyDisplay from "@/components/CurrencyDisplay.vue";

const props = defineProps({
  item: { type: Object, default: null },
  items: { type: Array, default: null },
  disbursementName: { type: String, required: true },
  weekNum: { type: Number, default: 1 },
  defaultDate: { type: String, default: "" },
});

const emit = defineEmits(["close", "claimed"]);

const isBulk = computed(() => Array.isArray(props.items) && props.items.length > 0);
const isOpen = computed(() => !!props.item || isBulk.value);
const submitting = ref(false);
const receivedBy = ref("");
const receivedDate = ref("");
const source = ref("");
const remarks = ref("");

const { data: workers } = useQuery({
  key: ["active-workers"],
  query: () => call("church_management.api.disbursement.get_workers"),
});

const { data: accounts } = useQuery({
  key: ["accounts"],
  query: () => call("church_management.api.disbursement.get_source_accounts"),
});

const totalAmount = computed(() => {
  if (isBulk.value) return props.items.reduce((s, i) => s + (i.amount || 0), 0);
  return props.item?.amount || 0;
});

watch(
  () => [props.item, props.items],
  () => {
    if (!isOpen.value) return;
    if (isBulk.value) {
      receivedBy.value = "";
      source.value = "";
      remarks.value = "";
    } else if (props.item) {
      receivedBy.value = props.item.received_by || props.item.worker || "";
      source.value = props.item.source || "";
      remarks.value = props.item.remarks || "";
    }
    receivedDate.value = props.defaultDate || getDefaultSunday();
  },
  { immediate: true }
);

function getDefaultSunday() {
  if (props.defaultDate) return props.defaultDate;
  const parts = props.disbursementName.split("-");
  if (parts.length < 2) return new Date().toISOString().slice(0, 10);
  const monthName = parts[0];
  const year = parseInt(parts[1]);
  const monthIdx = new Date(`${monthName} 1, ${year}`).getMonth();
  let sunday = new Date(year, monthIdx, 1);
  const dayOfWeek = sunday.getDay();
  if (dayOfWeek !== 0) sunday.setDate(sunday.getDate() + (7 - dayOfWeek));
  const weekOffset = Math.max(0, props.weekNum - 1);
  sunday.setDate(sunday.getDate() + weekOffset * 7);
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
    if (isBulk.value) {
      await call("church_management.api.disbursement.claim_items_bulk", {
        disbursement_name: props.disbursementName,
        child_names: JSON.stringify(props.items.map((i) => i.name)),
        received_by: receivedBy.value,
        received_date: receivedDate.value,
        source: source.value,
        remarks: remarks.value,
      });
    } else {
      await call("church_management.api.disbursement.claim_item", {
        disbursement_name: props.disbursementName,
        child_doctype: props.item.doctype || props.item.parenttype || "Disbursement Week Item",
        child_name: props.item.name,
        received_by: receivedBy.value,
        received_date: receivedDate.value,
        source: source.value,
        remarks: remarks.value,
      });
    }
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
        <div class="absolute inset-0 bg-black/40" @click="emit('close')" />

        <div class="relative w-full sm:max-w-sm bg-white rounded-t-2xl sm:rounded-2xl shadow-xl flex flex-col max-h-[90vh]">
          <div class="sm:hidden flex justify-center pt-3 pb-1">
            <div class="w-8 h-1 rounded-full bg-gray-300" />
          </div>

          <div class="px-5 pt-3 sm:pt-5 pb-3 border-b border-gray-100 shrink-0">
            <h3 class="text-base font-bold text-gray-900">
              {{ isBulk ? `Claim ${items.length} Items` : "Claim Disbursement" }}
            </h3>
            <div class="flex items-center gap-2 mt-1.5">
              <span v-if="!isBulk" class="text-sm text-gray-600 truncate">
                {{ item?.worker || item?.description }}
              </span>
              <span v-else class="text-sm text-gray-600">Total</span>
              <span class="text-gray-300">·</span>
              <CurrencyDisplay :value="totalAmount" />
            </div>
            <div v-if="isBulk" class="mt-2 max-h-24 overflow-y-auto text-xs text-gray-500 space-y-1">
              <div v-for="i in items" :key="i.name" class="flex items-center justify-between">
                <span class="truncate">{{ i.worker || i.description || i.name }}</span>
                <CurrencyDisplay :value="i.amount" size="xs" />
              </div>
            </div>
          </div>

          <div class="px-5 py-4 space-y-4 overflow-y-auto flex-1">
            <div>
              <label class="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1.5">
                Received By
              </label>
              <select
                v-model="receivedBy"
                class="w-full rounded-xl border border-gray-200 bg-gray-50 px-3.5 py-2.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors appearance-none"
              >
                <option value="" disabled>Select worker...</option>
                <option v-for="w in workers || []" :key="w.name" :value="w.name">
                  {{ w.full_name || w.name }}
                </option>
              </select>
            </div>

            <div>
              <label class="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1.5">
                Source Account <span class="text-red-500">*</span>
              </label>
              <select
                v-model="source"
                class="w-full rounded-xl border border-gray-200 bg-gray-50 px-3.5 py-2.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors appearance-none"
              >
                <option value="" disabled>Select source account...</option>
                <option v-for="a in accounts || []" :key="a.name" :value="a.name">
                  {{ a.account_name || a.name }}
                </option>
              </select>
            </div>

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

            <div>
              <label class="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1.5">
                Remarks / Description
              </label>
              <textarea
                v-model="remarks"
                rows="3"
                placeholder="Add notes..."
                class="w-full rounded-xl border border-gray-200 bg-gray-50 px-3.5 py-2.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-brand-500 transition-colors resize-none"
              />
            </div>
          </div>

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
              {{ isBulk ? `Claim ${items.length}` : "Confirm Claim" }}
            </AppButton>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-enter-active,
.modal-leave-active { transition: opacity 0.2s ease; }
.modal-enter-active > div:last-child,
.modal-leave-active > div:last-child { transition: transform 0.2s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-from > div:last-child { transform: translateY(100%); }
@media (min-width: 640px) {
  .modal-enter-from > div:last-child { transform: translateY(16px) scale(0.95); }
}
</style>
