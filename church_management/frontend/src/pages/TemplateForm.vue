<script setup>
import { ref, computed, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useQuery } from "@pinia/colada";
import { call } from "@/composables/useFrappeApi";
import PageHeader from "@/components/PageHeader.vue";
import AppButton from "@/components/AppButton.vue";
import CurrencyDisplay from "@/components/CurrencyDisplay.vue";

const route = useRoute();
const router = useRouter();
const isNew = computed(() => route.params.name === "new");

const form = ref({
  disbursement_year: new Date().getFullYear(),
  company: "",
  weekly_allowances: [],
  weekly_activity: [],
  mission_support: [],
  monthly_expenses: [],
});
const isSaving = ref(false);
const submitError = ref("");
const savedAt = ref(0);

const { data: template, isPending: loading, error, refetch } = useQuery({
  key: () => ["disbursement-template", route.params.name],
  query: () => call("church_management.api.disbursement.get_template", { name: route.params.name }),
  enabled: () => !isNew.value,
});

const { data: workers } = useQuery({
  key: ["workers"],
  query: () => call("church_management.api.disbursement.get_workers"),
});
const { data: purposes } = useQuery({
  key: ["purposes"],
  query: () => call("church_management.api.disbursement.get_purposes"),
});
const { data: accounts } = useQuery({
  key: ["accounts"],
  query: () => call("church_management.api.disbursement.get_source_accounts"),
});
const { data: companies } = useQuery({
  key: ["companies"],
  query: () => call("church_management.api.disbursement.get_companies"),
});

// Hydrate the form when the template loads.
watch(
  template,
  (t) => {
    if (!t) return;
    form.value = {
      disbursement_year: t.disbursement_year,
      company: t.company,
      weekly_allowances: (t.weekly_allowances || []).map((r) => ({ ...r })),
      weekly_activity: (t.weekly_activity || []).map((r) => ({ ...r })),
      mission_support: (t.mission_support || []).map((r) => ({ ...r })),
      monthly_expenses: (t.monthly_expenses || []).map((r) => ({ ...r })),
    };
  },
  { immediate: true }
);

// Default company once companies load (new templates only).
watch(companies, (list) => {
  if (isNew.value && list?.length && !form.value.company) {
    form.value.company = list[0].name;
  }
});

const sections = [
  {
    field: "weekly_allowances",
    title: "Weekly Allowances",
    hint: "One row per worker — repeated every Sunday of the month",
    nameField: "worker",
    namePlaceholder: "Worker",
  },
  {
    field: "weekly_activity",
    title: "Weekly Activities",
    hint: "Recurring weekly expenses — repeated every Sunday of the month",
    nameField: "description",
    namePlaceholder: "Description (e.g. Snacks)",
  },
  {
    field: "mission_support",
    title: "Mission Support",
    hint: "Once per month, lands on the Monthly tab",
    nameField: "worker",
    namePlaceholder: "Worker / missionary",
  },
  {
    field: "monthly_expenses",
    title: "Monthly Expenses",
    hint: "Once per month, lands on the Monthly tab",
    nameField: "description",
    namePlaceholder: "Description (e.g. Electric bill)",
  },
];

function addRow(field, nameField) {
  form.value[field].push({ [nameField]: "", purpose: "", amount: null, source: "" });
}
function removeRow(field, idx) {
  form.value[field].splice(idx, 1);
}
function sectionTotal(field) {
  return form.value[field].reduce((s, r) => s + (Number(r.amount) || 0), 0);
}

const weeklyTotal = computed(() => sectionTotal("weekly_allowances") + sectionTotal("weekly_activity"));
const monthlyTotal = computed(() => sectionTotal("mission_support") + sectionTotal("monthly_expenses"));
const estMonth = computed(() => weeklyTotal.value * 4 + monthlyTotal.value);

const canSave = computed(
  () => !!form.value.company && !!form.value.disbursement_year && !isSaving.value
);

