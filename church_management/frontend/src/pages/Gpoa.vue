<script setup>
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useQuery } from "@pinia/colada";
import { call } from "@/composables/useFrappeApi";
import { usePersistedRef } from "@/composables/usePersistedRef";
import AppButton from "@/components/AppButton.vue";
import YearSwitcher from "@/components/YearSwitcher.vue";
import GoalsTab from "@/components/gpoa/GoalsTab.vue";
import RegularTab from "@/components/gpoa/RegularTab.vue";
import ActivitiesTab from "@/components/gpoa/ActivitiesTab.vue";
import RequestsTab from "@/components/gpoa/RequestsTab.vue";
import BudgetTab from "@/components/gpoa/BudgetTab.vue";
import { peso } from "@/utils/calendar";

/** GPOA — General Planning of Activities. One page per year: goals,
 * regular activities, dated activities, budget requests and the budget
 * summary, each beside last year's. */
const route = useRoute();
const router = useRouter();
const thisYear = new Date().getFullYear();

const { data: yearsData, refetch: refetchYears } = useQuery({
  key: ["gpoa-years"],
  query: () => call("church_management.api.gpoa.get_years"),
});

const year = computed({
  get: () => Number(route.params.year) || thisYear,
  set: (y) => router.replace(`/gpoa/${y}`),
});
const years = computed(() => {
  const s = new Set((yearsData.value?.years || []).map((y) => y.year));
  s.add(thisYear);
  s.add(thisYear + 1);
  s.add(year.value);
  return [...s];
});

const { data, isPending, error, refetch } = useQuery({
  key: () => ["gpoa", year.value],
  query: () => call("church_management.api.gpoa.get_gpoa", { year: year.value }),
});

const TABS = [
  { key: "goals", label: "Goals" },
  { key: "regular", label: "Regular activities" },
  { key: "activities", label: "Activities" },
  { key: "requests", label: "Budget requests" },
  { key: "budget", label: "Budget summary" },
  { key: "notes", label: "Notes" },
];
const tab = usePersistedRef("cm-gpoa-tab", "goals", "session");

const stats = computed(() => {
  const d = data.value;
  if (!d?.exists) return null;
  const planned = d.budget.reduce((s, r) => s + r.total, 0);
  const prev = d.budget.reduce((s, r) => s + r.prev_total, 0);
  return {
    planned, prev,
    activities: d.activities.filter((a) => a.status !== "Cancelled").length,
    conflicts: d.activities.filter((a) => a.conflicts?.length).length,
  };
});

// ---------- create
const creating = ref(false);
async function create() {
  const prev = data.value?.prev;
  const msg = prev
    ? `Start GPOA ${year.value}? ${prev}'s regular activities and goal rows are copied so you can adjust them.`
    : `Start GPOA ${year.value}?`;
  if (!confirm(msg)) return;
  creating.value = true;
  try {
    await call("church_management.api.gpoa.create_gpoa", { year: year.value, copy_previous: 1 });
    await Promise.all([refetch(), refetchYears()]);
  } catch (e) {
    alert(e.message);
  } finally {
    creating.value = false;
  }
}

// ---------- notes / status
const notes = ref({ status: "", theme: "", notes: "" });
watch(
  () => data.value?.gpoa,
  (g) => {
    if (g) notes.value = { status: g.status, theme: g.theme || "", notes: g.notes || "" };
  },
  { immediate: true }
);
const savingNotes = ref(false);
async function saveNotes() {
  savingNotes.value = true;
  try {
    await call("church_management.api.gpoa.update_gpoa", { name: data.value.gpoa.name, ...notes.value });
    refetch();
    refetchYears();
  } catch (e) {
    alert(e.message);
  } finally {
    savingNotes.value = false;
  }
}
// ---------- public calendar
const publishing = ref(false);
async function setPublished(on) {
  const d = data.value;
  const conflicts = stats.value?.conflicts || 0;
  const msg = on
    ? `Publish GPOA ${year.value} to the public calendar?\n\nMembers will see ${d.public.shown} confirmed activities (dates, times and venues only, never budgets, transport or notes).` +
      (d.public.proposed ? `\n${d.public.proposed} proposed activities stay hidden until confirmed.` : "") +
      (conflicts ? `\n\n⚠ ${conflicts} activities still have conflicts.` : "")
    : `Withdraw GPOA ${year.value} from the public calendar? Members will see only the worship services for ${year.value}.`;
  if (!confirm(msg)) return;
  publishing.value = true;
  try {
    await call("church_management.api.gpoa.set_published", { name: d.gpoa.name, published: on ? 1 : 0 });
    await refetch();
  } catch (e) {
    alert(e.message);
  } finally {
    publishing.value = false;
  }
}

