<script setup>
import { computed, ref, watch } from "vue";
import { useQuery } from "@pinia/colada";
import { call } from "@/composables/useFrappeApi";
import { usePersistedRef } from "@/composables/usePersistedRef";
import AppButton from "@/components/AppButton.vue";
import ActivityModal from "@/components/ActivityModal.vue";
import {
  MONTHS, PART_OF_SERVICE, REPLACES, byDay, deptColor, deptShort, fmtDate, fmtRange, fmtTime,
  monthGrid, servicesOn, todayIso,
} from "@/utils/calendar";

/**
 * The church calendar. `publicView` is the members' page (no login): only
 * confirmed public activities, read-only. Planners also see proposed
 * activities, conflicts and budgets, and add or edit their departments'.
 */
const props = defineProps({ publicView: { type: Boolean, default: false } });
// Served by Frappe from the app's public folder, not bundled by Vite.
const LOGO = "/assets/church_management/images/jbc-logo-192.png";

const now = new Date();
const year = ref(now.getFullYear());
const month = ref(now.getMonth());
const view = usePersistedRef(props.publicView ? "cm-cal-view-public" : "cm-cal-view", "month");
const showProposed = usePersistedRef("cm-cal-proposed", true);
const hidden = ref(new Set()); // departments filtered out
const selectedDay = ref(todayIso());

const { data, isPending, error, refetch } = useQuery({
  key: () => ["church-calendar", year.value, props.publicView, showProposed.value],
  query: () =>
    call("church_management.api.church_calendar.get_calendar", {
      from_date: `${year.value}-01-01`,
      to_date: `${year.value}-12-31`,
      include_proposed: !props.publicView && showProposed.value ? 1 : 0,
    }),
});
const planner = computed(() => !props.publicView && !!data.value?.planner);
const yearPublished = computed(() => (data.value?.published_years || []).includes(year.value));

const { data: options } = useQuery({
  key: ["planner-options"],
  query: () => call("church_management.api.church_calendar.get_planner_options"),
  enabled: () => planner.value,
});
const { data: pending, refetch: refetchPending } = useQuery({
  key: ["pending-approvals"],
  query: () => call("church_management.api.church_calendar.pending_approvals"),
  enabled: () => planner.value,
});

const activities = computed(() => (data.value?.activities || []).filter((a) => !hidden.value.has(a.department)));
const days = computed(() => byDay(activities.value));
const usedDepartments = computed(() => [...new Set((data.value?.activities || []).map((a) => a.department))].sort());

function toggleDept(d) {
  const s = new Set(hidden.value);
  s.has(d) ? s.delete(d) : s.add(d);
  hidden.value = s;
}
function onlyDept(d) {
  hidden.value = new Set(usedDepartments.value.filter((x) => x !== d));
}

// ---------- navigation
function step(n) {
  if (view.value === "year") {
    year.value += n;
    return;
  }
  let m = month.value + n;
  let y = year.value;
  if (m < 0) { m = 11; y--; }
  if (m > 11) { m = 0; y++; }
  month.value = m;
  year.value = y;
}
function goToday() {
  year.value = now.getFullYear();
  month.value = now.getMonth();
  selectedDay.value = todayIso();
}
const title = computed(() => (view.value === "year" ? String(year.value) : `${MONTHS[month.value]} ${year.value}`));

const grid = computed(() => monthGrid(year.value, month.value));
const yearGrids = computed(() => MONTHS.map((name, m) => ({ name, m, cells: monthGrid(year.value, m) })));

const listMonths = computed(() => {
  const out = [];
  const months = view.value === "list" ? [...Array(12).keys()] : [month.value];
  for (const m of months) {
    const prefix = `${year.value}-${String(m + 1).padStart(2, "0")}`;
    const items = activities.value
      .filter((a) => a.start_date.startsWith(prefix) || (a.start_date < prefix && (a.end_date || a.start_date) >= prefix))
      .sort((a, b) => (a.start_date + (a.start_time || "")).localeCompare(b.start_date + (b.start_time || "")));
    if (items.length) out.push({ name: MONTHS[m], items });
  }
  return out;
});

const dayItems = computed(() => days.value[selectedDay.value] || []);
const dayServices = computed(() => servicesOn(selectedDay.value, data.value?.services, data.value?.replaced));

function servicesFor(date) {
  return servicesOn(date, data.value?.services, data.value?.replaced);
}
function chipClass(a) {
  const c = deptColor(a.department);
  return [
    c.chip,
    "ring-1",
    a.status === "Proposed" ? "border border-dashed border-gray-400" : "",
    a.status === "Cancelled" ? "line-through opacity-60" : "",
    a.status === "Done" ? "opacity-70" : "",
    a.conflicts?.length ? "!ring-2 !ring-red-500" : "",
  ];
}

