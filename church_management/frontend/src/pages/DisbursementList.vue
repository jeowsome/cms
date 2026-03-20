<script setup>
import { useRouter } from "vue-router";
import { useQuery } from "@pinia/colada";
import { call } from "@/composables/useFrappeApi";
import PageHeader from "@/components/PageHeader.vue";
import DataTable from "@/components/DataTable.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import CurrencyDisplay from "@/components/CurrencyDisplay.vue";
import AppButton from "@/components/AppButton.vue";

const router = useRouter();

const {
  data: disbursements,
  isPending: loading,
  error,
} = useQuery({
  key: ["disbursements"],
  query: () => call("church_management.api.disbursement.get_list"),
});

const columns = [
  { key: "name", label: "Name" },
  { key: "month_recorded", label: "Month", hideOnMobile: true },
  { key: "year_recorded", label: "Year", hideOnMobile: true },
  { key: "docstatus", label: "Status" },
  { key: "unclaim_count", label: "Item Count", align: "right", hideOnMobile: true },
  { key: "unclaim_amount", label: "Amount", align: "right", hideOnMobile: true },
];

function statusLabel(val) {
  return val === 1 ? "Submitted" : val === 2 ? "Cancelled" : "Draft";
}

function goTo(row) {
  router.push({ name: "DisbursementForm", params: { name: row.name } });
}
</script>

<template>
  <div class="px-4 sm:px-6 py-4 sm:py-6 max-w-5xl mx-auto w-full">
    <PageHeader title="Disbursements" subtitle="Monthly expenditure records">
      <template #actions>
        <AppButton
          size="sm"
          @click="router.push({ name: 'DisbursementForm', params: { name: 'new' } })"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          <span class="hidden sm:inline">New Disbursement</span>
          <span class="sm:hidden">New</span>
        </AppButton>
      </template>
    </PageHeader>

    <!-- Error banner -->
    <div v-if="error" class="mb-4 p-3 bg-red-50 text-red-700 rounded-xl text-sm flex items-center gap-2">
      <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
      </svg>
      {{ error.message }}
    </div>

    <DataTable
      :columns="columns"
      :rows="disbursements || []"
      :loading="loading"
      row-clickable
      empty-text="No disbursements yet"
      @row-click="goTo"
    >
      <!-- Table cell overrides (desktop) -->
      <template #cell-name="{ value }">
        <span class="font-semibold text-gray-900">{{ value }}</span>
      </template>
      <template #cell-docstatus="{ value }">
        <StatusBadge :status="statusLabel(value)" />
      </template>
      <template #cell-unclaim_count="{ row }">
        <div class="text-right">
          <span class="font-medium text-gray-900">{{ row.unclaimed_count }}</span>
          <span class="text-gray-500 text-sm"> / {{ row.planned_items }}</span>
        </div>
      </template>
      <template #cell-unclaim_amount="{ row }">
        <div class="flex flex-col items-end leading-tight mt-1">
          <CurrencyDisplay :value="row.unclaimed_amount" />
          <div class="text-xs text-gray-500 mt-0.5 whitespace-nowrap flex items-center gap-1">
            <span>of</span>
            <CurrencyDisplay :value="row.planned_amount" />
          </div>
        </div>
      </template>

      <!-- Mobile card layout -->
      <template #mobile-card="{ row }">
        <div class="flex flex-col gap-3 w-full border border-transparent hover:border-gray-50">
          <div class="flex items-center justify-between">
            <div class="min-w-0">
              <p class="font-semibold text-gray-900 text-sm truncate">{{ row.name }}</p>
              <p class="text-xs text-gray-400 mt-0.5">
                {{ row.month_recorded }} {{ row.year_recorded }}
              </p>
            </div>
            <div class="flex items-center gap-2">
              <StatusBadge :status="statusLabel(row.docstatus)" />
              <svg class="w-4 h-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
              </svg>
            </div>
          </div>
          <div class="grid grid-cols-2 gap-4 pt-3 border-t border-gray-100">
            <div>
              <p class="text-[10px] font-medium text-gray-500 uppercase tracking-wider mb-1">Items Unclaimed</p>
              <p class="text-sm font-medium text-gray-900">
                {{ row.unclaimed_count }} <span class="text-gray-400 font-normal">/ {{ row.planned_items }}</span>
              </p>
            </div>
            <div class="text-right">
              <p class="text-[10px] font-medium text-gray-500 uppercase tracking-wider mb-1">Amount Unclaimed</p>
              <div class="flex flex-col items-end">
                <CurrencyDisplay :value="row.unclaimed_amount" />
                <div class="text-[11px] text-gray-400 mt-0.5 whitespace-nowrap flex items-center justify-end gap-1">
                  <span>/</span>
                  <CurrencyDisplay :value="row.planned_amount" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </DataTable>
  </div>
</template>
