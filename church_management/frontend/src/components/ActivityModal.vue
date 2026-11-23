<script setup>
import { computed, ref, watch } from "vue";
import { call } from "@/composables/useFrappeApi";
import AppButton from "@/components/AppButton.vue";
import { RELATIONS, REPLACES, STATUSES, addDays, fmtRange } from "@/utils/calendar";

/**
 * Add or edit one church calendar activity. Conflicts are checked on the
 * server as the form changes, so the planner sees a clash before saving.
 */
const props = defineProps({
  isOpen: { type: Boolean, default: false },
  activity: { type: Object, default: null }, // existing activity, or null for new
  defaults: { type: Object, default: () => ({}) }, // e.g. { start_date, department }
  options: { type: Object, default: () => ({}) }, // get_planner_options()
});
const emit = defineEmits(["close", "saved", "deleted"]);

const API = "church_management.api.church_calendar.";
const form = ref({});
const days = ref(1);
const conflicts = ref([]);
const checking = ref(false);
const saving = ref(false);
const errorMsg = ref("");
const newVenue = ref(null);

const myDepts = computed(() => props.options.my_departments ?? null);
const departments = computed(() => (myDepts.value === null ? props.options.departments || [] : myDepts.value));
const isAdmin = computed(() => myDepts.value === null);
const readOnly = computed(() => props.activity && props.activity.can_edit === false);
const statusOptions = computed(() =>
  STATUSES.filter((s) => isAdmin.value || s !== "Confirmed" || props.activity?.status === "Confirmed")
);

watch(
  () => props.isOpen,
  (open) => {
    if (!open) return;
    errorMsg.value = "";
    conflicts.value = [];
    newVenue.value = null;
    const a = props.activity;
    form.value = a
      ? { ...a }
      : {
          title: "",
          department: props.defaults.department || (departments.value.length === 1 ? departments.value[0] : ""),
          status: "Proposed",
          start_date: props.defaults.start_date || "",
          end_date: props.defaults.start_date || "",
          all_day: 0,
          start_time: "14:00",
          end_time: "17:00",
          venue: "Church",
          location_details: "",
          service_relation: "Separate from worship service",
          budget: null,
          transport_needed: 0,
          headcount: null,
          notes: "",
          is_public: 1,
          gpoa: props.defaults.gpoa || null,
        };
    form.value.all_day = form.value.all_day ? 1 : 0;
    days.value = spanDays(form.value.start_date, form.value.end_date);
    check();
  }
);

function spanDays(s, e) {
  if (!s || !e) return 1;
  return Math.max(1, Math.round((new Date(e) - new Date(s)) / 86400000) + 1);
}
// Keep end date following start date + number of days.
watch(
  () => [form.value.start_date, days.value],
  ([s, n]) => {
    if (s) form.value.end_date = addDays(s, Math.max(1, Number(n) || 1) - 1);
  }
);

let timer = null;
watch(
  () => [form.value.start_date, form.value.end_date, form.value.all_day, form.value.start_time, form.value.end_time, form.value.venue, form.value.service_relation, form.value.status],
  () => {
    clearTimeout(timer);
    timer = setTimeout(check, 350);
  }
);

async function check() {
  if (!props.isOpen || !form.value.start_date || readOnly.value) return;
  checking.value = true;
  try {
    conflicts.value = await call(API + "check_activity", { data: JSON.stringify(form.value) });
  } catch {
    conflicts.value = [];
  } finally {
    checking.value = false;
  }
}

const serviceConflicts = computed(() => conflicts.value.filter((c) => c.kind === "service"));
const venueConflicts = computed(() => conflicts.value.filter((c) => c.kind === "venue"));
const blocked = computed(
  () => venueConflicts.value.length > 0 || (form.value.service_relation === "Separate from worship service" && serviceConflicts.value.length > 0)
);

async function save() {
  errorMsg.value = "";
  if (!form.value.title?.trim() || !form.value.department || !form.value.start_date) {
    errorMsg.value = "Fill in the title, department and date.";
    return;
  }
  saving.value = true;
  try {
    const saved = await call(API + "save_activity", { data: JSON.stringify(form.value) });
    emit("saved", saved);
  } catch (e) {
    errorMsg.value = e.messages?.join(" ") || e.message;
  } finally {
    saving.value = false;
  }
}

async function remove() {
  if (!confirm(`Delete “${form.value.title}”? To keep a record of it, set the status to Cancelled instead.`)) return;
  saving.value = true;
  try {
    await call(API + "delete_activity", { name: form.value.name });
    emit("deleted", form.value.name);
  } catch (e) {
    errorMsg.value = e.message;
  } finally {
    saving.value = false;
  }
}

