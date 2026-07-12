<script setup>
import { ref, computed, watch } from "vue";
import { useQuery } from "@pinia/colada";
import { call } from "@/composables/useFrappeApi";
import AppButton from "@/components/AppButton.vue";
import CurrencyDisplay from "@/components/CurrencyDisplay.vue";

const props = defineProps({
  isOpen: { type: Boolean, default: false },
});

const emit = defineEmits(["close", "created"]);

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

const currentYear = new Date().getFullYear();
const year = ref(currentYear);
const selectedTemplate = ref("");
const selectedMonths = ref([]);
const isGenerating = ref(false);
const submitError = ref("");

const { data: allTemplates, isPending: templatesLoading } = useQuery({
  key: ["disbursement-templates"],
  query: () => call("church_management.api.disbursement.get_templates"),
  enabled: () => props.isOpen,
});
// Templates whose company was deleted can never generate — hide them here
// (they remain visible on the Templates management page for cleanup).
const templates = computed(() => (allTemplates.value || []).filter((t) => t.company_valid));

const { data: availableMonths, isPending: monthsLoading } = useQuery({
  key: () => ["available-months", year.value],
  query: () =>
    call("church_management.api.disbursement.get_available_months", { year: year.value }),
  enabled: () => props.isOpen,
});

const availableSet = computed(
  () => new Set((availableMonths.value || []).map((m) => m.month))
);

// Reset transient state each time the modal opens; preselect a lone template.
watch(
  () => props.isOpen,
  (open) => {
    if (open) {
      selectedMonths.value = [];
      submitError.value = "";
      year.value = currentYear;
    }
  }
);
watch(templates, (list) => {
  if (list?.length === 1) selectedTemplate.value = list[0].name;
  else if (list?.length && !list.some((t) => t.name === selectedTemplate.value)) {
    selectedTemplate.value = "";
  }
});
// Changing year invalidates month picks that no longer exist for that year.
watch(year, () => {
  selectedMonths.value = [];
});

function sundaysIn(monthName, yr) {
  const monthIdx = MONTHS.indexOf(monthName);
  let count = 0;
  const days = new Date(yr, monthIdx + 1, 0).getDate();
  for (let d = 1; d <= days; d++) {
    if (new Date(yr, monthIdx, d).getDay() === 0) count++;
  }
  return Math.min(count, 5);
}

function toggleMonth(month) {
  if (!availableSet.value.has(month)) return;
  const i = selectedMonths.value.indexOf(month);
  if (i >= 0) selectedMonths.value.splice(i, 1);
  else selectedMonths.value.push(month);
}

const remainingMonths = computed(() =>
  MONTHS.filter((m) => availableSet.value.has(m))
);
const allRemainingSelected = computed(
  () =>
    remainingMonths.value.length > 0 &&
    selectedMonths.value.length === remainingMonths.value.length
);
function toggleAllRemaining() {
  selectedMonths.value = allRemainingSelected.value ? [] : [...remainingMonths.value];
}

const activeTemplate = computed(() =>
  (templates.value || []).find((t) => t.name === selectedTemplate.value)
);

// Mirrors generate_disbursements: weekly rows repeat once per Sunday of the
// month; mission support + monthly expenses land once on the Monthly tab.
const preview = computed(() => {
  const t = activeTemplate.value;
  if (!t || !selectedMonths.value.length) return null;
  let items = 0;
  let amount = 0;
  for (const m of selectedMonths.value) {
    const weeks = sundaysIn(m, year.value);
    items += t.weekly_item_count * weeks + t.monthly_item_count;
    amount += t.weekly_amount * weeks + t.monthly_amount;
  }
  return { records: selectedMonths.value.length, items, amount };
});

const canGenerate = computed(
  () => !!selectedTemplate.value && selectedMonths.value.length > 0 && !isGenerating.value
);

