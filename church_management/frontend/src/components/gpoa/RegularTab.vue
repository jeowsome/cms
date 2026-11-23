<script setup>
import { computed, ref, watch } from "vue";
import { call } from "@/composables/useFrappeApi";
import AppButton from "@/components/AppButton.vue";
import { FREQUENCIES, MONTHS, RELATIONS, WEEKDAYS, deptColor, describeRule, fmtDate, fmtTime, peso } from "@/utils/calendar";

/** Recurring department activities. Each rule's annual budget is its
 * per-occurrence budget × the dates it produces in the year; "Put on
 * calendar" turns the rules into dated calendar activities. */
const props = defineProps({ data: { type: Object, required: true } });
const emit = defineEmits(["changed"]);

const API = "church_management.api.gpoa.";
const groups = computed(() => {
  const out = {};
  for (const r of props.data.regular) (out[r.department] ||= []).push(r);
  return Object.entries(out).sort(([a], [b]) => a.localeCompare(b));
});
const total = computed(() => props.data.regular.filter((r) => r.active).reduce((s, r) => s + (r.annual_budget || 0), 0));
const departments = computed(() => props.data.my_departments ?? props.data.departments);

// ---------- form
const form = ref(null);
const preview = ref([]);
const busy = ref(false);
const errorMsg = ref("");

function openForm(r = null) {
  errorMsg.value = "";
  form.value = r
    ? { ...r }
    : {
        gpoa: props.data.gpoa.name, department: departments.value.length === 1 ? departments.value[0] : "",
        description: "", active: 1, on_calendar: 1, frequency: "Monthly", weekday: "Sunday", weeks_of_month: "",
        start_month: 1, months: "", all_day: 0, start_time: "", end_time: "", venue: "Church",
        service_relation: "Separate from worship service", budget_per_occurrence: 0, notes: "",
      };
  form.value.gpoa = props.data.gpoa.name;
  form.value.start_time = form.value.start_time?.slice(0, 5) || "";
  form.value.end_time = form.value.end_time?.slice(0, 5) || "";
}
let timer;
watch(
  () => form.value && [form.value.frequency, form.value.weekday, form.value.weeks_of_month, form.value.start_month, form.value.months],
  () => {
    if (!form.value) return;
    clearTimeout(timer);
    timer = setTimeout(async () => {
      try {
        preview.value = await call(API + "preview_regular", { data: JSON.stringify(form.value), year: props.data.year });
      } catch {
        preview.value = [];
      }
    }, 250);
  },
  { deep: true }
);
const previewBudget = computed(() => (form.value?.budget_per_occurrence || 0) * preview.value.length);

async function save() {
  if (!form.value.department || !form.value.description?.trim()) {
    errorMsg.value = "Choose the department and describe the activity.";
    return;
  }
  busy.value = true;
  errorMsg.value = "";
  try {
    const payload = { ...form.value, start_time: form.value.start_time || null, end_time: form.value.end_time || null };
    await call(API + "save_regular", { data: JSON.stringify(payload) });
    form.value = null;
    emit("changed");
  } catch (e) {
    errorMsg.value = e.message;
  } finally {
    busy.value = false;
  }
}
async function remove(r) {
  if (!confirm(`Delete “${r.description}”? Its upcoming calendar dates are removed too; past ones stay.`)) return;
  try {
    await call(API + "delete_regular", { name: r.name });
    emit("changed");
  } catch (e) {
    alert(e.message);
  }
}

