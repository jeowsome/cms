<script setup>
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { useQuery } from "@pinia/colada";
import { call } from "@/composables/useFrappeApi";
import { useSessionStore } from "@/stores/session";
import PageHeader from "@/components/PageHeader.vue";
import DataTable from "@/components/DataTable.vue";
import AppButton from "@/components/AppButton.vue";
import CurrencyDisplay from "@/components/CurrencyDisplay.vue";
import CreateDonationModal from "@/components/CreateDonationModal.vue";
import PurposeModal from "@/components/PurposeModal.vue";

const MIN_YEAR = 2026;

const router = useRouter();
const session = useSessionStore();
const year = ref(""); // "" → all years from 2026
const department = ref(""); // "" → all departments visible to the user
const showCreate = ref(false);
const showPurposes = ref(false);

const currentYear = new Date().getFullYear();
const yearOptions = computed(() => {
  const years = [];
  for (let y = Math.max(currentYear, MIN_YEAR); y >= MIN_YEAR; y--) years.push(y);
  return years;
});

const {
  data: donations,
  isPending: loading,
  error,
  refetch,
} = useQuery({
  key: () => ["donations", year.value || "all", department.value || "all"],
  query: () => {
    const params = { year: year.value || null };
    if (department.value) params.department = department.value;
    return call("church_management.api.donation.get_list", params);
  },
});

const { data: departments } = useQuery({
  key: ["donation-departments"],
  query: () => call("church_management.api.donation.get_departments"),
  staleTime: 5 * 60 * 1000,
});

const columns = [
  { key: "department", label: "Department" },
  { key: "year", label: "Year" },
  { key: "total_donated_cash_amount", label: "Cash", hideOnMobile: true },
  { key: "total_donated_cashless_amount", label: "GCash", hideOnMobile: true },
  { key: "total_donated_amount", label: "Total" },
];

const subtitle = computed(() => {
  const n = (donations.value || []).length;
  const scope = session.isDonationAdmin ? "all departments" : "your department";
  return `${n} record${n === 1 ? "" : "s"} · ${scope} · ${MIN_YEAR} onwards`;
});

function openRow(row) {
  router.push(`/donations/${encodeURIComponent(row.name)}`);
}

function onCreated(doc) {
  refetch();
  router.push(`/donations/${encodeURIComponent(doc.name)}`);
}
</script>

<template>
  <div class="px-4 sm:px-6 py-4 sm:py-6 max-w-5xl mx-auto w-full">
    <PageHeader title="Donations" :subtitle="subtitle">
      <template #actions>
        <AppButton size="sm" variant="secondary" @click="showPurposes = true">
          Purposes
        </AppButton>
        <AppButton v-if="session.isDonationAdmin" size="sm" @click="showCreate = true">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          <span class="hidden sm:inline">New Donation</span>
          <span class="sm:hidden">New</span>
        </AppButton>
      </template>
    </PageHeader>

    <!-- Filters -->
    <div class="mb-4 flex flex-wrap items-center gap-x-4 gap-y-2">
      <div class="flex items-center gap-2">
        <label class="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Year</label>
        <select v-model="year" class="cm-field cm-select !w-auto">
          <option value="">All ({{ MIN_YEAR }}+)</option>
          <option v-for="y in yearOptions" :key="y" :value="y">{{ y }}</option>
        </select>
      </div>
      <div v-if="(departments || []).length > 1" class="flex items-center gap-2">
        <label class="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Department</label>
        <select v-model="department" class="cm-field cm-select !w-auto max-w-[14rem]">
          <option value="">All departments</option>
          <option v-for="d in departments" :key="d" :value="d">{{ d }}</option>
        </select>
      </div>
    </div>

    <div v-if="error" class="mb-4 p-3 bg-red-50 text-red-700 rounded-xl text-sm">{{ error.message }}</div>

    <DataTable
      :columns="columns"
      :rows="donations || []"
      :loading="loading"
      row-clickable
      empty-text="No donation records yet"
      @row-click="openRow"
    >
      <template #cell-department="{ row }">
        <span class="font-semibold text-gray-900">{{ row.department }}</span>
        <p v-if="row.assigned_to" class="text-xs text-gray-400 truncate">{{ row.assigned_to }}</p>
      </template>
      <template #cell-year="{ value }">
        <span class="tabular text-gray-600">{{ value }}</span>
      </template>
      <template #cell-total_donated_cash_amount="{ value }">
        <CurrencyDisplay :value="value" />
      </template>
      <template #cell-total_donated_cashless_amount="{ value }">
        <CurrencyDisplay :value="value" />
      </template>
      <template #cell-total_donated_amount="{ value }">
        <CurrencyDisplay :value="value" weight="bold" />
      </template>

      <!-- Mobile card -->
      <template #mobile-card="{ row }">
        <div class="flex items-center gap-3 w-full">
          <div class="min-w-0 flex-1">
            <p class="font-semibold text-gray-900 text-sm truncate">{{ row.department }}</p>
            <p class="text-xs text-gray-400 mt-0.5">{{ row.year }}</p>
          </div>
          <CurrencyDisplay :value="row.total_donated_amount" weight="bold" />
          <svg class="w-4 h-4 text-gray-300 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
          </svg>
        </div>
      </template>
    </DataTable>

    <CreateDonationModal
      :is-open="showCreate"
      @close="showCreate = false"
      @created="onCreated"
    />
    <PurposeModal :is-open="showPurposes" @close="showPurposes = false" />
  </div>
</template>
