<script setup>
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { useQuery } from "@pinia/colada";
import { call } from "@/composables/useFrappeApi";
import PageHeader from "@/components/PageHeader.vue";
import DataTable from "@/components/DataTable.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import CurrencyDisplay from "@/components/CurrencyDisplay.vue";
import AppButton from "@/components/AppButton.vue";
import CreateDisbursementModal from "@/components/CreateDisbursementModal.vue";
import YearSwitcher from "@/components/YearSwitcher.vue";
import { usePersistedRef } from "@/composables/usePersistedRef";

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

const router = useRouter();
const showCreate = ref(false);
const filter = ref("all"); // all | open | overdue
// Kept for the browser tab, so coming back from a month keeps the chosen year
const pickedYear = usePersistedRef("cm-disbursements-year", null, "session");

const {
  data: disbursements,
  isPending: loading,
  error,
  refetch,
} = useQuery({
  key: ["disbursements"],
  query: () => call("church_management.api.disbursement.get_list"),
});

function onCreated(names) {
  refetch();
  if (names.length === 1) {
    router.push({ name: "DisbursementForm", params: { name: names[0] } });
  }
}

// Where each month stands relative to today drives its label:
// past months with anything unclaimed are overdue, never the current month.
const today = new Date();
const nowIndex = today.getFullYear() * 12 + today.getMonth();

const STATES = {
  overdue: { chip: "bg-red-50 text-red-700", bar: "bg-red-400" },
  current: { chip: "bg-brand-50 text-brand-700", bar: "bg-brand-500" },
  upcoming: { chip: "bg-gray-100 text-gray-600", bar: "bg-gray-300" },
  done: { chip: "bg-green-50 text-green-700", bar: "bg-green-500" },
  empty: { chip: "bg-gray-100 text-gray-500", bar: "bg-gray-300" },
};

const allRows = computed(() =>
  (disbursements.value || [])
    .map((d) => {
      const year = Number(d.year_recorded) || 0;
      const monthIdx = MONTHS.indexOf(d.month_recorded);
      const index = year * 12 + monthIdx;
      const items = d.planned_items || 0;
      const open = d.unclaimed_count || 0;
      const planned = d.planned_amount || 0;
      const openAmount = d.unclaimed_amount || 0;

      let state, label;
      if (!items) [state, label] = ["empty", "No items"];
      else if (!open) [state, label] = ["done", "All claimed"];
      else if (index < nowIndex) [state, label] = ["overdue", `${open} overdue`];
      else if (index === nowIndex) [state, label] = ["current", `This month · ${open} to claim`];
      else [state, label] = ["upcoming", "Upcoming"];

      return {
        ...d,
        year,
        index,
        state,
        label,
        open,
        openAmount,
        claimedItems: Math.max(items - open, 0),
        claimedAmount: Math.max(planned - openAmount, 0),
        pct: items ? Math.round(((items - open) / items) * 100) : 0,
      };
    })
    // Newest month first, whatever order the records were created in
    .sort((a, b) => b.index - a.index)
);

// Years with records, plus the current year so a new year is reachable
// before its first disbursement exists.
const years = computed(() =>
  [...new Set([...allRows.value.map((r) => r.year).filter(Boolean), today.getFullYear()])].sort((a, b) => b - a)
);
const year = computed({
  get: () => (years.value.includes(pickedYear.value) ? pickedYear.value : today.getFullYear()),
  set: (y) => (pickedYear.value = y),
});
const yearRows = computed(() => allRows.value.filter((r) => r.year === year.value));

const totals = computed(() => {
  const rows = yearRows.value;
  const sum = (list, key) => list.reduce((a, r) => a + (r[key] || 0), 0);
  const overdue = rows.filter((r) => r.state === "overdue");
  const planned = sum(rows, "planned_amount");
  const claimed = sum(rows, "claimedAmount");
  return {
    planned,
    claimed,
    claimedPct: planned ? Math.round((claimed / planned) * 100) : 0,
    open: sum(rows, "openAmount"),
    openItems: sum(rows, "open"),
    openMonths: rows.filter((r) => r.open).length,
    overdue: sum(overdue, "openAmount"),
    overdueItems: sum(overdue, "open"),
    overdueMonths: overdue.length,
  };
});

const filters = computed(() => [
  { key: "all", label: "All months", count: yearRows.value.length },
  { key: "open", label: "To claim", count: totals.value.openMonths },
  { key: "overdue", label: "Overdue", count: totals.value.overdueMonths },
]);

const rows = computed(() => {
  if (filter.value === "open") return yearRows.value.filter((r) => r.open);
  if (filter.value === "overdue") return yearRows.value.filter((r) => r.state === "overdue");
  return yearRows.value;
});

const emptyText = computed(() => {
  if (filter.value === "overdue") return "Nothing overdue — every past month is fully claimed";
  if (filter.value === "open") return "Nothing left to claim";
  return `No disbursements for ${year.value} yet`;
});

