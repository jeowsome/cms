<script setup>
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { useQuery } from "@pinia/colada";
import { call } from "@/composables/useFrappeApi";
import PageHeader from "@/components/PageHeader.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import CurrencyDisplay from "@/components/CurrencyDisplay.vue";
import AppButton from "@/components/AppButton.vue";

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

const router = useRouter();
const pickedYear = ref(null);
const month = ref(null); // "2026-11", or null for the whole year
const draftsOnly = ref(false);

const {
  data: collections,
  isPending: loading,
  error,
} = useQuery({
  key: ["collections"],
  query: () => call("church_management.api.collection.get_list"),
});

function statusLabel(val) {
  return val === 1 ? "Submitted" : val === 2 ? "Cancelled" : "Draft";
}

function fmtDate(iso) {
  const d = new Date(iso + "T00:00:00");
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
}

const peso = new Intl.NumberFormat("en-PH", { style: "currency", currency: "PHP", maximumFractionDigits: 0 });
function compact(v) {
  return v >= 1e6 ? `₱${(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `₱${Math.round(v / 1e3)}k` : `₱${Math.round(v)}`;
}

// "2026-07-12 MORNING" → day + service tag; the name is the reliable source of both.
const allRows = computed(() =>
  (collections.value || []).map((c) => {
    const [day, ...rest] = String(c.name).split(" ");
    return { ...c, day, tag: rest.join(" "), ym: day.slice(0, 7), year: Number(day.slice(0, 4)) };
  })
);

const years = computed(() => [...new Set(allRows.value.map((r) => r.year))].sort((a, b) => b - a));
const year = computed(() => (years.value.includes(pickedYear.value) ? pickedYear.value : years.value[0]));
// Cancelled records stay visible in the list but never count toward a total
const yearRows = computed(() => allRows.value.filter((r) => r.year === year.value));
const counted = computed(() => yearRows.value.filter((r) => r.docstatus !== 2));
const drafts = computed(() => yearRows.value.filter((r) => r.docstatus === 0));

const { data: ytd } = useQuery({
  key: () => ["collections-ytd", year.value || "current"],
  query: () => call("church_management.api.collection.get_ytd_summary", year.value ? { year: year.value } : {}),
  // Wait for the list so the year is known — avoids fetching the summary twice
  enabled: () => !loading.value,
});

const perSunday = computed(() => {
  const submitted = yearRows.value.filter((r) => r.docstatus === 1);
  const days = new Set(submitted.map((r) => r.day)).size;
  return days ? submitted.reduce((a, r) => a + (r.all_grand_total || 0), 0) / days : 0;
});

const ytdCards = computed(() => {
  const s = ytd.value;
  if (!s) return [];
  return [
    { label: `Tithes ${s.year}`, value: s.tithes, cls: "bg-brand-50/70 text-brand-600" },
    { label: `Offering ${s.year}`, value: s.offering, cls: "bg-violet-50/70 text-violet-600" },
    { label: `Mission ${s.year}`, value: s.mission, cls: "bg-teal-50/70 text-teal-600" },
    {
      label: `Total · ${s.count} services`,
      value: s.grand_total,
      cls: "bg-green-50/70 text-green-600",
      note: perSunday.value ? `about ${peso.format(perSunday.value)} per Sunday` : "",
    },
  ];
});

// One bar per month of the year, oldest first — doubles as the month filter.
const monthBars = computed(() => {
  const by = new Map();
  for (const r of counted.value) {
    const m = by.get(r.ym) || { key: r.ym, total: 0, count: 0, days: new Set() };
    m.total += r.all_grand_total || 0;
    m.count += 1;
    m.days.add(r.day);
    by.set(r.ym, m);
  }
  const bars = [...by.values()].sort((a, b) => a.key.localeCompare(b.key));
  const max = Math.max(...bars.map((b) => b.total), 1);
  const now = new Date();
  const nowKey = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  return bars.map((b) => {
    const name = MONTHS[Number(b.key.slice(5, 7)) - 1] || b.key;
    return { ...b, name, short: name.slice(0, 3), sundays: b.days.size, pct: Math.max((b.total / max) * 100, 3), current: b.key === nowKey };
  });
});

const activeMonth = computed(() => (monthBars.value.some((b) => b.key === month.value) ? month.value : null));

// The list: newest first, grouped by month with a subtotal, and each Sunday's
// services kept together with a combined total when there are two.
const groups = computed(() => {
  let rows = yearRows.value;
  if (activeMonth.value) rows = rows.filter((r) => r.ym === activeMonth.value);
  if (draftsOnly.value) rows = rows.filter((r) => r.docstatus === 0);
  rows = [...rows].sort((a, b) => b.day.localeCompare(a.day) || a.tag.localeCompare(b.tag));

  const dayTotals = new Map();
  const dayCounts = new Map();
  for (const r of rows) {
    if (r.docstatus === 2) continue;
    dayTotals.set(r.day, (dayTotals.get(r.day) || 0) + (r.all_grand_total || 0));
    dayCounts.set(r.day, (dayCounts.get(r.day) || 0) + 1);
  }

  const out = [];
  let prevDay = null;
  for (const r of rows) {
    let g = out[out.length - 1];
    if (!g || g.key !== r.ym) {
      g = { key: r.ym, label: `${MONTHS[Number(r.ym.slice(5, 7)) - 1] || r.ym} ${r.ym.slice(0, 4)}`, rows: [], total: 0, count: 0, days: new Set() };
      out.push(g);
      prevDay = null;
    }
    const firstOfDay = r.day !== prevDay;
    prevDay = r.day;
    g.rows.push({ ...r, firstOfDay, dayTotal: firstOfDay && dayCounts.get(r.day) > 1 ? dayTotals.get(r.day) : null });
    if (r.docstatus !== 2) {
      g.total += r.all_grand_total || 0;
      g.count += 1;
      g.days.add(r.day);
    }
  }
  return out.map((g) => ({ ...g, sundays: g.days.size }));
});

const emptyText = computed(() => {
  if (draftsOnly.value) return "No drafts — every collection is submitted";
  return "No collections recorded yet this year";
});

function tagClass(tag) {
  return tag === "MORNING" ? "bg-amber-50 text-amber-700" : "bg-indigo-50 text-indigo-700";
}

function goTo(row) {
  router.push({ name: "CollectionForm", params: { name: row.name } });
}
</script>

<template>
  <div class="px-4 sm:px-6 py-4 sm:py-6 max-w-5xl mx-auto w-full">
    <PageHeader title="Collections" subtitle="Sunday service tithes, offerings & missions — 2026 onwards">
      <template #actions>
        <AppButton size="sm" @click="router.push({ name: 'CollectionForm', params: { name: 'new' } })">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          <span class="hidden sm:inline">New Collection</span>
          <span class="sm:hidden">New</span>
        </AppButton>
      </template>
    </PageHeader>

    <!-- Year tabs (only once there is more than one year) -->
    <div v-if="years.length > 1" class="inline-flex p-1 mb-4 rounded-xl bg-gray-100 text-sm font-medium" role="group" aria-label="Year">
      <button
        v-for="y in years"
        :key="y"
        type="button"
        class="px-3 py-1.5 rounded-lg transition-colors cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
        :class="year === y ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'"
        :aria-pressed="year === y"
        @click="pickedYear = y; month = null"
      >
        {{ y }}
      </button>
    </div>

    <!-- YTD summary -->
    <div v-if="ytdCards.length" class="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
      <div v-for="card in ytdCards" :key="card.label" class="rounded-2xl p-3.5 border border-gray-100 bg-white">
        <p class="text-[11px] uppercase tracking-wide font-medium rounded-md inline-block px-1.5 py-0.5" :class="card.cls">
          {{ card.label }}
        </p>
        <div class="mt-1.5">
          <CurrencyDisplay :value="card.value" size="lg" />
        </div>
        <p v-if="card.note" class="text-xs text-gray-400 mt-0.5">{{ card.note }}</p>
      </div>
    </div>

    <!-- Month by month: tap a bar to show only that month -->
    <div v-if="monthBars.length > 1" class="rounded-2xl border border-gray-100 bg-white p-3.5 sm:p-4 mb-4">
      <div class="flex items-center justify-between gap-3 mb-3">
        <p class="text-sm font-semibold text-gray-900">
          Month by month
          <span class="font-normal text-gray-400">· tap a month to show only its services</span>
        </p>
        <button
          v-if="activeMonth"
          type="button"
          class="text-xs font-semibold text-brand-700 hover:underline cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 rounded"
          @click="month = null"
        >
          Show all months
        </button>
      </div>
      <div class="flex items-end gap-1 sm:gap-2 h-28">
        <button
          v-for="b in monthBars"
          :key="b.key"
          type="button"
          class="group flex-1 min-w-0 h-full flex flex-col justify-end items-center gap-1 cursor-pointer focus:outline-none"
          :aria-pressed="activeMonth === b.key"
          :aria-label="`${b.name}: ${peso.format(b.total)} from ${b.count} services${b.current ? ', month still in progress' : ''}`"
          :title="`${b.name}: ${peso.format(b.total)} · ${b.sundays} Sunday${b.sundays === 1 ? '' : 's'}`"
          @click="month = activeMonth === b.key ? null : b.key"
        >
          <span class="hidden sm:block text-[10px] font-medium tabular-nums" :class="activeMonth === b.key ? 'text-brand-700' : 'text-gray-500'">{{ compact(b.total) }}</span>
          <span
            class="w-full max-w-10 rounded-t-md transition-colors group-focus-visible:ring-2 group-focus-visible:ring-brand-500 group-focus-visible:ring-offset-1"
            :class="[
              activeMonth === b.key ? 'bg-brand-600' : activeMonth ? 'bg-gray-200 group-hover:bg-brand-300' : 'bg-brand-400 group-hover:bg-brand-600',
              b.current && activeMonth !== b.key ? 'opacity-60' : '',
            ]"
            :style="{ height: b.pct + '%' }"
          />
          <span class="text-[10px] sm:text-[11px] font-medium" :class="activeMonth === b.key ? 'text-brand-700 font-bold' : 'text-gray-500'">{{ b.short }}</span>
        </button>
      </div>
      <p v-if="monthBars.some((b) => b.current)" class="mt-2 text-[11px] text-gray-400">The paler bar is the current month — still in progress.</p>
    </div>

    <!-- Drafts waiting to be submitted -->
    <div
      v-if="drafts.length"
      class="mb-4 p-3 rounded-xl border border-amber-200 bg-amber-50 text-sm text-amber-900 flex flex-wrap items-center justify-between gap-2"
    >
      <span>
        <b>{{ drafts.length }} draft{{ drafts.length === 1 ? "" : "s" }}</b>
        not yet submitted — {{ drafts.length === 1 ? "it is" : "they are" }} not in the totals or the ledger until submitted.
      </span>
      <button
        type="button"
        class="text-xs font-semibold px-3 py-1.5 rounded-lg bg-white border border-amber-300 text-amber-900 hover:bg-amber-100 cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500"
        :aria-pressed="draftsOnly"
        @click="draftsOnly = !draftsOnly"
      >
        {{ draftsOnly ? "Show everything" : "Show drafts only" }}
      </button>
    </div>

    <!-- Error banner -->
    <div v-if="error" class="mb-4 p-3 bg-red-50 text-red-700 rounded-xl text-sm flex items-center gap-2">
      <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
      </svg>
      {{ error.message }}
    </div>

    <!-- Loading -->
    <div v-if="loading" class="bg-white rounded-2xl border border-gray-100 p-4 space-y-3">
      <div v-for="i in 6" :key="i" class="h-4 bg-gray-100 rounded-lg animate-pulse" :class="i % 2 ? 'w-2/3' : 'w-full'" />
    </div>

    <!-- Empty -->
    <div v-else-if="!groups.length" class="bg-white rounded-2xl border border-gray-100 flex flex-col items-center gap-2 py-16">
      <svg class="w-10 h-10 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z" />
      </svg>
      <span class="text-sm text-gray-400">{{ emptyText }}</span>
    </div>

    <template v-else>
      <!-- Desktop / tablet: one table, a subtotal row per month -->
      <div class="hidden sm:block bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        <div class="overflow-x-auto">
          <table class="min-w-full">
            <thead class="bg-gray-50/80">
              <tr class="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">
                <th scope="col" class="px-5 py-3 text-left">Service</th>
                <th scope="col" class="px-5 py-3 text-left">Status</th>
                <th scope="col" class="px-5 py-3 text-right hidden lg:table-cell">Tithes</th>
                <th scope="col" class="px-5 py-3 text-right hidden lg:table-cell">Offering</th>
                <th scope="col" class="px-5 py-3 text-right hidden lg:table-cell">Mission</th>
                <th scope="col" class="px-5 py-3 text-right">Grand Total</th>
              </tr>
            </thead>
            <tbody v-for="g in groups" :key="g.key" class="divide-y divide-gray-50 border-t border-gray-100">
              <tr class="bg-gray-50/60">
                <th scope="colgroup" colspan="2" class="px-5 py-2.5 text-left">
                  <span class="text-sm font-bold text-gray-900">{{ g.label }}</span>
                  <span class="ml-2 text-xs font-normal text-gray-500">{{ g.sundays }} Sunday{{ g.sundays === 1 ? "" : "s" }} · {{ g.count }} service{{ g.count === 1 ? "" : "s" }}</span>
                </th>
                <td colspan="3" class="hidden lg:table-cell" />
                <td class="px-5 py-2.5 text-right whitespace-nowrap">
                  <span class="text-[10px] uppercase tracking-wide font-medium text-gray-400 mr-1.5">Month</span>
                  <CurrencyDisplay :value="g.total" weight="bold" />
                </td>
              </tr>
              <tr
                v-for="row in g.rows"
                :key="row.name"
                class="hover:bg-gray-50/70 transition-colors cursor-pointer active:bg-gray-100 focus:outline-none focus-visible:bg-brand-50"
                :class="row.docstatus === 2 ? 'opacity-50' : ''"
                tabindex="0"
                @click="goTo(row)"
                @keydown.enter="goTo(row)"
              >
                <td class="px-5 py-3 whitespace-nowrap text-sm">
                  <div class="flex items-center gap-2">
                    <span class="w-28" :class="row.firstOfDay ? 'font-semibold text-gray-900' : 'text-gray-300'">{{ fmtDate(row.day) }}</span>
                    <span class="text-[10px] px-2 py-0.5 rounded-full font-black tracking-wider" :class="tagClass(row.tag)">{{ row.tag }}</span>
                  </div>
                </td>
                <td class="px-5 py-3 whitespace-nowrap"><StatusBadge :status="statusLabel(row.docstatus)" /></td>
                <td class="px-5 py-3 whitespace-nowrap text-right hidden lg:table-cell"><CurrencyDisplay :value="row.all_tithes_total" /></td>
                <td class="px-5 py-3 whitespace-nowrap text-right hidden lg:table-cell"><CurrencyDisplay :value="row.all_offering_total" /></td>
                <td class="px-5 py-3 whitespace-nowrap text-right hidden lg:table-cell"><CurrencyDisplay :value="row.all_mission_total" /></td>
                <td class="px-5 py-3 whitespace-nowrap text-right">
                  <CurrencyDisplay :value="row.all_grand_total" weight="bold" />
                  <p v-if="row.dayTotal !== null" class="text-[11px] text-gray-400 mt-0.5">Sunday total {{ peso.format(row.dayTotal) }}</p>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Mobile: cards under a month heading -->
      <div class="sm:hidden space-y-5">
        <section v-for="g in groups" :key="g.key" :aria-label="g.label">
          <div class="flex items-end justify-between gap-3 px-1 mb-2">
            <div>
              <h2 class="text-sm font-bold text-gray-900">{{ g.label }}</h2>
              <p class="text-[11px] text-gray-500">{{ g.sundays }} Sunday{{ g.sundays === 1 ? "" : "s" }} · {{ g.count }} service{{ g.count === 1 ? "" : "s" }}</p>
            </div>
            <CurrencyDisplay :value="g.total" weight="bold" />
          </div>
          <div class="space-y-2.5">
            <div
              v-for="row in g.rows"
              :key="row.name"
              class="bg-white rounded-2xl border border-gray-100 p-4 transition-all active:bg-gray-50 active:scale-[0.99] cursor-pointer"
              :class="row.docstatus === 2 ? 'opacity-50' : ''"
              role="link"
              tabindex="0"
              @click="goTo(row)"
              @keydown.enter="goTo(row)"
            >
              <div class="flex items-center justify-between">
                <div class="min-w-0">
                  <p class="font-semibold text-gray-900 text-sm truncate">{{ fmtDate(row.day) }}</p>
                  <span class="text-[10px] px-2 py-0.5 rounded-full font-black tracking-wider inline-block mt-1" :class="tagClass(row.tag)">{{ row.tag }}</span>
                </div>
                <div class="flex items-center gap-2">
                  <StatusBadge :status="statusLabel(row.docstatus)" />
                  <svg class="w-4 h-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                  </svg>
                </div>
              </div>
              <div class="grid grid-cols-3 gap-2 pt-3 mt-3 border-t border-gray-100">
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
              <p v-if="row.dayTotal !== null" class="mt-2 text-[11px] text-gray-400 text-right">Sunday total {{ peso.format(row.dayTotal) }}</p>
            </div>
          </div>
        </section>
      </div>
    </template>
  </div>
</template>
