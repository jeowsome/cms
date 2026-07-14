<script setup>
import { reactive, ref, watch } from "vue";
import { useQuery } from "@pinia/colada";
import { call } from "@/composables/useFrappeApi";
import AppButton from "@/components/AppButton.vue";

/**
 * Admin-only: start a department's donation record for a year (2026+).
 */
const props = defineProps({
  isOpen: { type: Boolean, default: false },
});
const emit = defineEmits(["close", "created"]);

const form = reactive({
  department: "",
  year: new Date().getFullYear(),
  assigned_to: "",
});
const saving = ref(false);
const errorMsg = ref("");

const { data: options } = useQuery({
  key: ["donation-new-options"],
  query: () => call("church_management.api.donation.get_new_donation_options"),
  enabled: () => props.isOpen,
  staleTime: 5 * 60 * 1000,
});

watch(
  () => props.isOpen,
  (open) => {
    if (!open) return;
    errorMsg.value = "";
    form.department = "";
    form.year = Math.max(new Date().getFullYear(), 2026);
    form.assigned_to = "";
  }
);

async function create() {
  errorMsg.value = "";
  if (!form.department) {
    errorMsg.value = "Pick a department.";
    return;
  }
  saving.value = true;
  try {
    const doc = await call("church_management.api.donation.save_donation", {
      doc: { ...form, donated_amounts: [] },
    });
    emit("created", doc);
    emit("close");
  } catch (e) {
    errorMsg.value = e.message || "Failed to create donation record.";
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <Teleport to="body">
    <div v-if="isOpen" class="fixed inset-0 z-[60] flex items-end sm:items-center justify-center p-4">
      <div class="absolute inset-0 bg-gray-900/40 backdrop-blur-sm" @click="!saving && emit('close')" />
      <div class="relative bg-white rounded-2xl shadow-2xl w-full max-w-md p-5 anim-pop max-h-[90dvh] overflow-y-auto">
        <div class="flex items-start justify-between gap-3">
          <div>
            <h3 class="text-base font-bold text-gray-900">New donation record</h3>
            <p class="text-xs text-gray-500 mt-0.5">One record per department per year</p>
          </div>
          <button
            type="button"
            class="w-8 h-8 rounded-lg flex items-center justify-center text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors shrink-0"
            aria-label="Close"
            @click="!saving && emit('close')"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div v-if="errorMsg" class="mt-3 p-2.5 rounded-xl bg-red-50 text-red-700 text-xs font-semibold">
          {{ errorMsg }}
        </div>

        <form class="mt-4 space-y-3" @submit.prevent="create">
          <div>
            <label class="block text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1">
              Department <span class="text-red-500">*</span>
            </label>
            <select v-model="form.department" class="cm-field cm-select">
              <option value="" disabled>Select a department…</option>
              <option v-for="d in options?.departments || []" :key="d" :value="d">{{ d }}</option>
            </select>
          </div>

          <div>
            <label class="block text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1">
              Year <span class="text-red-500">*</span>
            </label>
            <input v-model.number="form.year" type="number" :min="options?.min_year || 2026" class="cm-field tabular" />
          </div>

          <div>
            <label class="block text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1">
              Assigned to
            </label>
            <select v-model="form.assigned_to" class="cm-field cm-select">
              <option value="">— No one yet —</option>
              <option v-for="u in options?.users || []" :key="u.name" :value="u.name">
                {{ u.full_name ? `${u.full_name} (${u.name})` : u.name }}
              </option>
            </select>
            <p class="text-[11px] text-gray-400 mt-1">The assigned user records this department's donations.</p>
          </div>

          <div class="flex justify-end gap-2 pt-2">
            <AppButton type="button" variant="secondary" size="sm" :disabled="saving" @click="emit('close')">Cancel</AppButton>
            <AppButton type="submit" size="sm" :loading="saving">Create</AppButton>
          </div>
        </form>
      </div>
    </div>
  </Teleport>
</template>
