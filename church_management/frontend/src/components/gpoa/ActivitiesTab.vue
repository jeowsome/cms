<script setup>
import { computed, ref } from "vue";
import { useQuery } from "@pinia/colada";
import { call } from "@/composables/useFrappeApi";
import AppButton from "@/components/AppButton.vue";
import ActivityModal from "@/components/ActivityModal.vue";
import { MONTHS, REPLACES, deptColor, deptShort, fmtRange, peso } from "@/utils/calendar";

/** The year's dated activities (not the generated regular dates), by month. */
const props = defineProps({ data: { type: Object, required: true } });
const emit = defineEmits(["changed"]);

const { data: options } = useQuery({
  key: ["planner-options"],
  query: () => call("church_management.api.church_calendar.get_planner_options"),
});

const dept = ref("");
const onlyConflicts = ref(false);
const rows = computed(() =>
  props.data.activities.filter((a) => (!dept.value || a.department === dept.value) && (!onlyConflicts.value || a.conflicts?.length))
);
const byMonth = computed(() => {
  const out = [];
  for (let m = 0; m < 12; m++) {
    const items = rows.value.filter((a) => Number(a.start_date.slice(5, 7)) === m + 1);
    if (items.length) out.push({ name: MONTHS[m], items, total: items.filter((a) => a.status !== "Cancelled").reduce((s, a) => s + (a.budget || 0), 0) });
  }
  return out;
});
const usedDepts = computed(() => [...new Set(props.data.activities.map((a) => a.department))].sort());
const conflictCount = computed(() => props.data.activities.filter((a) => a.conflicts?.length).length);
const total = computed(() => rows.value.filter((a) => a.status !== "Cancelled").reduce((s, a) => s + (a.budget || 0), 0));

const modal = ref({ open: false, activity: null });
function open(a = null) {
  modal.value = { open: true, activity: a };
}
function saved() {
  modal.value.open = false;
  emit("changed");
}
const STATUS_CLASS = {
  Proposed: "bg-gray-100 text-gray-600",
  Confirmed: "bg-emerald-100 text-emerald-700",
  Done: "bg-sky-100 text-sky-700",
  Cancelled: "bg-red-100 text-red-600 line-through",
};
</script>

<template>
  <div>
    <div class="flex flex-wrap items-center justify-between gap-3 mb-3">
      <div class="flex items-center gap-2 flex-wrap">
        <select v-model="dept" class="cm-field cm-select !h-9 !w-48 text-xs">
          <option value="">All departments</option>
          <option v-for="d in usedDepts" :key="d" :value="d">{{ d }}</option>
        </select>
        <label v-if="conflictCount" class="inline-flex items-center gap-1.5 text-xs font-semibold text-red-600">
          <input v-model="onlyConflicts" type="checkbox" class="rounded border-gray-300" /> Only conflicts ({{ conflictCount }})
        </label>
        <span class="text-xs text-gray-500">{{ rows.length }} activities · {{ peso(total) }}</span>
      </div>
      <AppButton size="sm" @click="open()">+ Activity</AppButton>
    </div>

    <p v-if="!byMonth.length" class="p-6 text-center text-sm text-gray-400 bg-white rounded-2xl border border-gray-200">No activities yet. Add them here or by double-clicking a day on the calendar.</p>
    <section v-for="m in byMonth" :key="m.name" class="mb-4">
      <div class="flex items-baseline justify-between mb-1.5 px-1">
        <h3 class="text-xs font-bold uppercase tracking-wide text-gray-500">{{ m.name }}</h3>
        <span class="text-xs text-gray-400 tabular">{{ peso(m.total) }}</span>
      </div>
      <div class="bg-white rounded-2xl border border-gray-200 divide-y divide-gray-100">
        <button v-for="a in m.items" :key="a.name" class="w-full text-left px-4 py-2.5 flex flex-wrap items-center gap-x-3 gap-y-1 hover:bg-gray-50" @click="open(a)">
          <span class="w-2 h-2 rounded-full shrink-0" :class="deptColor(a.department).dot" />
          <span class="min-w-0 flex-1">
            <span class="block text-sm font-semibold text-gray-900">{{ a.title }}</span>
            <span class="block text-xs text-gray-500">{{ fmtRange(a) }} · {{ deptShort(a.department) }}<template v-if="a.venue || a.location_details"> · {{ a.venue || a.location_details }}</template><template v-if="a.transport_needed"> · 🚐</template></span>
            <span v-if="a.service_relation === REPLACES" class="block text-[11px] text-indigo-700">Replaces worship service · pastor: {{ a.pastor_approval || "not asked" }}</span>
            <span v-if="!a.is_public" class="block text-[11px] text-gray-400">Not on the public calendar</span>
            <span v-for="(c, i) in a.conflicts || []" :key="i" class="block text-[11px] text-red-600">⚠ {{ c.message }}</span>
          </span>
          <span class="text-[10px] font-bold uppercase px-2 py-0.5 rounded-md" :class="STATUS_CLASS[a.status]">{{ a.status }}</span>
          <span class="w-20 text-right text-sm font-semibold tabular text-gray-800">{{ a.budget ? peso(a.budget) : "—" }}</span>
        </button>
      </div>
    </section>

    <ActivityModal
      :is-open="modal.open"
      :activity="modal.activity"
      :defaults="{ gpoa: data.gpoa.name, start_date: `${data.year}-01-01` }"
      :options="options || {}"
      @close="modal.open = false"
      @saved="saved"
      @deleted="saved"
    />
  </div>
</template>