const STATUS_CLASS = { Planning: "bg-amber-100 text-amber-800", Approved: "bg-emerald-100 text-emerald-700", Closed: "bg-gray-100 text-gray-600" };
</script>

<template>
  <div class="px-4 sm:px-6 py-4 sm:py-6 max-w-6xl mx-auto w-full">
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-5">
      <div class="min-w-0">
        <h1 class="text-xl sm:text-2xl font-bold text-gray-900 flex items-center gap-2">
          GPOA {{ year }}
          <span v-if="data?.exists" class="text-[11px] font-bold uppercase px-2 py-0.5 rounded-md" :class="STATUS_CLASS[data.gpoa.status]">{{ data.gpoa.status }}</span>
        </h1>
        <p class="text-xs sm:text-sm text-gray-500 mt-0.5">General Planning of Activities{{ data?.gpoa?.theme ? ` · ${data.gpoa.theme}` : "" }}</p>
      </div>
      <div class="flex items-center gap-2">
        <AppButton size="sm" variant="secondary" @click="router.push('/calendar')">Calendar</AppButton>
        <YearSwitcher v-model="year" :years="years" />
      </div>
    </div>

    <div v-if="isPending" class="h-64 bg-white rounded-2xl border border-gray-100 animate-pulse" />
    <div v-else-if="error" class="p-4 bg-red-50 text-red-700 rounded-xl text-sm">{{ error.message }}</div>

    <div v-else-if="!data.exists" class="p-8 bg-white rounded-2xl border border-gray-200 text-center">
      <p class="text-gray-700 font-semibold">No GPOA for {{ year }} yet.</p>
      <p class="text-sm text-gray-500 mt-1">
        {{ data.prev ? `Starting it copies ${data.prev}'s regular activities and goal rows, so you only adjust what changes.` : "Start it to set goals and plan activities." }}
      </p>
      <AppButton v-if="data.can_create" class="mt-4" :loading="creating" @click="create">Start GPOA {{ year }}</AppButton>
      <p v-else class="text-xs text-gray-400 mt-3">Finance Team, the pastor or Pasig Admin starts the year's GPOA.</p>
    </div>

    <template v-else>
      <div v-if="stats" class="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
        <div class="bg-white rounded-2xl border border-gray-200 p-3">
          <p class="text-[11px] font-semibold text-gray-500">Planned budget</p>
          <p class="text-lg font-bold tabular">{{ peso(stats.planned) }}</p>
          <p v-if="stats.prev" class="text-[11px] text-gray-400">{{ year - 1 }}: {{ peso(stats.prev) }}</p>
        </div>
        <div class="bg-white rounded-2xl border border-gray-200 p-3">
          <p class="text-[11px] font-semibold text-gray-500">Collections {{ year }}</p>
          <p class="text-lg font-bold tabular">{{ peso(data.collections.this) }}</p>
          <p class="text-[11px] text-gray-400">{{ year - 1 }}: {{ peso(data.collections.prev) }}</p>
        </div>
        <div class="bg-white rounded-2xl border border-gray-200 p-3">
          <p class="text-[11px] font-semibold text-gray-500">Activities</p>
          <p class="text-lg font-bold tabular">{{ stats.activities }}</p>
          <p class="text-[11px] text-gray-400">{{ data.regular.length }} regular</p>
        </div>
        <button class="text-left bg-white rounded-2xl border p-3" :class="stats.conflicts ? 'border-red-200 bg-red-50' : 'border-gray-200'" @click="tab = 'activities'">
          <p class="text-[11px] font-semibold text-gray-500">Conflicts</p>
          <p class="text-lg font-bold tabular" :class="stats.conflicts ? 'text-red-600' : 'text-emerald-600'">{{ stats.conflicts }}</p>
          <p class="text-[11px] text-gray-400">{{ stats.conflicts ? "need a new date, time or venue" : "none" }}</p>
        </button>
      </div>

      <div v-if="data.public" class="mb-4 p-3 sm:px-4 rounded-2xl border flex flex-col sm:flex-row sm:items-center gap-3"
           :class="data.gpoa.calendar_published ? 'bg-emerald-50 border-emerald-100' : 'bg-white border-gray-200'">
        <div class="min-w-0 flex-1">
          <p class="text-sm font-semibold" :class="data.gpoa.calendar_published ? 'text-emerald-900' : 'text-gray-900'">
            {{ data.gpoa.calendar_published ? "Published to the public calendar" : "Not published to the public calendar" }}
          </p>
          <p class="text-xs text-gray-500 mt-0.5">
            <template v-if="data.gpoa.calendar_published">
              Members see {{ data.public.shown }} confirmed activities<template v-if="data.gpoa.published_on"> · since {{ data.gpoa.published_on.slice(0, 10) }}</template><template v-if="data.gpoa.published_by"> by {{ data.gpoa.published_by }}</template>.
            </template>
            <template v-else>Members see only the worship services for {{ year }}. Publishing shows {{ data.public.shown }} confirmed activities.</template>
            <template v-if="data.public.proposed"> {{ data.public.proposed }} proposed stay hidden until confirmed.</template>
            <template v-if="data.public.hidden"> {{ data.public.hidden }} marked not public.</template>
            Budgets, transport, headcount and notes are never shown.
          </p>
        </div>
        <div class="flex items-center gap-2 shrink-0">
          <a href="/calendar" target="_blank" rel="noopener" class="text-xs font-semibold text-brand-700 hover:underline">Open public calendar ↗</a>
          <template v-if="data.is_admin">
            <AppButton v-if="data.gpoa.calendar_published" size="sm" variant="secondary" :loading="publishing" @click="setPublished(false)">Unpublish</AppButton>
            <AppButton v-else size="sm" :loading="publishing" @click="setPublished(true)">Publish</AppButton>
          </template>
        </div>
      </div>

      <div class="flex gap-1 overflow-x-auto scrollbar-hide border-b border-gray-200 mb-4" role="tablist">
        <button v-for="t in TABS" :key="t.key" role="tab" :aria-selected="tab === t.key"
                class="px-3 py-2 text-sm font-semibold whitespace-nowrap border-b-2 -mb-px transition-colors"
                :class="tab === t.key ? 'border-brand-600 text-brand-700' : 'border-transparent text-gray-500 hover:text-gray-800'"
                @click="tab = t.key">{{ t.label }}</button>
      </div>

      <p v-if="data.my_departments" class="mb-3 text-xs text-gray-500">You plan for {{ data.my_departments.join(", ") }}. Other departments are shown read-only.</p>

      <GoalsTab v-if="tab === 'goals'" :data="data" @changed="refetch" />
      <RegularTab v-else-if="tab === 'regular'" :data="data" @changed="refetch" />
      <ActivitiesTab v-else-if="tab === 'activities'" :data="data" @changed="refetch" />
      <RequestsTab v-else-if="tab === 'requests'" :data="data" @changed="refetch" />
      <BudgetTab v-else-if="tab === 'budget'" :data="data" />
      <div v-else class="bg-white rounded-2xl border border-gray-200 p-4 space-y-3 max-w-2xl">
        <div class="grid grid-cols-3 gap-3">
          <label class="block col-span-2"><span class="text-xs font-semibold text-gray-600">Theme / verse</span>
            <input v-model="notes.theme" class="cm-field mt-1" :disabled="!data.is_admin" />
          </label>
          <label class="block"><span class="text-xs font-semibold text-gray-600">Status</span>
            <select v-model="notes.status" class="cm-field cm-select mt-1" :disabled="!data.is_admin">
              <option>Planning</option><option>Approved</option><option>Closed</option>
            </select>
          </label>
        </div>
        <label class="block"><span class="text-xs font-semibold text-gray-600">Special notes</span>
          <textarea v-model="notes.notes" rows="10" class="cm-field mt-1 !h-auto py-2 font-mono text-[13px]" :disabled="!data.is_admin" />
        </label>
        <p class="text-[11px] text-gray-400">When the GPOA is Approved, regular activities put on the calendar are marked Confirmed instead of Proposed.</p>
        <div v-if="data.is_admin" class="text-right"><AppButton :loading="savingNotes" @click="saveNotes">Save</AppButton></div>
      </div>
    </template>
  </div>
</template>
