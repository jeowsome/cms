<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useQuery } from "@pinia/colada";
import { call } from "@/composables/useFrappeApi";
import { usePersistedRef } from "@/composables/usePersistedRef";
import PageHeader from "@/components/PageHeader.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import CurrencyDisplay from "@/components/CurrencyDisplay.vue";
import AppButton from "@/components/AppButton.vue";
import YearSwitcher from "@/components/YearSwitcher.vue";

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const MIN_YEAR = 2026; // the API only lists 2026 onwards

const router = useRouter();
// "scroll": every month of the year in one list; "month": one month at a time.
// Remembered on this device so the list opens the way it was left.
const viewMode = usePersistedRef("cm-collections-view", "scroll");
// Year and month are kept for the browser tab, so opening a collection and
// coming back lands on the same place.
const pickedYear = usePersistedRef("cm-collections-year", null, "session");
const pickedMonth = usePersistedRef("cm-collections-month", null, "session"); // "2026-11"
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
function monthName(ym) {
  return MONTHS[Number(String(ym).slice(5, 7)) - 1] || ym;
}

// "2026-07-12 MORNING" → day + service tag; the name is the reliable source of both.
const allRows = computed(() =>
  (collections.value || []).map((c) => {
    const [day, ...rest] = String(c.name).split(" ");
    return { ...c, day, tag: rest.join(" "), ym: day.slice(0, 7), year: Number(day.slice(0, 4)) };
  })
);

const nowYear = new Date().getFullYear();
// Years with records plus the current one, so a new year is reachable before
// its first collection is entered.
const years = computed(() =>
  [...new Set([...allRows.value.map((r) => r.year), nowYear])].filter((y) => y >= MIN_YEAR).sort((a, b) => b - a)
);
const year = computed({
  get: () => (years.value.includes(pickedYear.value) ? pickedYear.value : years.value.includes(nowYear) ? nowYear : years.value[0]),
  set: (y) => {
    pickedYear.value = y;
    pickedMonth.value = null;
  },
});
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

const now = new Date();
const nowKey = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;

// One bar per month of the year with records, oldest first.
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
  return bars.map((b, i) => {
    const name = monthName(b.key);
    const prev = bars[i - 1];
    return {
      ...b,
      name,
      short: name.slice(0, 3),
      sundays: b.days.size,
      pct: Math.max((b.total / max) * 100, 3),
      current: b.key === nowKey,
      change: prev && prev.total ? (b.total - prev.total) / prev.total : null,
      prevShort: prev ? monthName(prev.key).slice(0, 3) : null,
    };
  });
});

// Months of the year that can be paged through: every month with records,
// plus the current month in the current year so a new month opens empty.
const monthKeys = computed(() => {
  const keys = new Set(yearRows.value.map((r) => r.ym));
  if (year.value === nowYear) keys.add(nowKey);
  return [...keys].sort();
});

// Month view: the chosen month, defaulting to the latest one
const activeMonth = computed(() =>
  monthKeys.value.includes(pickedMonth.value) ? pickedMonth.value : monthKeys.value[monthKeys.value.length - 1] || null
);

function monthsOf(y) {
  return [...new Set(allRows.value.filter((r) => r.year === y).map((r) => r.ym))].sort();
}

// Paging past either end of the year moves into the neighbouring year.
const monthStep = computed(() => {
  const i = monthKeys.value.indexOf(activeMonth.value);
  const sortedYears = [...years.value].sort((a, b) => a - b);
  const yi = sortedYears.indexOf(year.value);
  let prev = null;
  let next = null;
  if (i > 0) prev = { year: year.value, key: monthKeys.value[i - 1] };
  else if (yi > 0) {
    const y = sortedYears[yi - 1];
    const ms = monthsOf(y);
    if (ms.length) prev = { year: y, key: ms[ms.length - 1] };
  }
  if (i >= 0 && i < monthKeys.value.length - 1) next = { year: year.value, key: monthKeys.value[i + 1] };
  else if (yi >= 0 && yi < sortedYears.length - 1) {
    const y = sortedYears[yi + 1];
    const ms = monthsOf(y);
    next = { year: y, key: ms[0] || (y === nowYear ? nowKey : null) };
    if (!next.key) next = null;
  }
  return { prev, next };
});