const columns = [
  { key: "name", label: "Month" },
  { key: "progress", label: "Claimed so far" },
  { key: "claimedAmount", label: "Paid out", align: "right", hideOnMobile: true },
  { key: "openAmount", label: "Still to claim", align: "right" },
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
    <PageHeader title="Disbursements" subtitle="Monthly expenditure records — what was planned, paid out, and still waiting to be claimed">
      <template #actions>
        <AppButton size="sm" @click="showCreate = true">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          <span class="hidden sm:inline">New Disbursement</span>
          <span class="sm:hidden">New</span>
        </AppButton>
      </template>
    </PageHeader>

    <!-- Finance tools -->
    <nav class="flex flex-wrap gap-2 mb-4 -mt-1" aria-label="Finance tools">
      <RouterLink v-for="l in [
          { to: '/overdue', label: 'Overdue review' },
          { to: '/creditors', label: 'Creditors' },
          { to: '/fund-summary', label: 'Fund summary' },
          { to: '/audit-log', label: 'Audit log' },
        ]" :key="l.to" :to="l.to"
        class="text-[11px] font-bold uppercase tracking-wider text-brand-700 bg-brand-50 hover:bg-brand-100 border border-brand-100 px-3 py-1.5 rounded-lg">
        {{ l.label }}
      </RouterLink>
    </nav>

    <!-- Year -->
    <div class="mb-4">
      <YearSwitcher v-model="year" :years="years" />
    </div>

    <!-- Year at a glance -->
    <div v-if="yearRows.length" class="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-5">
      <div class="rounded-2xl p-3.5 border border-gray-100 bg-white">
        <p class="text-[11px] uppercase tracking-wide font-medium text-gray-500">Planned {{ year }}</p>
        <div class="mt-1.5"><CurrencyDisplay :value="totals.planned" size="lg" /></div>
        <p class="text-xs text-gray-400 mt-0.5">{{ yearRows.length }} month{{ yearRows.length === 1 ? "" : "s" }} on record</p>
      </div>
      <div class="rounded-2xl p-3.5 border border-gray-100 bg-white">
        <p class="text-[11px] uppercase tracking-wide font-medium text-green-700">Paid out</p>
        <div class="mt-1.5"><CurrencyDisplay :value="totals.claimed" size="lg" /></div>
        <div class="mt-1.5 h-1.5 rounded-full bg-gray-100 overflow-hidden" role="img" :aria-label="`${totals.claimedPct} percent of the planned amount has been claimed`">
          <div class="h-full rounded-full bg-green-500" :style="{ width: totals.claimedPct + '%' }" />
        </div>
        <p class="text-xs text-gray-400 mt-1">{{ totals.claimedPct }}% of planned</p>
      </div>
      <div class="rounded-2xl p-3.5 border border-gray-100 bg-white">
        <p class="text-[11px] uppercase tracking-wide font-medium text-amber-700">Still to claim</p>
        <div class="mt-1.5"><CurrencyDisplay :value="totals.open" size="lg" /></div>
        <p class="text-xs text-gray-400 mt-0.5">{{ totals.openItems }} item{{ totals.openItems === 1 ? "" : "s" }} in {{ totals.openMonths }} month{{ totals.openMonths === 1 ? "" : "s" }}</p>
      </div>
      <button
        type="button"
        class="rounded-2xl p-3.5 border text-left transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
        :class="totals.overdueItems ? 'border-red-200 bg-red-50/60 hover:bg-red-50 cursor-pointer' : 'border-gray-100 bg-white cursor-default'"
        :disabled="!totals.overdueItems"
        @click="filter = filter === 'overdue' ? 'all' : 'overdue'"
      >
        <p class="text-[11px] uppercase tracking-wide font-medium" :class="totals.overdueItems ? 'text-red-700' : 'text-gray-500'">Overdue from past months</p>
        <div class="mt-1.5"><CurrencyDisplay :value="totals.overdue" size="lg" /></div>
        <p class="text-xs mt-0.5" :class="totals.overdueItems ? 'text-red-700' : 'text-gray-400'">
          <template v-if="totals.overdueItems">{{ totals.overdueItems }} item{{ totals.overdueItems === 1 ? "" : "s" }} in {{ totals.overdueMonths }} month{{ totals.overdueMonths === 1 ? "" : "s" }} — {{ filter === "overdue" ? "showing these" : "tap to show" }}</template>
          <template v-else>Every past month is fully claimed</template>
        </p>
      </button>
    </div>

    <!-- Year + filter -->
    <div v-if="yearRows.length" class="flex flex-wrap items-center justify-between gap-2 mb-3">
      <div class="inline-flex p-1 rounded-xl bg-gray-100 text-sm font-medium" role="group" aria-label="Filter months">
        <button
          v-for="f in filters"
          :key="f.key"
          type="button"
          class="px-3 py-1.5 rounded-lg transition-colors cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
          :class="filter === f.key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'"
          :aria-pressed="filter === f.key"
          @click="filter = f.key"
        >
          {{ f.label }}
          <span class="ml-1 text-xs" :class="f.key === 'overdue' && f.count ? 'text-red-600 font-semibold' : 'text-gray-400'">{{ f.count }}</span>
        </button>
      </div>
    </div>

    <!-- Error banner -->
    <div v-if="error" class="mb-4 p-3 bg-red-50 text-red-700 rounded-xl text-sm flex items-center gap-2">
      <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
      </svg>
      {{ error.message }}
    </div>

    <DataTable
      :columns="columns"
      :rows="rows"
      :loading="loading"
      row-clickable
      :empty-text="emptyText"
      @row-click="goTo"
    >
      <!-- Table cell overrides (desktop) -->
      <template #cell-name="{ row }">
        <div class="flex flex-wrap items-center gap-x-2 gap-y-1">
          <span class="font-semibold text-gray-900">{{ row.month_recorded }} {{ row.year_recorded }}</span>
          <span class="text-[11px] px-2 py-0.5 rounded-full font-semibold" :class="STATES[row.state].chip">{{ row.label }}</span>
          <StatusBadge v-if="row.docstatus" :status="statusLabel(row.docstatus)" />
        </div>
      </template>
      <template #cell-progress="{ row }">
        <div class="w-40 lg:w-48">
          <div class="h-1.5 rounded-full bg-gray-100 overflow-hidden" role="img" :aria-label="`${row.pct} percent of items claimed`">
            <div class="h-full rounded-full" :class="STATES[row.state].bar" :style="{ width: row.pct + '%' }" />
          </div>
          <p class="text-xs text-gray-500 mt-1">
            <span class="font-medium text-gray-700">{{ row.claimedItems }}</span> of {{ row.planned_items || 0 }} items
          </p>
        </div>
      </template>
      <template #cell-claimedAmount="{ row }">
        <div class="flex flex-col items-end leading-tight">
          <CurrencyDisplay :value="row.claimedAmount" />
          <div class="text-xs text-gray-500 mt-0.5 whitespace-nowrap flex items-center gap-1">
            <span>of</span>
            <CurrencyDisplay :value="row.planned_amount" size="xs" />
          </div>
        </div>
      </template>
      <template #cell-openAmount="{ row }">
        <span v-if="!row.open" class="text-sm text-gray-300">—</span>
        <span v-else :class="row.state === 'overdue' ? '[&>span]:text-red-700' : ''">
          <CurrencyDisplay :value="row.openAmount" weight="bold" />
        </span>
      </template>

      <!-- Mobile card layout -->
      <template #mobile-card="{ row }">
        <div class="flex flex-col gap-3 w-full">
          <div class="flex items-start justify-between gap-2">
            <div class="min-w-0">
              <p class="font-semibold text-gray-900 text-sm truncate">{{ row.month_recorded }} {{ row.year_recorded }}</p>
              <span class="inline-block mt-1 text-[11px] px-2 py-0.5 rounded-full font-semibold" :class="STATES[row.state].chip">{{ row.label }}</span>
            </div>
            <div class="flex items-center gap-2 shrink-0">
              <StatusBadge v-if="row.docstatus" :status="statusLabel(row.docstatus)" />
              <svg class="w-4 h-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
              </svg>
            </div>
          </div>
          <div>
            <div class="h-1.5 rounded-full bg-gray-100 overflow-hidden" role="img" :aria-label="`${row.pct} percent of items claimed`">
              <div class="h-full rounded-full" :class="STATES[row.state].bar" :style="{ width: row.pct + '%' }" />
            </div>
            <p class="text-xs text-gray-500 mt-1">
              <span class="font-medium text-gray-700">{{ row.claimedItems }}</span> of {{ row.planned_items || 0 }} items claimed
            </p>
          </div>
          <div class="grid grid-cols-2 gap-4 pt-3 border-t border-gray-100">
            <div>
              <p class="text-[10px] font-medium text-gray-500 uppercase tracking-wider mb-1">Paid out</p>
              <CurrencyDisplay :value="row.claimedAmount" />
              <div class="text-[11px] text-gray-400 mt-0.5 whitespace-nowrap flex items-center gap-1">
                <span>of</span>
                <CurrencyDisplay :value="row.planned_amount" size="xs" />
              </div>
            </div>
            <div class="text-right">
              <p class="text-[10px] font-medium text-gray-500 uppercase tracking-wider mb-1">Still to claim</p>
              <span v-if="!row.open" class="text-sm text-gray-300">—</span>
              <span v-else :class="row.state === 'overdue' ? '[&>span]:text-red-700' : ''">
                <CurrencyDisplay :value="row.openAmount" weight="bold" />
              </span>
            </div>
          </div>
        </div>
      </template>
    </DataTable>

    <CreateDisbursementModal
      :is-open="showCreate"
      @close="showCreate = false"
      @created="onCreated"
    />
  </div>
</template>