async function generate() {
  if (!canGenerate.value) return;
  isGenerating.value = true;
  submitError.value = "";
  try {
    const r = await call("church_management.api.disbursement.create_from_template", {
      template_name: selectedTemplate.value,
      year: year.value,
      months: JSON.stringify(selectedMonths.value),
    });
    emit("created", r.created || []);
    emit("close");
  } catch (err) {
    submitError.value = err.messages?.[0] || err.message || "Failed to generate disbursements";
  } finally {
    isGenerating.value = false;
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="isOpen"
        class="fixed inset-0 z-[60] flex items-end sm:items-center justify-center sm:p-4"
        @click.self="emit('close')"
      >
        <div class="absolute inset-0 bg-black/40" @click="emit('close')" />

        <div class="relative w-full max-w-lg bg-white sm:rounded-2xl rounded-t-2xl shadow-xl flex flex-col max-h-[92vh] sm:max-h-[85vh]">
          <!-- Header -->
          <div class="flex items-start justify-between px-5 pt-5 pb-3 border-b border-gray-100">
            <div>
              <h3 class="text-lg font-bold text-gray-900">New Disbursement</h3>
              <p class="text-xs text-gray-400 mt-0.5">Generate monthly records from a template</p>
            </div>
            <button
              @click="emit('close')"
              aria-label="Close"
              class="p-2 -mr-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <!-- Body -->
          <div class="flex-1 overflow-y-auto p-5 space-y-5">
            <!-- Template picker -->
            <div>
              <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Template *</label>

              <div v-if="templatesLoading" class="space-y-2">
                <div v-for="i in 2" :key="i" class="h-16 bg-gray-50 rounded-xl animate-pulse" />
              </div>

              <div
                v-else-if="!templates?.length"
                class="p-4 bg-amber-50 rounded-xl text-sm text-amber-700"
              >
                No disbursement templates found. Create one in the Desk under
                <span class="font-semibold">Disbursement Template</span> first.
              </div>

              <div v-else class="space-y-2" role="radiogroup" aria-label="Disbursement template">
                <button
                  v-for="t in templates"
                  :key="t.name"
                  type="button"
                  role="radio"
                  :aria-checked="selectedTemplate === t.name"
                  @click="selectedTemplate = t.name"
                  class="w-full text-left rounded-xl border-2 p-3.5 transition-all active:scale-[0.99]"
                  :class="selectedTemplate === t.name
                    ? 'border-brand-500 bg-brand-50/50'
                    : 'border-gray-100 hover:border-gray-200 bg-white'"
                >
                  <div class="flex items-center justify-between gap-3">
                    <div class="min-w-0">
                      <p class="font-semibold text-sm text-gray-900 truncate">{{ t.name }}</p>
                      <p class="text-xs text-gray-400 mt-0.5 truncate">{{ t.company }}</p>
                    </div>
                    <div
                      class="w-5 h-5 rounded-full border-2 shrink-0 flex items-center justify-center transition-colors"
                      :class="selectedTemplate === t.name ? 'border-brand-500 bg-brand-500' : 'border-gray-300'"
                    >
                      <svg v-if="selectedTemplate === t.name" class="w-3 h-3 text-white" fill="none" stroke="currentColor" stroke-width="3" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                  </div>
                  <div class="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-[11px] text-gray-500">
                    <span>
                      <span class="font-semibold text-gray-700">{{ t.weekly_item_count }}</span>
                      weekly items ·
                      <CurrencyDisplay :value="t.weekly_amount" class="!text-[11px] !font-semibold" />/wk
                    </span>
                    <span>
                      <span class="font-semibold text-gray-700">{{ t.monthly_item_count }}</span>
                      monthly items ·
                      <CurrencyDisplay :value="t.monthly_amount" class="!text-[11px] !font-semibold" />/mo
                    </span>
                  </div>
                </button>
              </div>
            </div>

            <!-- Year stepper -->
            <div>
              <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Year</label>
              <div class="inline-flex items-center rounded-xl border border-gray-200 overflow-hidden">
                <button
                  type="button"
                  aria-label="Previous year"
                  @click="year--"
                  class="px-3.5 py-2.5 text-gray-500 hover:bg-gray-50 hover:text-gray-800 transition-colors"
                >
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.75 19.5L8.25 12l7.5-7.5" />
                  </svg>
                </button>
                <span class="px-4 text-sm font-bold text-gray-900 tabular-nums min-w-[4.5rem] text-center">{{ year }}</span>
                <button
                  type="button"
                  aria-label="Next year"
                  @click="year++"
                  class="px-3.5 py-2.5 text-gray-500 hover:bg-gray-50 hover:text-gray-800 transition-colors"
                >
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                  </svg>
                </button>
              </div>
            </div>

            <!-- Month chips -->
            <div>
              <div class="flex items-center justify-between mb-2">
                <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide">Months *</label>
                <button
                  v-if="remainingMonths.length"
                  type="button"
                  @click="toggleAllRemaining"
                  class="text-xs font-semibold text-brand-600 hover:text-brand-700 px-2 py-1 -my-1 rounded-lg hover:bg-brand-50 transition-colors"
                >
                  {{ allRemainingSelected ? "Clear all" : `Select all (${remainingMonths.length})` }}
                </button>
              </div>

              <div v-if="monthsLoading" class="grid grid-cols-3 gap-2">
                <div v-for="i in 12" :key="i" class="h-11 bg-gray-50 rounded-xl animate-pulse" />
              </div>

              <div v-else class="grid grid-cols-3 gap-2">
                <button
                  v-for="m in MONTHS"
                  :key="m"
                  type="button"
                  :disabled="!availableSet.has(m)"
                  :aria-pressed="selectedMonths.includes(m)"
                  @click="toggleMonth(m)"
                  class="relative h-11 rounded-xl text-xs font-semibold border transition-all active:scale-[0.97] disabled:cursor-not-allowed"
                  :class="!availableSet.has(m)
                    ? 'bg-gray-50 border-gray-100 text-gray-300'
                    : selectedMonths.includes(m)
                      ? 'bg-brand-600 border-brand-600 text-white shadow-sm'
                      : 'bg-white border-gray-200 text-gray-700 hover:border-brand-300 hover:bg-brand-50/40'"
                >
                  {{ m.slice(0, 3) }}
                  <span
                    v-if="!availableSet.has(m)"
                    class="absolute -top-1.5 -right-1.5 flex items-center justify-center w-4 h-4 rounded-full bg-gray-200"
                    title="Already created"
                  >
                    <svg class="w-2.5 h-2.5 text-gray-500" fill="none" stroke="currentColor" stroke-width="3" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  </span>
                </button>
              </div>
              <p class="mt-2 text-[11px] text-gray-400">
                Grayed-out months already have a disbursement for {{ year }}.
              </p>
            </div>

            <!-- Generation preview -->
            <div
              v-if="preview"
              class="rounded-xl bg-brand-50/60 border border-brand-100 px-4 py-3 flex items-center justify-between gap-3"
              aria-live="polite"
            >
              <div class="text-xs text-brand-800">
                <span class="font-bold">{{ preview.records }}</span>
                record{{ preview.records > 1 ? "s" : "" }} ·
                <span class="font-bold">{{ preview.items }}</span> items
              </div>
              <div class="text-right">
                <p class="text-[10px] uppercase tracking-wide font-medium text-brand-500">Est. planned</p>
                <CurrencyDisplay :value="preview.amount" class="!text-brand-800" />
              </div>
            </div>

            <!-- Error -->
            <div v-if="submitError" role="alert" class="p-3 bg-red-50 text-red-700 rounded-xl text-sm flex items-start gap-2">
              <svg class="w-4 h-4 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
              </svg>
              {{ submitError }}
            </div>
          </div>

          <!-- Footer -->
          <div class="px-5 py-4 border-t border-gray-100 flex gap-3">
            <AppButton variant="secondary" class="flex-1" @click="emit('close')">Cancel</AppButton>
            <AppButton class="flex-1" :loading="isGenerating" :disabled="!canGenerate" @click="generate">
              Generate
              <span v-if="selectedMonths.length" class="opacity-80">({{ selectedMonths.length }})</span>
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
.modal-enter-from,
.modal-leave-to { opacity: 0; }
.modal-enter-from > div:last-child { transform: translateY(100%); }
@media (min-width: 640px) { .modal-enter-from > div:last-child { transform: translateY(16px) scale(0.95); } }
</style>
