<script setup>
import { computed, ref } from "vue";
import { useQuery } from "@pinia/colada";
import { call } from "@/composables/useFrappeApi";
import AppButton from "@/components/AppButton.vue";

const props = defineProps({
  isOpen: { type: Boolean, default: false },
  disbursementName: { type: String, required: true },
  weekNum: { type: Number, required: true },
  tableField: { type: String, required: true }, // 'expense_item_week_X' or 'monthly_expense_items'
});

const emit = defineEmits(["close", "added"]);

const form = ref({
  description: "",
  amount: 0,
  purpose: "",
  source: "",
  is_planned: 0,
});

const isSaving = ref(false);

const { data: purposes } = useQuery({
  key: ["purposes"],
  query: () => call("church_management.api.disbursement.get_purposes"),
});

const { data: accounts } = useQuery({
  key: ["accounts"],
  query: () => call("church_management.api.disbursement.get_source_accounts"),
});

async function saveItem() {
  if (!form.value.description || !form.value.amount) {
    alert("Please provide a description and amount.");
    return;
  }

  isSaving.value = true;
  try {
    await call("church_management.api.disbursement.add_item", {
      disbursement_name: props.disbursementName,
      table_field: props.tableField,
      item_data: JSON.stringify({
        ...form.value,
        status: "Unclaimed"
      }),
    });
    
    // reset form
    form.value = { description: "", amount: 0, purpose: "", source: "", is_planned: 0 };
    emit("added");
    emit("close");
  } catch (err) {
    console.error(err);
    alert(err.messages?.[0] || err.message || "Failed to add item");
  } finally {
    isSaving.value = false;
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="isOpen"
        class="fixed inset-0 z-[60] flex items-end sm:items-center justify-center p-4"
        @click.self="emit('close')"
      >
        <div class="absolute inset-0 bg-black/40" @click="emit('close')" />

        <div class="relative w-full max-w-md bg-white rounded-2xl shadow-xl flex flex-col">
          <div class="flex items-start justify-between px-5 pt-5 pb-3 border-b border-gray-100">
            <h3 class="text-lg font-bold text-gray-900">Add New Row</h3>
            <button
              @click="emit('close')"
              class="p-1.5 -mr-1 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div class="flex-1 p-5 space-y-4 overflow-y-auto max-h-[70vh]">
            <div>
              <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">Description *</label>
              <input v-model="form.description" type="text" placeholder="e.g. Utility Bill" class="block w-full text-sm border-gray-200 rounded-lg shadow-sm focus:border-brand-500 focus:ring-brand-500">
            </div>

            <div>
              <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">Amount *</label>
              <input v-model="form.amount" type="number" step="0.01" min="0" class="block w-full text-sm border-gray-200 rounded-lg shadow-sm focus:border-brand-500 focus:ring-brand-500">
            </div>

            <div>
              <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">Purpose</label>
              <select v-model="form.purpose" class="block w-full text-sm border-gray-200 rounded-lg shadow-sm focus:border-brand-500 focus:ring-brand-500">
                <option value="">Select Purpose</option>
                <option v-for="p in purposes" :key="p.name" :value="p.name">{{ p.name || p.description }}</option>
              </select>
            </div>

            <div>
              <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">Source</label>
              <select v-model="form.source" class="block w-full text-sm border-gray-200 rounded-lg shadow-sm focus:border-brand-500 focus:ring-brand-500">
                <option value="">Select Source</option>
                <option v-for="a in accounts" :key="a.name" :value="a.name">{{ a.account_name || a.name }}</option>
              </select>
            </div>

            <div>
              <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">Is Planned</label>
              <select v-model="form.is_planned" class="block w-full text-sm border-gray-200 rounded-lg shadow-sm focus:border-brand-500 focus:ring-brand-500">
                <option :value="1">Yes</option>
                <option :value="0">No</option>
              </select>
            </div>
          </div>

          <div class="px-5 py-4 border-t border-gray-100 flex gap-3">
            <AppButton variant="outline" class="flex-1" @click="emit('close')">Cancel</AppButton>
            <AppButton class="flex-1" :loading="isSaving" @click="saveItem">Save Row</AppButton>
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
.modal-enter-from,
.modal-leave-to { opacity: 0; }
.modal-enter-from > div:last-child { transform: translateY(100%); }
@media (min-width: 640px) { .modal-enter-from > div:last-child { transform: translateY(16px) scale(0.95); } }
</style>