async function save() {
  if (!canSave.value) return;
  isSaving.value = true;
  submitError.value = "";
  try {
    const payload = {
      name: isNew.value ? null : route.params.name,
      disbursement_year: form.value.disbursement_year,
      company: form.value.company,
    };
    for (const s of sections) {
      // Ignore fully blank rows; validate the rest against the doctype's
      // mandatory fields (purpose always; worker for worker-based tables).
      const kept = form.value[s.field].filter(
        (r) => r[s.nameField] || r.purpose || Number(r.amount)
      );
      for (const r of kept) {
        const needsWorker = s.nameField === "worker" && !r.worker;
        if (needsWorker || !r.purpose || !(Number(r.amount) > 0)) {
          submitError.value =
            `${s.title}: each row needs ` +
            (s.nameField === "worker" ? "a worker, " : "") +
            "a purpose and an amount greater than zero.";
          isSaving.value = false;
          return;
        }
      }
      payload[s.field] = kept;
    }
    const res = await call("church_management.api.disbursement.save_template", {
      payload: JSON.stringify(payload),
    });
    savedAt.value = Date.now();
    if (isNew.value) {
      router.replace({ name: "TemplateForm", params: { name: res.name } });
    } else {
      refetch();
    }
  } catch (err) {
    submitError.value = err.messages?.[0] || err.message || "Failed to save template";
  } finally {
    isSaving.value = false;
  }
}
</script>