function goMonth(step) {
  if (!step) return;
  pickedYear.value = step.year;
  pickedMonth.value = step.key;
}

// Scroll view: the month whose section is at the top of the screen
const inViewMonth = ref(null);

// The bar the chart highlights follows whichever view is in use
const highlighted = computed(() => (viewMode.value === "month" ? activeMonth.value : inViewMonth.value));
const highlightedBar = computed(() => monthBars.value.find((b) => b.key === highlighted.value) || null);

// Trend line over the bars: x at each bar's centre, y at its top (0–100 box).
// Each segment is coloured by direction; the one into the current, unfinished
// month is dashed.
const trend = computed(() => {
  const n = monthBars.value.length;
  const pts = monthBars.value.map((b, i) => ({ x: ((i + 0.5) / n) * 100, y: 100 - b.pct, total: b.total, current: b.current }));
  return pts.slice(1).map((p, i) => ({
    x1: pts[i].x,
    y1: pts[i].y,
    x2: p.x,
    y2: p.y,
    up: p.total >= pts[i].total,
    partial: p.current,
  }));
});

function pctText(change) {
  return `${Math.abs(Math.round(change * 100))}%`;
}

function onBarClick(b) {
  if (viewMode.value === "month") {
    pickedMonth.value = b.key;
  } else {
    scrollToMonth(b.key);
  }
}

