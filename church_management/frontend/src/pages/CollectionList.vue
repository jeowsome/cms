<script setup>
import { computed } from "vue";
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
  data: collections,
  isPending: loading,
  error,
} = useQuery({
  key: ["collections"],
  query: () => call("church_management.api.collection.get_list"),
});

const { data: ytd } = useQuery({
  key: ["collections-ytd"],
  query: () => call("church_management.api.collection.get_ytd_summary"),
});

const columns = [
  { key: "name", label: "Service" },
  { key: "docstatus", label: "Status" },
  { key: "all_tithes_total", label: "Tithes", align: "right", hideOnMobile: true },
  { key: "all_offering_total", label: "Offering", align: "right", hideOnMobile: true },
  { key: "all_mission_total", label: "Mission", align: "right", hideOnMobile: true },
  { key: "all_grand_total", label: "Grand Total", align: "right" },
];

function statusLabel(val) {
  return val === 1 ? "Submitted" : val === 2 ? "Cancelled" : "Draft";
}

function serviceParts(name) {
  // "2026-07-12 MORNING" → date + tag
  const [date, ...rest] = String(name).split(" ");
  return { date, tag: rest.join(" ") };
}

function fmtDate(iso) {
  const d = new Date(iso + "T00:00:00");
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", year: "numeric" });
}

const ytdCards = computed(() => {
  const s = ytd.value;
  if (!s) return [];
  return [
    { label: `Tithes ${s.year}`, value: s.tithes, cls: "bg-brand-50/70 text-brand-600" },
    { label: `Offering ${s.year}`, value: s.offering, cls: "bg-violet-50/70 text-violet-600" },
    { label: `Mission ${s.year}`, value: s.mission, cls: "bg-teal-50/70 text-teal-600" },
    { label: `Total · ${s.count} services`, value: s.grand_total, cls: "bg-green-50/70 text-green-600" },
  ];
});

function goTo(row) {
  router.push({ name: "CollectionForm", params: { name: row.name } });
}
</script>

<template>
  <div class="px-4 sm:px-6 py-4 sm:py-6 max-w-5xl mx-auto w-full">
    <PageHeader title="Collections" subtitle="Sunday service tithes, offerings & missions — 2026 onwards">
      <template #actions>
        <AppButton size="sm" @click="router.push({ name: 'CollectionForm', params: { name: 'new' } })">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          <span class="hidden sm:inline">New Collection</span>
          <span class="sm:hidden">New</span>
        </AppButton>
      </template>
    </PageHeader>

    <!-- YTD summary -->
    <div v-if="ytdCards.length" class="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
      <div v-for="card in ytdCards" :key="card.label" class="rounded-2xl p-3.5 border border-gray-100 bg-white">
        <p class="text-[11px] uppercase tracking-wide font-medium rounded-md inline-block px-1.5 py-0.5" :class="card.cls">
          {{ card.label }}
        </p>
        <div class="mt-1.5">
          <CurrencyDisplay :value="card.value" size="lg" />
        </div>
      </div>
    </div>

    <!-- Error banner -->
    <div v-if="error" class="mb-4 p-3 bg-red-50 text-red-700 rounded-xl text-sm flex items-center gap-2">
      <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
      </svg>
      {{ error.message }}
    </div>

    <DataTable
      :columns="columns"
      :rows="collections || []"
      :loading="loading"
      row-clickable
      empty-text="No collections recorded yet this year"
      @row-click="goTo"
    >
      <template #cell-name="{ value }">
        <div class="flex items-center gap-2">
          <span class="font-semibold text-gray-900">{{ fmtDate(serviceParts(value).date) }}</span>
          <span
            class="text-[10px] px-2 py-0.5 rounded-full font-black tracking-wider"
            :class="serviceParts(value).tag === 'MORNING' ? 'bg-amber-50 text-amber-700' : 'bg-indigo-50 text-indigo-700'"
          >
            {{ serviceParts(value).tag }}
          </span>
        </div>
      </template>
      <template #cell-docstatus="{ value }">
        <StatusBadge :status="statusLabel(value)" />
      </template>
      <template #cell-all_tithes_total="{ value }">
        <CurrencyDisplay :value="value" />
      </template>
      <template #cell-all_offering_total="{ value }">
        <CurrencyDisplay :value="value" />
      </template>
      <template #cell-all_mission_total="{ value }">
        <CurrencyDisplay :value="value" />
      </template>
      <template #cell-all_grand_total="{ value }">
        <CurrencyDisplay :value="value" weight="bold" />
      </template>

      <!-- Mobile card layout -->
      <template #mobile-card="{ row }">
        <div class="flex flex-col gap-3 w-full">
          <div class="flex items-center justify-between">
            <div class="min-w-0">
              <p class="font-semibold text-gray-900 text-sm truncate">{{ fmtDate(serviceParts(row.name).date) }}</p>
              <span
                class="text-[10px] px-2 py-0.5 rounded-full font-black tracking-wider inline-block mt-1"
                :class="serviceParts(row.name).tag === 'MORNING' ? 'bg-amber-50 text-amber-700' : 'bg-indigo-50 text-indigo-700'"
              >
                {{ serviceParts(row.name).tag }}
              </span>
            </div>
            <div class="flex items-center gap-2">
              <StatusBadge :status="statusLabel(row.docstatus)" />
              <svg class="w-4 h-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
              </svg>
            </div>
          </div>
          <div class="grid grid-cols-3 gap-2 pt-3 border-t border-gray-100">
            <div>
              <p class="text-[10px] font-medium text-gray-500 uppercase tracking-wider mb-1">Tithes</p>
              <CurrencyDisplay :value="row.all_tithes_total" size="xs" />
            </div>
            <div>
              <p class="text-[10px] font-medium text-gray-500 uppercase tracking-wider mb-1">Offering</p>
              <CurrencyDisplay :value="row.all_offering_total" size="xs" />
            </div>
            <div class="text-right">
              <p class="text-[10px] font-medium text-gray-500 uppercase tracking-wider mb-1">Total</p>
              <CurrencyDisplay :value="row.all_grand_total" size="xs" weight="bold" />
            </div>
          </div>
        </div>
      </template>
    </DataTable>
  </div>
</template>