<template>
  <div class="px-4 sm:px-6 py-4 sm:py-6 max-w-5xl mx-auto w-full">
    <PageHeader
      :title="isNew ? 'New Template' : route.params.name"
      :subtitle="isNew ? 'Define a recurring disbursement pattern' : `${form.company || ''}`"
    >
      <template #actions>
        <div class="flex items-center gap-2">
          <AppButton variant="ghost" size="sm" @click="router.push({ name: 'TemplateList' })">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
            </svg>
            <span class="hidden sm:inline">Back</span>
          </AppButton>
          <AppButton size="sm" :loading="isSaving" :disabled="!canSave" @click="save">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
            </svg>
            {{ isNew ? "Create Template" : "Save Changes" }}
          </AppButton>
        </div>
      </template>
    </PageHeader>

    <!-- Loading -->
    <div v-if="!isNew && loading" class="space-y-3">
      <div class="h-24 bg-white rounded-2xl border border-gray-100 animate-pulse" />
      <div v-for="i in 3" :key="i" class="h-40 bg-white rounded-2xl border border-gray-100 animate-pulse" />
    </div>

    <div v-else-if="!isNew && error" class="p-4 bg-red-50 text-red-700 rounded-xl text-sm">
      {{ error.message }}
    </div>

    <template v-else>
      <!-- Feedback -->
      <div v-if="submitError" role="alert" class="mb-4 p-3 bg-red-50 text-red-700 rounded-xl text-sm">
        {{ submitError }}
      </div>
      <div v-else-if="savedAt" class="mb-4 p-3 bg-green-50 text-green-700 rounded-xl text-sm flex items-center gap-2">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
        </svg>
        Template saved.
      </div>

      <!-- Header fields + totals -->
      <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-4 sm:p-5 mb-5">
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div>
            <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">Year *</label>
            <input
              v-model.number="form.disbursement_year"
              type="number" min="2000" max="2100"
              :disabled="!isNew"
              class="cm-field tabular"
            />
            <p v-if="isNew" class="mt-1 text-[10px] text-gray-400">Named automatically: DT - {{ form.disbursement_year || "…" }}</p>
          </div>
          <div>
            <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">Company *</label>
            <select v-model="form.company" class="cm-field cm-select">
              <option value="" disabled>Select company</option>
              <option v-for="c in companies" :key="c.name" :value="c.name">{{ c.name }}</option>
            </select>
          </div>
          <div class="rounded-xl bg-gray-50/70 px-3.5 py-2.5">
            <p class="text-[10px] font-medium text-gray-400 uppercase tracking-wider">Weekly total</p>
            <CurrencyDisplay :value="weeklyTotal" />
            <span class="text-xs text-gray-400"> /wk</span>
          </div>
          <div class="rounded-xl bg-gray-50/70 px-3.5 py-2.5">
            <p class="text-[10px] font-medium text-gray-400 uppercase tracking-wider">Est. per month</p>
            <CurrencyDisplay :value="estMonth" />
            <p class="text-[10px] text-gray-400 mt-0.5">weekly ×4 + monthly</p>
          </div>
        </div>
      </div>

      <!-- Item sections -->
      <div v-for="s in sections" :key="s.field" class="bg-white rounded-2xl border border-gray-100 shadow-sm mb-5 overflow-hidden">
        <div class="flex items-center justify-between px-4 sm:px-5 pt-4 pb-3">
          <div>
            <h3 class="text-sm font-bold text-gray-900">{{ s.title }}</h3>
            <p class="text-[11px] text-gray-400 mt-0.5">{{ s.hint }}</p>
          </div>
          <div class="text-right shrink-0 ml-3">
            <p class="text-[10px] font-medium text-gray-400 uppercase tracking-wider">Subtotal</p>
            <CurrencyDisplay :value="sectionTotal(s.field)" />
          </div>
        </div>

        <div v-if="!form[s.field].length" class="mx-4 sm:mx-5 mb-4 py-6 text-center text-sm text-gray-400 bg-gray-50/50 rounded-xl border border-dashed border-gray-200">
          No rows yet.
        </div>

        <div v-else class="px-4 sm:px-5 pb-2 space-y-2.5">
          <!-- Column headers (desktop) -->
          <div class="hidden sm:grid grid-cols-[1fr_1fr_8rem_1fr_2.25rem] gap-2 text-[10px] font-black text-gray-400 uppercase tracking-widest px-1">
            <span>{{ s.nameField === "worker" ? "Worker" : "Description" }}</span>
            <span>Purpose</span>
            <span class="text-right">Amount</span>
            <span>Source</span>
            <span />
          </div>

          <div
            v-for="(row, idx) in form[s.field]"
            :key="row.name || idx"
            class="grid grid-cols-2 sm:grid-cols-[1fr_1fr_8rem_1fr_2.25rem] gap-2 items-center bg-gray-50/40 sm:bg-transparent rounded-xl sm:rounded-none p-2.5 sm:p-0"
          >
            <!-- worker select or description input -->
            <select
              v-if="s.nameField === 'worker'"
              v-model="row.worker"
              class="cm-field cm-select col-span-2 sm:col-span-1"
            >
              <option value="">{{ s.namePlaceholder }}…</option>
              <option v-for="w in workers" :key="w.name" :value="w.name">{{ w.full_name || w.name }}</option>
            </select>
            <input
              v-else
              v-model="row.description"
              type="text"
              :placeholder="s.namePlaceholder"
              class="cm-field col-span-2 sm:col-span-1"
            />

            <select v-model="row.purpose" class="cm-field cm-select">
              <option value="">Purpose…</option>
              <option v-for="p in purposes" :key="p.name" :value="p.name">{{ p.name }}</option>
            </select>

            <input
              v-model.number="row.amount"
              type="number" step="0.01" min="0" placeholder="0.00" inputmode="decimal"
              class="cm-field text-right tabular font-medium"
            />

            <select v-model="row.source" class="cm-field cm-select hidden sm:block">
              <option value="">Source…</option>
              <option v-for="a in accounts" :key="a.name" :value="a.name">{{ a.account_name || a.name }}</option>
            </select>

            <button
              class="h-11 w-9 flex items-center justify-center rounded-lg text-gray-300 hover:text-red-600 hover:bg-red-50 transition-colors justify-self-end"
              :aria-label="`Remove row ${idx + 1}`"
              @click="removeRow(s.field, idx)"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <div class="px-4 sm:px-5 pb-4 pt-1">
          <button
            class="flex items-center gap-1.5 text-[11px] font-bold text-brand-600 uppercase tracking-wider bg-brand-50 hover:bg-brand-100 px-3 py-1.5 rounded-lg transition-colors"
            @click="addRow(s.field, s.nameField)"
          >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
            </svg>
            Add row
          </button>
        </div>
      </div>

      <!-- Sticky save on mobile -->
      <div class="sm:hidden sticky bottom-4 z-40">
        <AppButton class="w-full shadow-xl" :loading="isSaving" :disabled="!canSave" @click="save">
          {{ isNew ? "Create Template" : "Save Changes" }}
        </AppButton>
      </div>
    </template>
  </div>
</template>
