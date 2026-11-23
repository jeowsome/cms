<script setup>
import { computed, ref } from "vue";
import { call } from "@/composables/useFrappeApi";
import { deptShort, peso } from "@/utils/calendar";

/** Goals grid: metric rows × department columns. Each cell is this year's
 * target, with last year's target (and actual, if recorded) beside it. */
const props = defineProps({ data: { type: Object, required: true } });
const emit = defineEmits(["changed"]);

const mode = ref("target"); // target | actual
const saving = ref("");
const errorMsg = ref("");
const added = ref([]);

const key = (d, m) => `${d}|${m}`;
const current = computed(() => Object.fromEntries(props.data.goals.map((g) => [key(g.department, g.metric), g])));
const previous = computed(() => Object.fromEntries(props.data.prev_goals.map((g) => [key(g.department, g.metric), g])));

// Pasig General first, then the rest in the order the GPOA sheet uses.
const ORDER = ["Pasig General", "Pasig Sunday School", "Pasig ColSPro", "Pasig Young People", "Pasig Juniors", "Pasig Ladies", "Pasig Men", "Cainta General"];
const columns = computed(() => {
  const set = new Set([...props.data.goals, ...props.data.prev_goals].map((g) => g.department).concat(added.value));
  return [...set].sort((a, b) => {
    const ia = ORDER.indexOf(a), ib = ORDER.indexOf(b);
    return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib) || a.localeCompare(b);
  });
});
const addable = computed(() => {
  const mine = props.data.my_departments ?? props.data.departments;
  return mine.filter((d) => !columns.value.includes(d));
});
function canEdit(dept) {
  return props.data.my_departments === null || props.data.my_departments.includes(dept);
}

function fmt(metric, v) {
  if (v === null || v === undefined || v === "") return "—";
  if (metric === "Finance") return v >= 1e6 ? `₱${+(v / 1e6).toFixed(2)}M` : v >= 1e3 ? `₱${+(v / 1e3).toFixed(1)}K` : peso(v);
  return Number(v).toLocaleString();
}
function delta(dept, metric) {
  const now = current.value[key(dept, metric)]?.target;
  const before = previous.value[key(dept, metric)]?.target;
  if (now == null || before == null || before === 0) return null;
  return ((now - before) / before) * 100;
}

/** "150" → 150, "2.5M" → 2500000, "300K" → 300000, "" → null. */
function parseNum(raw) {
  const t = String(raw ?? "").trim().toUpperCase().replace(/[,₱\s]/g, "");
  if (!t) return null;
  const m = t.match(/^(\d+(?:\.\d+)?)([MK]?)$/);
  if (!m) return NaN;
  return Number(m[1]) * (m[2] === "M" ? 1e6 : m[2] === "K" ? 1e3 : 1);
}

async function save(dept, metric, field, raw) {
  const g = current.value[key(dept, metric)] || {};
  const value = parseNum(raw);
  if (Number.isNaN(value)) {
    errorMsg.value = `“${raw}” is not a number. Use e.g. 150, 2500000, 2.5M or 300K.`;
    return;
  }
  if ((g[field] ?? null) === value) return;
  saving.value = key(dept, metric);
  errorMsg.value = "";
  try {
    await call("church_management.api.gpoa.save_goal", {
      gpoa: props.data.gpoa.name, department: dept, metric,
      target: field === "target" ? value : g.target, actual: field === "actual" ? value : g.actual,
    });
    emit("changed");
  } catch (e) {
    errorMsg.value = e.message;
  } finally {
    saving.value = "";
  }
}
function addColumn(e) {
  if (e.target.value) added.value.push(e.target.value);
  e.target.value = "";
}

const finance = computed(() => {
  const goal = current.value[key("Pasig General", "Finance")]?.target;
  const got = props.data.collections.this;
  return { goal, got, pct: goal ? Math.min(100, (got / goal) * 100) : null };
});
</script>

