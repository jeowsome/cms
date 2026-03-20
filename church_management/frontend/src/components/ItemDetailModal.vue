<script setup>
import { computed, ref, watch } from "vue";
import { useQuery } from "@pinia/colada";
import { call } from "@/composables/useFrappeApi";
import CurrencyDisplay from "@/components/CurrencyDisplay.vue";
import AppButton from "@/components/AppButton.vue";

const props = defineProps({
  item: { type: Object, default: null },
  type: { type: String, default: "item" },
  disbursementName: { type: String, default: "" },
});

const emit = defineEmits(["close", "claim", "updated"]);

const isOpen = computed(() => !!props.item);
const isClaimed = computed(() => props.item?.status === "Claimed");

const editForm = ref({ worker: "", purpose: "", source: "", is_planned: 0 });
const isSaving = ref(false);
const isDeleting = ref(false);

async function deleteItem() {
  if (!confirm("Are you sure you want to permanently delete this row?")) return;
  
  isDeleting.value = true;
  try {
    await call("church_management.api.disbursement.delete_item", {
      disbursement_name: props.disbursementName,
      child_name: props.item.name,
    });
    emit("updated");
    emit("close");
  } catch (err) {
    console.error(err);
    alert(err.messages?.[0] || err.message || "Failed to delete item");
  } finally {
    isDeleting.value = false;
  }
}

watch(
  () => props.item,
  (val) => {
    if (val) {
      editForm.value = {
        worker: val.worker || "",
        purpose: val.purpose || "",
        source: val.source || "",
        is_planned: val.is_planned ? 1 : 0,
      };
    }
  }
);

const { data: workers } = useQuery({
  key: ["workers"],
  query: () => call("church_management.api.disbursement.get_workers"),
  enabled: () => isOpen.value && !isClaimed.value && props.item?.worker !== undefined,
});

const { data: purposes } = useQuery({
  key: ["purposes"],
  query: () => call("church_management.api.disbursement.get_purposes"),
  enabled: () => isOpen.value && !isClaimed.value,
});

const { data: accounts } = useQuery({
  key: ["accounts"],
  query: () => call("church_management.api.disbursement.get_source_accounts"),
  enabled: () => isOpen.value && !isClaimed.value,
});

const fields = computed(() => {
  if (!props.item) return [];
  const i = props.item;
  const result = [];

  if (isClaimed.value) {
    if (i.worker !== undefined) result.push({ label: "Worker", value: i.worker });
    if (i.description) result.push({ label: "Description", value: i.description });
    result.push({ label: "Purpose", value: i.purpose || "—" });
    result.push({ label: "Source", value: i.source || "—" });
  } else {
    // Unclaimed: worker, purpose, source are shown in edit form.
    // Show description if it's an expense item
    if (i.description) result.push({ label: "Description", value: i.description });
  }

  result.push({ label: "Status", value: i.status || "Unclaimed" });

  if (isClaimed.value) {
    result.push({ label: "Received By", value: i.received_by || "—" });
    result.push({ label: "Received Date", value: i.received_date || "—" });
  }

  if (i.department) result.push({ label: "Department", value: i.department });
  if (i.remarks) result.push({ label: "Remarks", value: i.remarks });
  if (isClaimed.value) {
    result.push({ label: "Is Planned", value: i.is_planned ? "Yes" : "No" });
  }

  return result;
});