// ---------- generate
const result = ref(null);
async function generate(r = null) {
  const what = r ? `“${r.description}”` : "every regular activity you plan for";
  if (!confirm(`Put ${what} on the ${props.data.year} calendar from today on? Dates generated before are replaced, except ones edited by hand.`)) return;
  busy.value = true;
  try {
    result.value = await call(API + "generate_dates", { gpoa: props.data.gpoa.name, regular: r?.name || null });
    emit("changed");
  } catch (e) {
    alert(e.message);
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div>
    <div class="flex flex-wrap items-center justify-between gap-3 mb-3">
      <p class="text-xs text-gray-500">What departments do every week or month. Annual total {{ peso(total) }}.</p>
      <div class="flex gap-2">
        <AppButton size="sm" variant="secondary" :loading="busy && !form" @click="generate()">Put on calendar</AppButton>
        <AppButton size="sm" @click="openForm()">+ Regular activity</AppButton>
      </div>
    </div>

    <div v-if="result" class="mb-4 p-3 rounded-2xl text-xs" :class="result.skipped.length ? 'bg-amber-50 text-amber-900' : 'bg-emerald-50 text-emerald-900'">
      <div class="flex justify-between gap-2">
        <p class="font-bold">{{ result.created }} dates added to the calendar{{ result.kept ? `, ${result.kept} edited dates kept` : "" }}{{ result.skipped.length ? `, ${result.skipped.length} skipped because of conflicts:` : "." }}</p>
        <button class="font-bold" aria-label="Dismiss" @click="result = null">✕</button>
      </div>
      <ul v-if="result.skipped.length" class="mt-1 space-y-0.5 max-h-40 overflow-y-auto">
        <li v-for="(s, i) in result.skipped" :key="i">{{ fmtDate(s.date) }} · {{ s.rule }} ({{ s.department }}) — {{ s.reason }}</li>
      </ul>
      <p v-if="result.skipped.length" class="mt-1">Give the rule a time that avoids the services, mark it part of the service, or add those dates by hand.</p>
    </div>

    <p v-if="!groups.length" class="p-6 text-center text-sm text-gray-400 bg-white rounded-2xl border border-gray-200">No regular activities yet.</p>
    <div v-for="[dept, rows] in groups" :key="dept" class="mb-4 bg-white rounded-2xl border border-gray-200 overflow-hidden">
      <div class="px-4 py-2 bg-gray-50 border-b border-gray-100 flex items-center gap-2">
        <span class="w-2 h-2 rounded-full" :class="deptColor(dept).dot" />
        <h3 class="text-xs font-bold text-gray-700">{{ dept }}</h3>
        <span class="ml-auto text-xs font-semibold text-gray-500 tabular">{{ peso(rows.filter((r) => r.active).reduce((s, r) => s + (r.annual_budget || 0), 0)) }}</span>
      </div>
      <div v-for="r in rows" :key="r.name" class="px-4 py-2.5 border-t border-gray-50 first:border-t-0 flex flex-wrap items-center gap-x-4 gap-y-1" :class="r.active ? '' : 'opacity-50'">
        <div class="min-w-0 flex-1">
          <p class="text-sm font-semibold text-gray-900">{{ r.description }}
            <span v-if="!r.on_calendar" class="ml-1 text-[10px] font-bold uppercase text-gray-400">budget only</span>
            <span v-if="!r.active" class="ml-1 text-[10px] font-bold uppercase text-gray-400">inactive</span>
          </p>
          <p class="text-xs text-gray-500">{{ r.frequency }} · {{ describeRule(r) }}<template v-if="r.start_time"> · {{ fmtTime(r.start_time.slice(0, 5)) }}–{{ fmtTime(r.end_time?.slice(0, 5)) }}</template><template v-if="r.venue"> · {{ r.venue }}</template></p>
        </div>
        <div class="text-right text-xs tabular">
          <p class="font-semibold text-gray-800">{{ peso(r.annual_budget) }}</p>
          <p class="text-gray-400">{{ peso(r.budget_per_occurrence) }} × {{ r.occurrences }}</p>
        </div>
        <div class="text-xs text-gray-400 w-20 text-right">{{ r.on_calendar ? `${r.generated} on calendar` : "" }}</div>
        <div v-if="r.can_edit" class="flex gap-1">
          <AppButton v-if="r.on_calendar && r.active" size="sm" variant="ghost" :disabled="busy" title="Put this one on the calendar" @click="generate(r)">📅</AppButton>
          <AppButton size="sm" variant="ghost" @click="openForm(r)">Edit</AppButton>
          <AppButton size="sm" variant="ghost" class="!text-red-600" @click="remove(r)">Delete</AppButton>
        </div>
      </div>
    </div>

    <!-- Form -->
    <Teleport to="body">
      <div v-if="form" class="fixed inset-0 z-[60] flex items-end sm:items-center justify-center sm:p-4">
        <div class="absolute inset-0 bg-gray-900/40 backdrop-blur-sm" @click="!busy && (form = null)" />
        <div class="relative bg-white rounded-t-2xl sm:rounded-2xl shadow-2xl w-full max-w-xl p-5 anim-pop max-h-[92dvh] overflow-y-auto">
          <h3 class="text-base font-bold text-gray-900 mb-4">{{ form.name ? "Edit" : "New" }} regular activity</h3>
          <div class="space-y-3">
            <div class="grid grid-cols-2 gap-3">
              <label class="block"><span class="text-xs font-semibold text-gray-600">Department</span>
                <select v-model="form.department" class="cm-field cm-select mt-1">
                  <option value="" disabled>Choose…</option>
                  <option v-for="d in departments" :key="d" :value="d">{{ d }}</option>
                </select>
              </label>
              <label class="block"><span class="text-xs font-semibold text-gray-600">Description</span>
                <input v-model="form.description" class="cm-field mt-1" placeholder="e.g. Regular Fellowship" />
              </label>
            </div>
            <div class="grid grid-cols-3 gap-3">
              <label class="block"><span class="text-xs font-semibold text-gray-600">Frequency</span>
                <select v-model="form.frequency" class="cm-field cm-select mt-1"><option v-for="f in FREQUENCIES" :key="f">{{ f }}</option></select>
              </label>
              <label class="block"><span class="text-xs font-semibold text-gray-600">Day</span>
                <select v-model="form.weekday" class="cm-field cm-select mt-1"><option v-for="w in WEEKDAYS" :key="w">{{ w }}</option></select>
              </label>
              <label class="block"><span class="text-xs font-semibold text-gray-600">Weeks</span>
                <input v-model="form.weeks_of_month" class="cm-field mt-1" placeholder="e.g. 2,4 or 1,last" />
              </label>
            </div>
            <div v-if="!['Weekly', 'Twice a Month', 'Monthly'].includes(form.frequency)" class="grid grid-cols-2 gap-3">
              <label class="block"><span class="text-xs font-semibold text-gray-600">Starting month</span>
                <select v-model.number="form.start_month" class="cm-field cm-select mt-1"><option v-for="(m, i) in MONTHS" :key="m" :value="i + 1">{{ m }}</option></select>
              </label>
              <label class="block"><span class="text-xs font-semibold text-gray-600">Or specific months</span>
                <input v-model="form.months" class="cm-field mt-1" placeholder="e.g. 3,7,11" />
              </label>
            </div>
            <div class="grid grid-cols-3 gap-3">
              <label class="block"><span class="text-xs font-semibold text-gray-600">Start time</span><input v-model="form.start_time" type="time" class="cm-field mt-1" /></label>
              <label class="block"><span class="text-xs font-semibold text-gray-600">End time</span><input v-model="form.end_time" type="time" class="cm-field mt-1" /></label>
              <label class="block"><span class="text-xs font-semibold text-gray-600">Venue</span>
                <select v-model="form.venue" class="cm-field cm-select mt-1">
                  <option :value="null">Off-site / TBD</option>
                  <option v-for="v in data.venues" :key="v.name" :value="v.name">{{ v.name }}</option>
                </select>
              </label>
            </div>
            <label class="block"><span class="text-xs font-semibold text-gray-600">Worship service</span>
              <select v-model="form.service_relation" class="cm-field cm-select mt-1"><option v-for="r in RELATIONS" :key="r.value" :value="r.value">{{ r.label }}</option></select>
            </label>
            <div class="grid grid-cols-2 gap-3 items-end">
              <label class="block"><span class="text-xs font-semibold text-gray-600">Budget per occurrence</span>
                <input v-model.number="form.budget_per_occurrence" type="number" min="0" step="50" class="cm-field mt-1" />
              </label>
              <div class="pb-2 text-sm">
                <span class="text-gray-500">{{ preview.length }} dates → </span><span class="font-bold tabular">{{ peso(previewBudget) }}</span>
              </div>
            </div>
            <div class="flex gap-4 text-sm text-gray-700">
              <label class="inline-flex items-center gap-2"><input v-model="form.on_calendar" type="checkbox" :true-value="1" :false-value="0" class="rounded border-gray-300" /> Show on calendar</label>
              <label class="inline-flex items-center gap-2"><input v-model="form.active" type="checkbox" :true-value="1" :false-value="0" class="rounded border-gray-300" /> Active</label>
            </div>
            <div class="p-2.5 rounded-xl bg-gray-50 text-[11px] text-gray-600">
              <p class="font-bold mb-1">{{ describeRule(form) }} — {{ data.year }} dates</p>
              <p class="leading-5">{{ preview.map((d) => fmtDate(d)).join(" · ") || "No dates." }}</p>
            </div>
          </div>
          <div v-if="errorMsg" class="mt-3 p-2.5 rounded-xl bg-red-50 text-red-700 text-xs font-semibold">{{ errorMsg }}</div>
          <div class="mt-5 flex justify-end gap-2">
            <AppButton variant="secondary" :disabled="busy" @click="form = null">Cancel</AppButton>
            <AppButton :loading="busy" @click="save">Save</AppButton>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