// The list: newest first, grouped by month with a subtotal, and each Sunday's
// services kept together with a combined total when there are two.
const groups = computed(() => {
  let rows = yearRows.value;
  if (viewMode.value === "month") rows = rows.filter((r) => r.ym === activeMonth.value);
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
      g = { key: r.ym, label: `${monthName(r.ym)} ${r.ym.slice(0, 4)}`, rows: [], total: 0, count: 0, days: new Set() };
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

// Month view header: the chosen month's counted totals (unaffected by the
// drafts filter), and zeros for a month with nothing entered yet.
const activeGroup = computed(() => {
  const key = activeMonth.value;
  const bar = monthBars.value.find((m) => m.key === key);
  return {
    label: key ? `${monthName(key)} ${key.slice(0, 4)}` : "",
    total: bar?.total || 0,
    count: bar?.count || 0,
    sundays: bar?.sundays || 0,
  };
});

const emptyText = computed(() => {
  if (draftsOnly.value) return "No drafts — every collection is submitted";
  if (viewMode.value === "month" && activeMonth.value) return `No collections recorded in ${monthName(activeMonth.value)} yet`;
  return `No collections recorded in ${year.value} yet`;
});

function tagClass(tag) {
  return tag === "MORNING" ? "bg-amber-50 text-amber-700" : "bg-indigo-50 text-indigo-700";
}

function goTo(row) {
  router.push({ name: "CollectionForm", params: { name: row.name } });
}

// ── Scroll view: month tracking + floating month indicator ────────────────
// The app scrolls inside #main-scroll-area, not the window.
let scroller = null;
const indicator = ref({ show: false, top: 0 });
let hideTimer = null;
let frame = 0;
const SCROLL_KEY = "cm-collections-scroll";

function sectionEls() {
  return [...document.querySelectorAll("[data-month-section]")];
}

function updateInView() {
  frame = 0;
  if (!scroller || viewMode.value !== "scroll") return;
  const box = scroller.getBoundingClientRect();
  // A section is "in view" once its top passes a reading line near the top of
  // the screen. Over the last screenful of scrolling the line slides down to
  // the bottom edge, so the final (oldest) months — whose tops can never reach
  // the upper line — still become current in turn as the list bottoms out.
  const base = Math.min(160, box.height / 3);
  const remaining = scroller.scrollHeight - scroller.clientHeight - scroller.scrollTop;
  const line = box.top + base + Math.max(0, box.height - base - remaining);
  let current = null;
  for (const el of sectionEls()) {
    if (el.offsetParent === null) continue; // the hidden desktop/mobile copy
    if (el.getBoundingClientRect().top <= line) current = el.dataset.monthSection;
  }
  const visible = sectionEls().filter((el) => el.offsetParent !== null);
  inViewMonth.value = current || visible[0]?.dataset.monthSection || null;

  const range = scroller.scrollHeight - scroller.clientHeight;
  const progress = range > 0 ? scroller.scrollTop / range : 0;
  indicator.value = { show: true, top: box.top + 12 + progress * Math.max(box.height - 64, 0) };
  clearTimeout(hideTimer);
  hideTimer = setTimeout(() => (indicator.value = { ...indicator.value, show: false }), 900);
}

function onScroll() {
  if (!frame) frame = requestAnimationFrame(updateInView);
}

// The month just jumped to from the chart; its header flashes on arrival.
const flashMonth = ref(null);
let flashTimer = null;

function scrollToMonth(key) {
  const el = sectionEls().find((e) => e.dataset.monthSection === key && e.offsetParent !== null);
  if (!el || !scroller) return;
  const top = el.getBoundingClientRect().top - scroller.getBoundingClientRect().top + scroller.scrollTop - 8;
  scroller.scrollTo({ top, behavior: "smooth" });
  flashMonth.value = key;
  clearTimeout(flashTimer);
  flashTimer = setTimeout(() => (flashMonth.value = null), 1800);
}

// Header look for a month: the flashed one glows, the one in view is accented.
function headerState(key) {
  if (flashMonth.value === key) return "flash";
  return inViewMonth.value === key ? "active" : "idle";
}

const indicatorLabel = computed(() => (inViewMonth.value ? `${monthName(inViewMonth.value)} ${inViewMonth.value.slice(0, 4)}` : ""));

onMounted(() => {
  scroller = document.getElementById("main-scroll-area");
  scroller?.addEventListener("scroll", onScroll, { passive: true });
});

// Coming back from a collection in scroll view: restore where the list was.
const cameFromForm = String(window.history.state?.back || "").startsWith("/collections/");
let restored = false;
watch(
  () => !loading.value && groups.value.length,
  async (ready) => {
    if (!ready || restored) return;
    restored = true;
    await nextTick();
    let saved = null;
    try {
      saved = Number(sessionStorage.getItem(SCROLL_KEY));
    } catch {}
    if (cameFromForm && viewMode.value === "scroll" && scroller && saved) scroller.scrollTop = saved;
    updateInView();
    indicator.value.show = false;
  },
  { immediate: true }
);

watch([viewMode, year], async () => {
  await nextTick();
  updateInView();
  indicator.value.show = false;
});

onBeforeUnmount(() => {
  try {
    if (scroller) sessionStorage.setItem(SCROLL_KEY, String(scroller.scrollTop));
  } catch {}
  scroller?.removeEventListener("scroll", onScroll);
  clearTimeout(hideTimer);
  clearTimeout(flashTimer);
  if (frame) cancelAnimationFrame(frame);
});
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

    <!-- Year + how the list is shown -->
    <div class="flex flex-wrap items-center justify-between gap-2 mb-4">
      <YearSwitcher v-model="year" :years="years" />
      <div class="inline-flex p-1 rounded-xl bg-gray-100 text-sm font-medium" role="group" aria-label="List view">
        <button
          v-for="v in [{ key: 'scroll', label: 'Scroll' }, { key: 'month', label: 'By month' }]"
          :key="v.key"
          type="button"
          class="px-3 py-1.5 rounded-lg transition-colors cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
          :class="viewMode === v.key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'"
          :aria-pressed="viewMode === v.key"
          @click="viewMode = v.key"
        >
          {{ v.label }}
        </button>
      </div>
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

    <!-- Month by month: bars with a trend line. The highlighted bar follows the
         view — the chosen month, or the month scrolled into view. -->
    <div v-if="monthBars.length" class="isolate rounded-2xl border border-gray-100 bg-white p-3.5 sm:p-4 mb-4">
      <div class="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 mb-3">
        <p class="text-sm font-semibold text-gray-900">
          Month by month
          <span class="font-normal text-gray-400">· tap a month to {{ viewMode === "month" ? "open it" : "jump to it" }}</span>
        </p>
        <p v-if="highlightedBar" class="text-xs text-gray-500 tabular-nums">
          <span class="font-semibold text-gray-900">{{ highlightedBar.name }}</span>
          {{ peso.format(highlightedBar.total) }}<template v-if="highlightedBar.current"> so far</template>
          <span
            v-if="highlightedBar.change !== null"
            class="ml-1 font-semibold"
            :class="highlightedBar.change >= 0 ? 'text-green-700' : 'text-red-600'"
          >
            {{ highlightedBar.change >= 0 ? "▲" : "▼" }} {{ pctText(highlightedBar.change) }}
            <span class="font-normal text-gray-400">vs {{ highlightedBar.prevShort }}</span>
          </span>
        </p>
      </div>
      <div class="relative flex">
        <!-- Trend line, drawn over the bar area (below the 16px value labels) -->
        <svg
          v-if="trend.length"
          class="pointer-events-none absolute inset-x-0 top-4 h-24 w-full overflow-visible z-10"
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          <line
            v-for="(seg, i) in trend"
            :key="i"
            :x1="seg.x1" :y1="seg.y1" :x2="seg.x2" :y2="seg.y2"
            :class="seg.up ? 'stroke-green-600' : 'stroke-red-500'"
            stroke-width="2"
            stroke-linecap="round"
            :stroke-dasharray="seg.partial ? '4 3' : null"
            vector-effect="non-scaling-stroke"
          />
        </svg>
        <button
          v-for="b in monthBars"
          :key="b.key"
          type="button"
          class="group flex-1 min-w-0 px-0.5 sm:px-1 flex flex-col items-center cursor-pointer focus:outline-none"
          :aria-pressed="highlighted === b.key"
          :aria-label="`${b.name}: ${peso.format(b.total)} from ${b.count} services${b.change !== null ? `, ${b.change >= 0 ? 'up' : 'down'} ${pctText(b.change)} from ${b.prevShort}` : ''}${b.current ? ', month still in progress' : ''}`"
          :title="`${b.name}: ${peso.format(b.total)} · ${b.sundays} Sunday${b.sundays === 1 ? '' : 's'}`"
          @click="onBarClick(b)"
        >
          <span
            class="h-4 leading-4 text-[10px] font-medium tabular-nums whitespace-nowrap"
            :class="[highlighted === b.key ? 'text-brand-700 font-bold' : 'text-gray-500 invisible sm:visible']"
          >{{ compact(b.total) }}</span>
          <span class="relative w-full h-24 flex items-end justify-center">
            <span
              class="w-full max-w-10 rounded-t-md transition-colors group-focus-visible:ring-2 group-focus-visible:ring-brand-500 group-focus-visible:ring-offset-1"
              :class="[
                highlighted === b.key ? 'bg-brand-600' : highlighted ? 'bg-brand-200 group-hover:bg-brand-300' : 'bg-brand-400 group-hover:bg-brand-600',
                b.current && highlighted !== b.key ? 'opacity-60' : '',
              ]"
              :style="{ height: b.pct + '%' }"
            />
            <!-- Trend point at the top of the bar -->
            <span
              class="pointer-events-none absolute left-1/2 z-20 w-2 h-2 -translate-x-1/2 translate-y-1/2 rounded-full bg-white border-2"
              :class="highlighted === b.key ? 'border-brand-800' : 'border-gray-500'"
              :style="{ bottom: b.pct + '%' }"
            />
          </span>
          <span class="h-5 leading-5 text-[10px] sm:text-[11px] font-medium" :class="highlighted === b.key ? 'text-brand-700 font-bold' : 'text-gray-500'">{{ b.short }}</span>
        </button>
      </div>
      <p class="mt-2 text-[11px] text-gray-400">
        The line turns <span class="font-semibold text-green-700">green</span> when a month is up on the one before and
        <span class="font-semibold text-red-600">red</span> when it is down<template v-if="monthBars.some((b) => b.current)">; the dashed part and paler bar are the current month, still in progress</template>.
      </p>
    </div>

    <!-- Month view: step through months (and into the next/previous year) -->
    <div
      v-if="viewMode === 'month' && activeMonth"
      class="sticky top-0 z-20 -mx-4 sm:mx-0 px-4 sm:px-0 py-2 mb-2 bg-gray-50/95 backdrop-blur"
    >
      <div class="flex items-center gap-2 rounded-2xl border border-gray-100 bg-white p-1.5 shadow-sm">
        <button
          type="button"
          class="w-10 h-10 shrink-0 flex items-center justify-center rounded-xl text-gray-500 hover:bg-gray-50 hover:text-gray-900 disabled:text-gray-200 disabled:hover:bg-transparent cursor-pointer disabled:cursor-default focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
          :disabled="!monthStep.prev"
          :aria-label="monthStep.prev ? `Previous month: ${monthName(monthStep.prev.key)} ${monthStep.prev.year}` : 'No earlier month'"
          @click="goMonth(monthStep.prev)"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" /></svg>
        </button>
        <div class="flex-1 min-w-0 text-center" aria-live="polite">
          <p class="text-sm font-bold text-gray-900">{{ activeGroup.label }}</p>
          <p class="text-[11px] text-gray-500 tabular-nums">
            {{ activeGroup.sundays }} Sunday{{ activeGroup.sundays === 1 ? "" : "s" }} · {{ activeGroup.count }} service{{ activeGroup.count === 1 ? "" : "s" }} ·
            <span class="font-semibold text-gray-900">{{ peso.format(activeGroup.total) }}</span>
          </p>
        </div>
        <button
          type="button"
          class="w-10 h-10 shrink-0 flex items-center justify-center rounded-xl text-gray-500 hover:bg-gray-50 hover:text-gray-900 disabled:text-gray-200 disabled:hover:bg-transparent cursor-pointer disabled:cursor-default focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
          :disabled="!monthStep.next"
          :aria-label="monthStep.next ? `Next month: ${monthName(monthStep.next.key)} ${monthStep.next.year}` : 'No later month'"
          @click="goMonth(monthStep.next)"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" /></svg>
        </button>
      </div>
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
            <tbody v-for="g in groups" :key="g.key" :data-month-section="g.key" class="divide-y divide-gray-50 border-t border-gray-100">
              <tr
                v-if="viewMode === 'scroll'"
                class="transition-colors duration-500"
                :class="{ flash: 'bg-brand-100', active: 'bg-brand-50', idle: 'bg-gray-100/70' }[headerState(g.key)]"
              >
                <th
                  scope="colgroup"
                  colspan="2"
                  class="px-5 py-3 text-left border-l-4 transition-colors duration-500"
                  :class="headerState(g.key) === 'idle' ? 'border-gray-300' : 'border-brand-600'"
                >
                  <span class="text-base font-bold" :class="headerState(g.key) === 'idle' ? 'text-gray-900' : 'text-brand-800'">{{ g.label }}</span>
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
        <section v-for="g in groups" :key="g.key" :data-month-section="g.key" :aria-label="g.label">
          <div v-if="viewMode === 'scroll'" class="sticky top-0 z-10 -mx-4 px-4 py-2 mb-1 bg-gray-50/95 backdrop-blur">
            <div
              class="flex items-center justify-between gap-3 rounded-xl border border-l-4 px-3 py-2 shadow-sm transition-all duration-500"
              :class="{
                flash: 'bg-brand-100 border-brand-400 border-l-brand-600 ring-4 ring-brand-200',
                active: 'bg-brand-50 border-brand-200 border-l-brand-600',
                idle: 'bg-white border-gray-200 border-l-gray-300',
              }[headerState(g.key)]"
            >
            <div>
              <h2 class="text-base font-bold" :class="headerState(g.key) === 'idle' ? 'text-gray-900' : 'text-brand-800'">{{ g.label }}</h2>
              <p class="text-[11px] text-gray-500">{{ g.sundays }} Sunday{{ g.sundays === 1 ? "" : "s" }} · {{ g.count }} service{{ g.count === 1 ? "" : "s" }}</p>
            </div>
            <CurrencyDisplay :value="g.total" weight="bold" />
            </div>
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

    <!-- Month indicator beside the scrollbar while scrolling (scroll view) -->
    <Teleport to="body">
      <div
        v-if="viewMode === 'scroll' && indicatorLabel"
        class="pointer-events-none fixed right-4 z-40 rounded-full bg-gray-900/90 px-3 py-1.5 text-xs font-bold text-white shadow-lg transition-opacity duration-300"
        :class="indicator.show ? 'opacity-100' : 'opacity-0'"
        :style="{ top: indicator.top + 'px' }"
        aria-hidden="true"
      >
        {{ indicatorLabel }}
      </div>
    </Teleport>
  </div>
</template>