async function saveItem() {
  if (!props.item || !props.disbursementName) return;
  isSaving.value = true;
  try {
    await call("church_management.api.disbursement.update_item", {
      disbursement_name: props.disbursementName,
      child_doctype: props.item.doctype || props.item.parenttype || "Disbursement Week Item",
      child_name: props.item.name,
      updates: JSON.stringify(editForm.value)
    });
    emit("updated");
    emit("close");
  } catch (err) {
    console.error(err);
    alert(err.messages?.[0] || err.message || "Failed to update item");
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
        class="fixed inset-0 z-[60] flex items-end sm:items-center justify-center"
        @click.self="emit('close')"
      >
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-black/40" @click="emit('close')" />

        <!-- Panel -->
        <div
          class="relative w-full sm:max-w-md bg-white rounded-t-2xl sm:rounded-2xl shadow-xl max-h-[85vh] flex flex-col"
        >
          <!-- Drag handle (mobile) -->
          <div class="sm:hidden flex justify-center pt-3 pb-1">
            <div class="w-8 h-1 rounded-full bg-gray-300" />
          </div>

          <!-- Header -->
          <div class="flex items-start justify-between px-5 pt-3 sm:pt-5 pb-3 border-b border-gray-100">
            <div class="min-w-0">
              <h3 class="text-base font-bold text-gray-900 truncate">
                {{ item?.worker || item?.description || "Item Detail" }}
              </h3>
              <div class="flex items-center gap-2 mt-1">
                <span
                  class="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full"
                  :class="isClaimed ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700'"
                >
                  <span class="w-1.5 h-1.5 rounded-full" :class="isClaimed ? 'bg-green-400' : 'bg-amber-400'" />
                  {{ isClaimed ? "Claimed" : "Unclaimed" }}
                </span>
                <CurrencyDisplay :value="item?.amount" />
              </div>
            </div>
            <button
              @click="emit('close')"
              class="p-1.5 -mr-1 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <!-- Body -->
          <div class="flex-1 overflow-y-auto px-5 py-4">
            <div class="space-y-4">
              <!-- Edit Form -->
              <div v-if="!isClaimed" class="space-y-3 p-3 bg-gray-50 rounded-xl border border-gray-100">
                <div v-if="item?.worker !== undefined">
                  <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">Worker</label>
                  <select v-model="editForm.worker" class="block w-full text-sm border-gray-200 rounded-lg shadow-sm focus:border-brand-500 focus:ring-brand-500 bg-white">
                    <option value="">Select Worker</option>
                    <option v-for="w in workers" :key="w.name" :value="w.name">{{ w.full_name }}</option>
                  </select>
                </div>
                <div>
                  <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">Purpose</label>
                  <select v-model="editForm.purpose" class="block w-full text-sm border-gray-200 rounded-lg shadow-sm focus:border-brand-500 focus:ring-brand-500 bg-white">
                    <option value="">Select Purpose</option>
                    <option v-for="p in purposes" :key="p.name" :value="p.name">{{ p.name || p.description }}</option>
                  </select>
                </div>
                <div>
                  <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">Source</label>
                  <select v-model="editForm.source" class="block w-full text-sm border-gray-200 rounded-lg shadow-sm focus:border-brand-500 focus:ring-brand-500 bg-white">
                    <option value="">Select Source</option>
                    <option v-for="a in accounts" :key="a.name" :value="a.name">{{ a.account_name || a.name }}</option>
                  </select>
                </div>
                <div v-if="item?.is_planned !== undefined">
                  <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">Is Planned</label>
                  <select v-model="editForm.is_planned" class="block w-full text-sm border-gray-200 rounded-lg shadow-sm focus:border-brand-500 focus:ring-brand-500 bg-white">
                    <option :value="1">Yes</option>
                    <option :value="0">No</option>
                  </select>
                </div>
              </div>

              <!-- Static Fields -->
              <div class="space-y-3">
                <div
                  v-for="field in fields"
                  :key="field.label"
                  class="flex items-center justify-between py-1.5"
                >
                  <span class="text-xs text-gray-400 uppercase tracking-wider">{{ field.label }}</span>
                  <span class="text-sm font-medium text-gray-800 text-right">{{ field.value }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Footer -->
          <div v-if="!isClaimed" class="px-5 py-4 border-t border-gray-100 flex gap-3">
            <button
              @click="deleteItem"
              :disabled="isDeleting"
              class="w-10 flex-shrink-0 flex items-center justify-center rounded-xl border border-red-200 text-red-600 hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-500 transition-colors disabled:opacity-50"
              title="Delete Item"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
            <AppButton variant="outline" class="flex-1" :disabled="isSaving || isDeleting" @click="saveItem">
               {{ isSaving ? 'Saving...' : 'Save Details' }}
            </AppButton>
            <AppButton class="flex-1" :disabled="isDeleting" @click="emit('claim', item)">
              Claim Item
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