async function decide(decision) {
  const remarks = decision === "Declined" ? prompt("Reason (shown to the planner):") : "";
  if (decision === "Declined" && remarks === null) return;
  saving.value = true;
  try {
    const saved = await call(API + "decide_service_replacement", { name: form.value.name, decision, remarks });
    emit("saved", saved);
  } catch (e) {
    errorMsg.value = e.message;
  } finally {
    saving.value = false;
  }
}

async function addVenue() {
  const v = newVenue.value;
  if (!v?.name?.trim()) return;
  try {
    const name = await call(API + "add_venue", { venue_name: v.name.trim(), on_premises: v.on_premises ? 1 : 0 });
    props.options.venues?.push({ name, on_premises: v.on_premises ? 1 : 0 });
    form.value.venue = name;
    newVenue.value = null;
  } catch (e) {
    errorMsg.value = e.message;
  }
}
</script>

<template>
  <Teleport to="body">
    <div v-if="isOpen" class="fixed inset-0 z-[60] flex items-end sm:items-center justify-center sm:p-4">
      <div class="absolute inset-0 bg-gray-900/40 backdrop-blur-sm" @click="!saving && emit('close')" />
      <div class="relative bg-white rounded-t-2xl sm:rounded-2xl shadow-2xl w-full max-w-xl p-5 anim-pop max-h-[92dvh] overflow-y-auto">
        <div class="flex items-start justify-between gap-3 mb-4">
          <div class="min-w-0">
            <h3 class="text-base font-bold text-gray-900">{{ activity ? (readOnly ? "Activity" : "Edit activity") : "New activity" }}</h3>
            <p v-if="activity" class="text-xs text-gray-500 mt-0.5">{{ fmtRange(activity) }}</p>
            <p v-if="activity?.regular_activity" class="text-[11px] text-gray-400 mt-0.5">Generated from a regular activity. Editing it keeps it when the dates are regenerated.</p>
          </div>
          <button type="button" class="w-8 h-8 rounded-lg flex items-center justify-center text-gray-400 hover:text-gray-600 hover:bg-gray-100 shrink-0" aria-label="Close" @click="!saving && emit('close')">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>

        <fieldset :disabled="readOnly || saving" class="space-y-3">
          <label class="block">
            <span class="text-xs font-semibold text-gray-600">Title</span>
            <input v-model="form.title" type="text" class="cm-field mt-1" placeholder="e.g. YP Retreat" />
          </label>

          <div class="grid grid-cols-2 gap-3">
            <label class="block">
              <span class="text-xs font-semibold text-gray-600">Department</span>
              <select v-model="form.department" class="cm-field cm-select mt-1">
                <option value="" disabled>Choose…</option>
                <option v-for="d in departments" :key="d" :value="d">{{ d }}</option>
                <option v-if="form.department && !departments.includes(form.department)" :value="form.department">{{ form.department }}</option>
              </select>
            </label>
            <label class="block">
              <span class="text-xs font-semibold text-gray-600">Status</span>
              <select v-model="form.status" class="cm-field cm-select mt-1">
                <option v-for="s in statusOptions" :key="s" :value="s">{{ s }}</option>
              </select>
            </label>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <label class="block">
              <span class="text-xs font-semibold text-gray-600">Date</span>
              <input v-model="form.start_date" type="date" class="cm-field mt-1" />
            </label>
            <label class="block">
              <span class="text-xs font-semibold text-gray-600">Number of days</span>
              <input v-model.number="days" type="number" min="1" max="30" class="cm-field mt-1" />
            </label>
          </div>

          <div class="flex items-center gap-4 flex-wrap">
            <label class="inline-flex items-center gap-2 text-sm text-gray-700">
              <input v-model="form.all_day" type="checkbox" :true-value="1" :false-value="0" class="rounded border-gray-300" /> All day
            </label>
            <template v-if="!form.all_day">
              <input v-model="form.start_time" type="time" class="cm-field !w-32" aria-label="Start time" />
              <span class="text-gray-400 text-sm">to</span>
              <input v-model="form.end_time" type="time" class="cm-field !w-32" aria-label="End time" />
            </template>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <label class="block">
              <span class="text-xs font-semibold text-gray-600">Venue</span>
              <select v-model="form.venue" class="cm-field cm-select mt-1">
                <option :value="null">Off-site / to be decided</option>
                <option v-for="v in options.venues || []" :key="v.name" :value="v.name">{{ v.name }}{{ v.on_premises ? " (church)" : "" }}</option>
              </select>
              <button v-if="!readOnly && !newVenue" type="button" class="mt-1 text-[11px] font-semibold text-brand-700 hover:underline" @click="newVenue = { name: '', on_premises: 0 }">+ New venue</button>
            </label>
            <label class="block">
              <span class="text-xs font-semibold text-gray-600">Place details</span>
              <input v-model="form.location_details" type="text" class="cm-field mt-1" placeholder="e.g. Tanay, Rizal" />
            </label>
          </div>
          <div v-if="newVenue" class="flex items-center gap-2 p-2 rounded-xl bg-gray-50">
            <input v-model="newVenue.name" type="text" class="cm-field !h-9" placeholder="Venue name" />
            <label class="inline-flex items-center gap-1 text-xs text-gray-600 shrink-0"><input v-model="newVenue.on_premises" type="checkbox" /> In church</label>
            <AppButton size="sm" @click="addVenue">Add</AppButton>
            <AppButton size="sm" variant="ghost" @click="newVenue = null">Cancel</AppButton>
          </div>

          <label class="block">
            <span class="text-xs font-semibold text-gray-600">Worship service</span>
            <select v-model="form.service_relation" class="cm-field cm-select mt-1">
              <option v-for="r in RELATIONS" :key="r.value" :value="r.value">{{ r.label }}</option>
            </select>
          </label>

          <div class="grid grid-cols-3 gap-3">
            <label class="block">
              <span class="text-xs font-semibold text-gray-600">Budget</span>
              <input v-model.number="form.budget" type="number" min="0" step="50" class="cm-field mt-1" placeholder="0" />
            </label>
            <label class="block">
              <span class="text-xs font-semibold text-gray-600">Headcount</span>
              <input v-model.number="form.headcount" type="number" min="0" class="cm-field mt-1" />
            </label>
            <label class="flex items-end gap-2 pb-3 text-sm text-gray-700">
              <input v-model="form.transport_needed" type="checkbox" :true-value="1" :false-value="0" class="rounded border-gray-300" /> Transport
            </label>
          </div>

          <label class="block">
            <span class="text-xs font-semibold text-gray-600">Notes</span>
            <textarea v-model="form.notes" rows="2" class="cm-field mt-1 !h-auto py-2" />
          </label>
          <label class="inline-flex items-center gap-2 text-sm text-gray-700">
            <input v-model="form.is_public" type="checkbox" :true-value="1" :false-value="0" class="rounded border-gray-300" /> Show on the public calendar (once confirmed and the year is published; budget, transport and notes stay private)
          </label>
        </fieldset>

        <!-- Conflicts -->
        <div v-if="!readOnly" class="mt-4 space-y-2" aria-live="polite">
          <div v-if="venueConflicts.length" class="p-3 rounded-xl bg-red-50 text-red-800 text-xs">
            <p class="font-bold mb-1">Venue already taken</p>
            <p v-for="(c, i) in venueConflicts" :key="'v' + i">{{ c.message }}</p>
          </div>
          <div v-if="serviceConflicts.length" class="p-3 rounded-xl text-xs"
               :class="form.service_relation === REPLACES ? 'bg-amber-50 text-amber-900' : 'bg-red-50 text-red-800'">
            <p class="font-bold mb-1">{{ form.service_relation === REPLACES ? "Replaces a worship service — needs the pastor's approval" : "Overlaps a worship service" }}</p>
            <p v-for="(c, i) in serviceConflicts" :key="'s' + i">{{ c.message }}</p>
            <p v-if="form.service_relation !== REPLACES" class="mt-1">Change the time, mark it as part of the service, or ask the pastor to let it replace the service.</p>
          </div>
          <p v-if="!conflicts.length && form.start_date && !checking" class="text-xs text-emerald-700 font-semibold">No conflicts.</p>
        </div>

        <!-- Pastor approval -->
        <div v-if="activity?.service_relation === REPLACES" class="mt-3 p-3 rounded-xl bg-indigo-50 text-indigo-900 text-xs">
          <p><span class="font-bold">Pastor's approval:</span> {{ activity.pastor_approval || "Not requested yet" }}<span v-if="activity.approved_by"> · {{ activity.approved_by }}</span></p>
          <p v-if="activity.approval_remarks" class="mt-0.5">“{{ activity.approval_remarks }}”</p>
          <div v-if="options.is_pastor" class="mt-2 flex gap-2">
            <AppButton size="sm" :disabled="saving" @click="decide('Approved')">Approve</AppButton>
            <AppButton size="sm" variant="secondary" :disabled="saving" @click="decide('Declined')">Decline</AppButton>
          </div>
        </div>

        <div v-if="errorMsg" class="mt-3 p-2.5 rounded-xl bg-red-50 text-red-700 text-xs font-semibold">{{ errorMsg }}</div>

        <div class="mt-5 flex items-center justify-between gap-2">
          <AppButton v-if="activity?.name && !readOnly" variant="ghost" size="sm" class="!text-red-600" :disabled="saving" @click="remove">Delete</AppButton>
          <span v-else />
          <div class="flex gap-2">
            <AppButton variant="secondary" :disabled="saving" @click="emit('close')">{{ readOnly ? "Close" : "Cancel" }}</AppButton>
            <AppButton v-if="!readOnly" :loading="saving" :disabled="blocked" @click="save">Save</AppButton>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