<template>
  <div>
    <div class="flex flex-wrap items-center justify-between gap-3 mb-3">
      <p class="text-xs text-gray-500">Goals for {{ data.year }} beside {{ data.year - 1 }}'s. PRC = profess to receive Christ.</p>
      <div class="flex items-center gap-2">
        <div class="inline-flex rounded-xl bg-gray-100 p-0.5 text-xs font-semibold">
          <button class="px-3 py-1.5 rounded-lg" :class="mode === 'target' ? 'bg-white shadow-sm' : 'text-gray-500'" @click="mode = 'target'">Set targets</button>
          <button class="px-3 py-1.5 rounded-lg" :class="mode === 'actual' ? 'bg-white shadow-sm' : 'text-gray-500'" @click="mode = 'actual'">Record actuals</button>
        </div>
        <select v-if="addable.length" class="cm-field cm-select !h-8 !w-44 text-xs" @change="addColumn">
          <option value="">+ Department…</option>
          <option v-for="d in addable" :key="d" :value="d">{{ d }}</option>
        </select>
      </div>
    </div>

    <div v-if="finance.goal" class="mb-4 p-3 bg-white rounded-2xl border border-gray-200">
      <div class="flex items-baseline justify-between text-xs mb-1.5">
        <span class="font-bold text-gray-700">Finance — JBC Pasig collections so far</span>
        <span class="tabular text-gray-600">{{ peso(finance.got) }} of {{ peso(finance.goal) }} ({{ finance.pct.toFixed(0) }}%)</span>
      </div>
      <div class="h-2 rounded-full bg-gray-100 overflow-hidden" role="progressbar" :aria-valuenow="finance.pct" aria-valuemin="0" aria-valuemax="100">
        <div class="h-full bg-emerald-500 rounded-full" :style="{ width: finance.pct + '%' }" />
      </div>
      <p class="text-[11px] text-gray-400 mt-1">{{ data.year - 1 }} collections in the system: {{ peso(data.collections.prev) }}</p>
    </div>

    <div v-if="errorMsg" class="mb-3 p-2.5 rounded-xl bg-red-50 text-red-700 text-xs font-semibold">{{ errorMsg }}</div>

    <div class="bg-white rounded-2xl border border-gray-200 overflow-x-auto">
      <table class="min-w-full text-sm">
        <thead>
          <tr class="bg-gray-50 text-[11px] uppercase text-gray-500">
            <th class="text-left px-3 py-2 sticky left-0 bg-gray-50">Goal</th>
            <th v-for="d in columns" :key="d" class="px-3 py-2 text-center whitespace-nowrap" :title="d">{{ d === "Pasig General" ? "JBC Pasig" : deptShort(d) }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="m in data.metrics" :key="m" class="border-t border-gray-100">
            <th class="text-left px-3 py-2 font-semibold text-gray-800 sticky left-0 bg-white">{{ m }}</th>
            <td v-for="d in columns" :key="d" class="px-2 py-2 text-center align-top">
              <input
                :value="current[key(d, m)]?.[mode] ?? ''"
                :disabled="!canEdit(d) || saving === key(d, m)"
                inputmode="decimal"
                class="w-24 h-9 text-center rounded-lg border border-gray-200 text-sm font-semibold tabular focus:border-brand-500 focus:ring-2 focus:ring-brand-100 focus:outline-none disabled:bg-gray-50 disabled:text-gray-500"
                :aria-label="`${m} ${mode} for ${d}`"
                :placeholder="mode === 'target' ? 'target' : 'actual'"
                @change="save(d, m, mode, $event.target.value)"
              />
              <div class="mt-1 text-[10px] leading-tight text-gray-400 whitespace-nowrap">
                <span v-if="mode === 'actual'">target {{ fmt(m, current[key(d, m)]?.target) }}</span>
                <template v-else>
                  <span>{{ data.year - 1 }}: {{ fmt(m, previous[key(d, m)]?.target) }}</span>
                  <span v-if="previous[key(d, m)]?.actual != null"> · got {{ fmt(m, previous[key(d, m)].actual) }}</span>
                  <span v-if="delta(d, m) !== null" class="ml-1 font-bold" :class="delta(d, m) > 0 ? 'text-emerald-600' : delta(d, m) < 0 ? 'text-red-600' : ''">
                    {{ delta(d, m) > 0 ? "▲" : delta(d, m) < 0 ? "▼" : "=" }}{{ Math.abs(delta(d, m)).toFixed(0) }}%
                  </span>
                </template>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <p class="text-[11px] text-gray-400 mt-2">Finance targets accept 2500000, 2.5M or 300K. Changes save when you leave the box.</p>
  </div>
</template>