// ---------- editing
const modal = ref({ open: false, activity: null, defaults: {} });
function openNew(date) {
  if (!planner.value) {
    selectedDay.value = date;
    return;
  }
  modal.value = { open: true, activity: null, defaults: { start_date: date } };
}
function openActivity(a) {
  if (!planner.value) {
    detail.value = a;
    return;
  }
  modal.value = { open: true, activity: a, defaults: {} };
}
function onSaved() {
  modal.value.open = false;
  refetch();
  refetchPending();
}
const detail = ref(null);

function selectDay(date) {
  selectedDay.value = date;
}
watch(view, (v) => {
  if (v === "month") {
    const [y, m] = selectedDay.value.split("-").map(Number);
    if (y === year.value) month.value = m - 1;
  }
});
function openMonth(m) {
  month.value = m;
  view.value = "month";
}
</script>

<template>
  <div :class="publicView ? 'min-h-screen bg-slate-50 h-screen overflow-y-auto' : ''">
    <!-- Public header -->
    <header v-if="publicView" class="bg-gradient-to-br from-emerald-900 to-emerald-950 text-white">
      <div class="max-w-6xl mx-auto px-4 py-5 flex items-center gap-3">
        <img :src="LOGO" alt="" class="w-11 h-11 rounded-full ring-4 ring-white/10" />
        <div>
          <h1 class="text-lg sm:text-xl font-bold leading-tight">Church Calendar</h1>
          <p class="text-xs text-emerald-200">Jezreel Baptist Church Pasig · Sunday worship 9:00 AM and 6:00 PM</p>
        </div>
      </div>
    </header>

    <div class="px-4 sm:px-6 py-4 sm:py-6 max-w-6xl mx-auto w-full">
      <!-- Toolbar -->
      <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-3 mb-4">
        <div class="flex items-center gap-2">
          <h1 v-if="!publicView" class="text-xl sm:text-2xl font-bold text-gray-900 mr-2">Calendar</h1>
          <div class="inline-flex items-center rounded-xl bg-white border border-gray-200 shadow-sm">
            <button class="w-9 h-9 flex items-center justify-center text-gray-500 hover:text-gray-900" aria-label="Previous" @click="step(-1)">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" /></svg>
            </button>
            <span class="min-w-[9.5rem] text-center font-bold text-gray-900 text-sm" aria-live="polite">{{ title }}</span>
            <button class="w-9 h-9 flex items-center justify-center text-gray-500 hover:text-gray-900" aria-label="Next" @click="step(1)">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" /></svg>
            </button>
          </div>
          <AppButton size="sm" variant="secondary" @click="goToday">Today</AppButton>
        </div>
        <div class="flex items-center gap-2 flex-wrap">
          <div class="inline-flex rounded-xl bg-gray-100 p-0.5 text-xs font-semibold" role="tablist">
            <button v-for="v in ['month', 'year', 'list']" :key="v" role="tab" :aria-selected="view === v"
                    class="px-3 py-1.5 rounded-lg capitalize" :class="view === v ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500'" @click="view = v">{{ v }}</button>
          </div>
          <label v-if="planner" class="inline-flex items-center gap-1.5 text-xs text-gray-600">
            <input v-model="showProposed" type="checkbox" class="rounded border-gray-300" /> Proposed
          </label>
          <AppButton v-if="planner" size="sm" @click="openNew(selectedDay)">+ Activity</AppButton>
        </div>
      </div>

      <!-- Publish state -->
      <div v-if="data && !yearPublished && !planner" class="mb-4 p-3 rounded-2xl bg-amber-50 border border-amber-100 text-sm text-amber-900">
        The {{ year }} church calendar hasn't been published yet. Worship services are shown; activities appear once the church publishes them.
      </div>
      <div v-else-if="data && !yearPublished && planner" class="mb-4 p-3 rounded-2xl bg-amber-50 border border-amber-100 text-xs text-amber-900 flex flex-wrap items-center justify-between gap-2">
        <span>{{ year }} isn't published yet: members don't see these activities on the public calendar.</span>
        <router-link :to="`/gpoa/${year}`" class="font-semibold underline">Publish from GPOA {{ year }}</router-link>
      </div>

      <!-- Pastor approvals -->
      <div v-if="planner && pending?.length" class="mb-4 p-3 rounded-2xl bg-indigo-50 border border-indigo-100">
        <p class="text-xs font-bold text-indigo-900 mb-2">
          {{ pending.length }} {{ pending.length === 1 ? "activity asks" : "activities ask" }} to replace a worship service{{ options?.is_pastor ? " — your decision is needed" : " — waiting for the pastor" }}
        </p>
        <div class="flex flex-wrap gap-2">
          <button v-for="a in pending" :key="a.name" class="px-2.5 py-1 rounded-lg bg-white ring-1 ring-indigo-200 text-xs text-indigo-900 hover:bg-indigo-100" @click="openActivity(a)">
            {{ fmtDate(a.start_date) }} · {{ a.title }} <span class="text-indigo-500">({{ deptShort(a.department) }})</span>
          </button>
        </div>
      </div>

      <!-- Department legend / filter -->
      <div v-if="usedDepartments.length" class="flex flex-wrap gap-1.5 mb-4">
        <button v-for="d in usedDepartments" :key="d"
                class="inline-flex items-center gap-1.5 px-2 py-1 rounded-lg text-[11px] font-semibold ring-1 transition"
                :class="hidden.has(d) ? 'bg-white text-gray-400 ring-gray-200' : deptColor(d).chip"
                :title="`Click to show or hide. Double-click to show only ${d}.`"
                @click="toggleDept(d)" @dblclick="onlyDept(d)">
          <span class="w-2 h-2 rounded-full" :class="hidden.has(d) ? 'bg-gray-300' : deptColor(d).dot" />{{ deptShort(d) }}
        </button>
        <button v-if="hidden.size" class="text-[11px] font-semibold text-brand-700 px-2" @click="hidden = new Set()">Show all</button>
      </div>

      <div v-if="isPending" class="h-96 bg-white rounded-2xl border border-gray-100 animate-pulse" />
      <div v-else-if="error" class="p-4 bg-red-50 text-red-700 rounded-xl text-sm">{{ error.message }}</div>

      <!-- MONTH -->
      <template v-else-if="view === 'month'">
        <div class="bg-white rounded-2xl border border-gray-200 overflow-hidden">
          <div class="grid grid-cols-7 bg-gray-50 border-b border-gray-200 text-[11px] font-bold text-gray-500 uppercase">
            <div v-for="d in ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']" :key="d" class="px-2 py-2 text-center">{{ d }}</div>
          </div>
          <div class="grid grid-cols-7">
            <div v-for="c in grid" :key="c.date"
                 class="min-h-[4.5rem] sm:min-h-[7.5rem] border-b border-r border-gray-100 p-1 sm:p-1.5 cursor-pointer transition-colors"
                 :class="[c.inMonth ? 'bg-white hover:bg-gray-50' : 'bg-gray-50/60 text-gray-400', selectedDay === c.date ? '!bg-brand-50' : '']"
                 @click="selectDay(c.date)" @dblclick="openNew(c.date)">
              <div class="flex items-center justify-between">
                <span class="text-xs font-bold w-6 h-6 flex items-center justify-center rounded-full"
                      :class="c.date === todayIso() ? 'bg-brand-600 text-white' : ''">{{ c.day }}</span>
              </div>
              <!-- worship services -->
              <div class="hidden sm:block">
                <p v-for="s in servicesFor(c.date)" :key="s.name" class="text-[10px] leading-4 truncate" :class="s.replacedBy ? 'text-gray-300 line-through' : 'text-gray-400'">
                  ⛪ {{ fmtTime(s.start_time) }} {{ s.name.replace(' Worship', '') }}
                </p>
              </div>
              <!-- activities: chips on wide screens, dots on phones -->
              <div class="hidden sm:block space-y-0.5 mt-0.5">
                <button v-for="a in (days[c.date] || []).slice(0, 3)" :key="a.name"
                        class="w-full text-left px-1.5 py-0.5 rounded text-[11px] font-semibold truncate" :class="chipClass(a)"
                        :title="`${a.title} — ${a.department}`" @click.stop="openActivity(a)">
                  <span v-if="a.conflicts?.length" aria-label="Has conflicts">⚠ </span>{{ !a.all_day && a.start_time && a.start_date === c.date ? fmtTime(a.start_time) + " " : "" }}{{ a.title }}
                </button>
                <p v-if="(days[c.date] || []).length > 3" class="text-[10px] font-semibold text-gray-500 px-1">+{{ days[c.date].length - 3 }} more</p>
              </div>
              <div class="sm:hidden flex flex-wrap gap-0.5 mt-1">
                <span v-for="a in (days[c.date] || []).slice(0, 4)" :key="a.name" class="w-1.5 h-1.5 rounded-full" :class="deptColor(a.department).dot" />
              </div>
            </div>
          </div>
        </div>
        <p v-if="planner" class="text-[11px] text-gray-400 mt-2">Double-click a day to add an activity. Dashed = proposed, red ring = conflict.</p>

        <!-- Selected day -->
        <div class="mt-4 bg-white rounded-2xl border border-gray-200 p-4">
          <div class="flex items-center justify-between mb-2">
            <h3 class="text-sm font-bold text-gray-900">{{ fmtDate(selectedDay, { weekday: "long", month: "long", day: "numeric" }) }}</h3>
            <AppButton v-if="planner" size="sm" variant="secondary" @click="openNew(selectedDay)">+ Add on this day</AppButton>
          </div>
          <p v-for="s in dayServices" :key="s.name" class="text-xs py-1" :class="s.replacedBy ? 'text-gray-400 line-through' : 'text-gray-600'">
            ⛪ {{ fmtTime(s.start_time) }}–{{ fmtTime(s.end_time) }} {{ s.name }}<span v-if="s.replacedBy" class="no-underline"> — replaced by {{ s.replacedBy }}</span>
          </p>
          <p v-if="!dayItems.length && !dayServices.length" class="text-sm text-gray-400">Nothing scheduled.</p>
          <ul class="divide-y divide-gray-100">
            <li v-for="a in dayItems" :key="a.name">
              <button class="w-full text-left py-2 flex items-start gap-3 hover:bg-gray-50 rounded-lg px-1" @click="openActivity(a)">
                <span class="w-1 self-stretch rounded-full" :class="deptColor(a.department).dot" />
                <span class="min-w-0 flex-1">
                  <span class="block text-sm font-semibold text-gray-900">{{ a.title }}
                    <span v-if="a.status !== 'Confirmed'" class="ml-1 text-[10px] font-bold uppercase text-gray-400">{{ a.status }}</span>
                  </span>
                  <span class="block text-xs text-gray-500">{{ fmtRange(a) }} · {{ a.department }}<template v-if="a.venue || a.location_details"> · {{ a.venue || a.location_details }}</template></span>
                  <span v-if="a.service_relation === REPLACES" class="block text-[11px] text-indigo-700">Replaces the worship service{{ planner ? ` · pastor: ${a.pastor_approval || "not asked"}` : "" }}</span>
                  <span v-else-if="a.service_relation === PART_OF_SERVICE" class="block text-[11px] text-gray-400">During the worship service</span>
                  <span v-for="(c, i) in a.conflicts || []" :key="i" class="block text-[11px] text-red-600">⚠ {{ c.message }}</span>
                </span>
              </button>
            </li>
          </ul>
        </div>
      </template>

      <!-- YEAR -->
      <div v-else-if="view === 'year'" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <div v-for="g in yearGrids" :key="g.m" class="bg-white rounded-2xl border border-gray-200 p-3">
          <button class="text-sm font-bold text-gray-900 hover:text-brand-700 mb-2" @click="openMonth(g.m)">{{ g.name }}</button>
          <div class="grid grid-cols-7 text-[9px] text-gray-400 font-bold text-center mb-1">
            <span v-for="(d, i) in ['S', 'M', 'T', 'W', 'T', 'F', 'S']" :key="i">{{ d }}</span>
          </div>
          <div class="grid grid-cols-7 gap-y-0.5">
            <button v-for="c in g.cells" :key="c.date" class="h-9 flex flex-col items-center justify-start rounded-md pt-0.5"
                    :class="[c.inMonth ? 'hover:bg-gray-100' : 'invisible', selectedDay === c.date ? 'bg-brand-50' : '']"
                    :title="(days[c.date] || []).map((a) => `${a.title} (${deptShort(a.department)})`).join('\n')"
                    @click="selectDay(c.date)" @dblclick="openNew(c.date)">
              <span class="text-[11px] leading-4" :class="c.date === todayIso() ? 'font-bold text-brand-700' : 'text-gray-700'">{{ c.day }}</span>
              <span class="flex gap-px mt-0.5">
                <span v-for="a in (days[c.date] || []).slice(0, 4)" :key="a.name" class="w-1.5 h-1.5 rounded-full"
                      :class="[deptColor(a.department).dot, a.conflicts?.length ? 'ring-1 ring-red-500' : '', a.status === 'Proposed' ? 'opacity-50' : '']" />
              </span>
            </button>
          </div>
        </div>
        <div class="sm:col-span-2 lg:col-span-3 bg-white rounded-2xl border border-gray-200 p-4">
          <div class="flex items-center justify-between mb-2">
            <h3 class="text-sm font-bold text-gray-900">{{ fmtDate(selectedDay, { weekday: "long", month: "long", day: "numeric", year: "numeric" }) }}</h3>
            <AppButton v-if="planner" size="sm" variant="secondary" @click="openNew(selectedDay)">+ Add on this day</AppButton>
          </div>
          <p v-if="!dayItems.length" class="text-sm text-gray-400">Nothing scheduled.</p>
          <button v-for="a in dayItems" :key="a.name" class="w-full text-left py-1.5 text-sm flex items-center gap-2" @click="openActivity(a)">
            <span class="w-2 h-2 rounded-full" :class="deptColor(a.department).dot" />
            <span class="font-semibold">{{ a.title }}</span>
            <span class="text-xs text-gray-500">{{ deptShort(a.department) }} · {{ fmtRange(a) }}</span>
            <span v-if="a.conflicts?.length" class="text-xs text-red-600">⚠ {{ a.conflicts.length }}</span>
          </button>
        </div>
      </div>

      <!-- LIST -->
      <div v-else class="space-y-5">
        <p v-if="!listMonths.length" class="text-sm text-gray-400">Nothing scheduled in {{ year }}.</p>
        <section v-for="m in listMonths" :key="m.name">
          <h3 class="text-xs font-bold uppercase tracking-wide text-gray-500 mb-2">{{ m.name }}</h3>
          <div class="bg-white rounded-2xl border border-gray-200 divide-y divide-gray-100">
            <button v-for="a in m.items" :key="a.name" class="w-full text-left px-4 py-3 flex items-start gap-3 hover:bg-gray-50 border-l-4" :class="deptColor(a.department).bar" @click="openActivity(a)">
              <span class="w-14 shrink-0 text-center">
                <span class="block text-[10px] font-bold uppercase text-gray-400">{{ fmtDate(a.start_date, { weekday: "short" }) }}</span>
                <span class="block text-lg font-bold text-gray-900 leading-5">{{ Number(a.start_date.slice(8)) }}</span>
              </span>
              <span class="min-w-0 flex-1">
                <span class="block text-sm font-semibold text-gray-900">{{ a.title }}
                  <span v-if="a.status !== 'Confirmed'" class="ml-1 text-[10px] font-bold uppercase text-gray-400">{{ a.status }}</span>
                </span>
                <span class="block text-xs text-gray-500">{{ a.department }} · {{ fmtRange(a) }}<template v-if="a.venue || a.location_details"> · {{ a.venue || a.location_details }}</template></span>
                <span v-for="(c, i) in a.conflicts || []" :key="i" class="block text-[11px] text-red-600">⚠ {{ c.message }}</span>
              </span>
              <span v-if="planner && a.budget" class="text-xs font-semibold text-gray-600 tabular">₱{{ Number(a.budget).toLocaleString() }}</span>
            </button>
          </div>
        </section>
      </div>
    </div>

    <!-- Public detail -->
    <Teleport to="body">
      <div v-if="detail" class="fixed inset-0 z-[60] flex items-end sm:items-center justify-center sm:p-4" @click.self="detail = null">
        <div class="absolute inset-0 bg-gray-900/40" @click="detail = null" />
        <div class="relative bg-white rounded-t-2xl sm:rounded-2xl shadow-2xl w-full max-w-md p-5 anim-pop">
          <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-lg text-[11px] font-semibold ring-1" :class="deptColor(detail.department).chip">{{ detail.department }}</span>
          <h3 class="mt-2 text-lg font-bold text-gray-900">{{ detail.title }}</h3>
          <p class="text-sm text-gray-600 mt-1">{{ fmtRange(detail) }}</p>
          <p v-if="detail.venue || detail.location_details" class="text-sm text-gray-600">{{ [detail.venue, detail.location_details].filter(Boolean).join(" · ") }}</p>
          <p v-if="detail.service_relation === REPLACES" class="text-sm text-indigo-700 mt-2">This replaces the regular worship service that day.</p>
          <div class="mt-4 text-right"><AppButton variant="secondary" @click="detail = null">Close</AppButton></div>
        </div>
      </div>
    </Teleport>

    <ActivityModal
      v-if="planner"
      :is-open="modal.open"
      :activity="modal.activity"
      :defaults="modal.defaults"
      :options="options || {}"
      @close="modal.open = false"
      @saved="onSaved"
      @deleted="onSaved"
    />
  </div>
</template>
