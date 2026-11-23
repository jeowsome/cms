<script setup>
import { computed } from "vue";
import { deptColor, deptShort, peso } from "@/utils/calendar";

/** Per department: this year's plan (regular + scheduled activities +
 * budget requests) beside last year's plan and what was actually spent on
 * activities (disbursements with purpose Regular Activity or Special Event). */
const props = defineProps({ data: { type: Object, required: true } });

const rows = computed(() => [...props.data.budget].sort((a, b) => b.total - a.total || a.department.localeCompare(b.department)));
const sum = (k) => rows.value.reduce((s, r) => s + (r[k] || 0), 0);
const totals = computed(() => Object.fromEntries(
  ["regular", "scheduled", "activities", "requests", "total", "prev_activities", "prev_total", "prev_spent", "spent"].map((k) => [k, sum(k)])
));
const max = computed(() => Math.max(1, ...rows.value.map((r) => Math.max(r.activities, r.prev_activities, r.prev_spent))));
function pct(v) {
  return `${Math.max(0, (v / max.value) * 100)}%`;
}
function change(now, before) {
  if (!before) return null;
  return ((now - before) / before) * 100;
}
</script>

<template>
  <div>
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
      <div class="bg-white rounded-2xl border border-gray-200 p-3">
        <p class="text-[11px] font-semibold text-gray-500">Activities {{ data.year }}</p>
        <p class="text-lg font-bold tabular">{{ peso(totals.activities) }}</p>
        <p class="text-[11px] text-gray-400">regular {{ peso(totals.regular) }} + events {{ peso(totals.scheduled) }}</p>
      </div>
      <div class="bg-white rounded-2xl border border-gray-200 p-3">
        <p class="text-[11px] font-semibold text-gray-500">Budget requests</p>
        <p class="text-lg font-bold tabular">{{ peso(totals.requests) }}</p>
      </div>
      <div class="bg-white rounded-2xl border border-gray-200 p-3">
        <p class="text-[11px] font-semibold text-gray-500">Planned for {{ data.year - 1 }}</p>
        <p class="text-lg font-bold tabular">{{ peso(totals.prev_activities) }}</p>
        <p class="text-[11px] text-gray-400">activities only</p>
      </div>
      <div class="bg-white rounded-2xl border border-gray-200 p-3">
        <p class="text-[11px] font-semibold text-gray-500">Spent on activities {{ data.year - 1 }}</p>
        <p class="text-lg font-bold tabular">{{ peso(totals.prev_spent) }}</p>
        <p class="text-[11px] text-gray-400">{{ data.year }} so far: {{ peso(totals.spent) }}</p>
      </div>
    </div>

    <div class="bg-white rounded-2xl border border-gray-200 overflow-x-auto">
      <table class="min-w-full text-sm">
        <thead>
          <tr class="bg-gray-50 text-[11px] uppercase text-gray-500">
            <th class="text-left px-3 py-2">Department</th>
            <th class="text-right px-3 py-2">Regular</th>
            <th class="text-right px-3 py-2">Events</th>
            <th class="text-right px-3 py-2">Requests</th>
            <th class="text-right px-3 py-2">Total {{ data.year }}</th>
            <th class="text-right px-3 py-2">Plan {{ data.year - 1 }}</th>
            <th class="text-right px-3 py-2">Spent {{ data.year - 1 }}</th>
            <th class="text-right px-3 py-2">Spent {{ data.year }}</th>
            <th class="px-3 py-2 w-40">Activities: plan vs last year</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.department" class="border-t border-gray-100">
            <td class="px-3 py-2 font-semibold whitespace-nowrap">
              <span class="inline-block w-2 h-2 rounded-full mr-1.5" :class="deptColor(r.department).dot" />{{ deptShort(r.department) }}
            </td>
            <td class="px-3 py-2 text-right tabular">{{ r.regular ? peso(r.regular) : "—" }}</td>
            <td class="px-3 py-2 text-right tabular">{{ r.scheduled ? peso(r.scheduled) : "—" }}</td>
            <td class="px-3 py-2 text-right tabular">{{ r.requests ? peso(r.requests) : "—" }}</td>
            <td class="px-3 py-2 text-right tabular font-bold">
              {{ peso(r.total) }}
              <span v-if="change(r.total, r.prev_total) !== null" class="block text-[10px] font-bold" :class="r.total > r.prev_total ? 'text-amber-600' : 'text-emerald-600'">
                {{ r.total > r.prev_total ? "▲" : r.total < r.prev_total ? "▼" : "=" }}{{ Math.abs(change(r.total, r.prev_total)).toFixed(0) }}%
              </span>
            </td>
            <td class="px-3 py-2 text-right tabular text-gray-500">{{ r.prev_total ? peso(r.prev_total) : "—" }}</td>
            <td class="px-3 py-2 text-right tabular text-gray-500">{{ r.prev_spent ? peso(r.prev_spent) : "—" }}</td>
            <td class="px-3 py-2 text-right tabular text-gray-500">{{ r.spent ? peso(r.spent) : "—" }}</td>
            <td class="px-3 py-2">
              <div class="space-y-0.5" :title="`Plan ${peso(r.activities)} · last year's plan ${peso(r.prev_activities)} · spent last year ${peso(r.prev_spent)}`">
                <div class="h-1.5 rounded-full" :class="deptColor(r.department).dot" :style="{ width: pct(r.activities) }" />
                <div class="h-1.5 rounded-full bg-gray-300" :style="{ width: pct(r.prev_activities) }" />
                <div class="h-1.5 rounded-full bg-gray-500" :style="{ width: pct(r.prev_spent) }" />
              </div>
            </td>
          </tr>
          <tr class="border-t-2 border-gray-200 bg-gray-50 font-bold">
            <td class="px-3 py-2">Total</td>
            <td class="px-3 py-2 text-right tabular">{{ peso(totals.regular) }}</td>
            <td class="px-3 py-2 text-right tabular">{{ peso(totals.scheduled) }}</td>
            <td class="px-3 py-2 text-right tabular">{{ peso(totals.requests) }}</td>
            <td class="px-3 py-2 text-right tabular">{{ peso(totals.total) }}</td>
            <td class="px-3 py-2 text-right tabular">{{ peso(totals.prev_total) }}</td>
            <td class="px-3 py-2 text-right tabular">{{ peso(totals.prev_spent) }}</td>
            <td class="px-3 py-2 text-right tabular">{{ peso(totals.spent) }}</td>
            <td />
          </tr>
        </tbody>
      </table>
    </div>
    <p class="text-[11px] text-gray-400 mt-2">
      Bars: <span class="font-semibold">colour</span> = this year's activity plan, light grey = last year's plan, dark grey = spent last year.
      “Spent” counts disbursements with purpose Regular Activity or Special Event, so record activity spending under those purposes.
    </p>
  </div>
</template>
