<script setup>
import { computed, ref } from "vue";
import { call } from "@/composables/useFrappeApi";
import AppButton from "@/components/AppButton.vue";
import { deptShort, peso } from "@/utils/calendar";

/** One-off purchases departments ask for (equipment, repairs, subscriptions). */
const props = defineProps({ data: { type: Object, required: true } });
const emit = defineEmits(["changed"]);

const SOURCES = ["", "General Fund", "White Gift", "Mission", "Benevolence", "Department Funds"];
const STATUSES = ["Requested", "Approved", "Declined", "Purchased"];
const STATUS_CLASS = {
  Requested: "bg-gray-100 text-gray-600",
  Approved: "bg-emerald-100 text-emerald-700",
  Declined: "bg-red-100 text-red-600",
  Purchased: "bg-sky-100 text-sky-700",
};
const departments = computed(() => props.data.my_departments ?? props.data.departments);
const isAdmin = computed(() => props.data.my_departments === null);
const rows = computed(() => [...props.data.requests].sort((a, b) => b.priority - a.priority || a.department.localeCompare(b.department)));
const totals = computed(() => {
  const t = { all: 0, approved: 0 };
  for (const r of props.data.requests) {
    if (r.status !== "Declined") t.all += r.amount || 0;
    if (r.status === "Approved" || r.status === "Purchased") t.approved += r.amount || 0;
  }
  return t;
});

const form = ref(null);
const busy = ref(false);
const errorMsg = ref("");
function openForm(r = null) {
  errorMsg.value = "";
  form.value = r ? { ...r } : {
    gpoa: props.data.gpoa.name, department: departments.value.length === 1 ? departments.value[0] : "Pasig General",
    area: "", description: "", amount: null, source_of_fund: "", priority: 0, status: "Requested", notes: "",
  };
  form.value.gpoa = props.data.gpoa.name;
}
async function save() {
  if (!form.value.department || !form.value.description?.trim()) {
    errorMsg.value = "Choose the department and describe the request.";
    return;
  }
  busy.value = true;
  try {
    await call("church_management.api.gpoa.save_budget_request", { data: JSON.stringify(form.value) });
    form.value = null;
    emit("changed");
  } catch (e) {
    errorMsg.value = e.message;
  } finally {
    busy.value = false;
  }
}
async function remove() {
  if (!confirm(`Delete “${form.value.description}”?`)) return;
  busy.value = true;
  try {
    await call("church_management.api.gpoa.delete_budget_request", { name: form.value.name });
    form.value = null;
    emit("changed");
  } catch (e) {
    errorMsg.value = e.message;
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div>
    <div class="flex flex-wrap items-center justify-between gap-3 mb-3">
      <p class="text-xs text-gray-500">Requested {{ peso(totals.all) }} · approved {{ peso(totals.approved) }}</p>
      <AppButton size="sm" @click="openForm()">+ Budget request</AppButton>
    </div>
    <p v-if="!rows.length" class="p-6 text-center text-sm text-gray-400 bg-white rounded-2xl border border-gray-200">No budget requests yet.</p>
    <div v-else class="bg-white rounded-2xl border border-gray-200 divide-y divide-gray-100">
      <button v-for="r in rows" :key="r.name" class="w-full text-left px-4 py-2.5 flex flex-wrap items-center gap-x-3 gap-y-1 hover:bg-gray-50 disabled:hover:bg-white" :disabled="!r.can_edit" @click="openForm(r)">
        <span class="min-w-0 flex-1">
          <span class="block text-sm font-semibold text-gray-900">
            <span v-if="r.priority" class="mr-1 text-[10px] font-bold uppercase text-amber-700 bg-amber-100 px-1.5 py-0.5 rounded">Priority</span>{{ r.description }}
          </span>
          <span class="block text-xs text-gray-500">{{ deptShort(r.department) }}<template v-if="r.area"> · {{ r.area }}</template><template v-if="r.source_of_fund"> · from {{ r.source_of_fund }}</template></span>
        </span>
        <span class="text-[10px] font-bold uppercase px-2 py-0.5 rounded-md" :class="STATUS_CLASS[r.status]">{{ r.status }}</span>
        <span class="w-24 text-right text-sm font-semibold tabular">{{ r.amount ? peso(r.amount) : "—" }}</span>
      </button>
    </div>

    <Teleport to="body">
      <div v-if="form" class="fixed inset-0 z-[60] flex items-end sm:items-center justify-center sm:p-4">
        <div class="absolute inset-0 bg-gray-900/40 backdrop-blur-sm" @click="!busy && (form = null)" />
        <div class="relative bg-white rounded-t-2xl sm:rounded-2xl shadow-2xl w-full max-w-lg p-5 anim-pop max-h-[92dvh] overflow-y-auto">
          <h3 class="text-base font-bold text-gray-900 mb-4">{{ form.name ? "Edit" : "New" }} budget request</h3>
          <div class="space-y-3">
            <div class="grid grid-cols-2 gap-3">
              <label class="block"><span class="text-xs font-semibold text-gray-600">Department</span>
                <select v-model="form.department" class="cm-field cm-select mt-1"><option v-for="d in departments" :key="d" :value="d">{{ d }}</option></select>
              </label>
              <label class="block"><span class="text-xs font-semibold text-gray-600">Area</span>
                <input v-model="form.area" class="cm-field mt-1" placeholder="e.g. Kitchen, 4th floor" />
              </label>
            </div>
            <label class="block"><span class="text-xs font-semibold text-gray-600">What is needed</span>
              <input v-model="form.description" class="cm-field mt-1" placeholder="e.g. Mic set for 4th floor" />
            </label>
            <div class="grid grid-cols-2 gap-3">
              <label class="block"><span class="text-xs font-semibold text-gray-600">Amount</span>
                <input v-model.number="form.amount" type="number" min="0" step="50" class="cm-field mt-1" />
              </label>
              <label class="block"><span class="text-xs font-semibold text-gray-600">Source of fund</span>
                <select v-model="form.source_of_fund" class="cm-field cm-select mt-1"><option v-for="s in SOURCES" :key="s" :value="s">{{ s || "Not decided" }}</option></select>
              </label>
            </div>
            <div class="grid grid-cols-2 gap-3 items-end">
              <label class="block"><span class="text-xs font-semibold text-gray-600">Status</span>
                <select v-model="form.status" class="cm-field cm-select mt-1" :disabled="!isAdmin"><option v-for="s in STATUSES" :key="s">{{ s }}</option></select>
              </label>
              <label class="inline-flex items-center gap-2 pb-3 text-sm text-gray-700"><input v-model="form.priority" type="checkbox" :true-value="1" :false-value="0" class="rounded border-gray-300" /> Priority</label>
            </div>
            <label class="block"><span class="text-xs font-semibold text-gray-600">Notes</span>
              <textarea v-model="form.notes" rows="2" class="cm-field mt-1 !h-auto py-2" />
            </label>
          </div>
          <div v-if="errorMsg" class="mt-3 p-2.5 rounded-xl bg-red-50 text-red-700 text-xs font-semibold">{{ errorMsg }}</div>
          <div class="mt-5 flex items-center justify-between gap-2">
            <AppButton v-if="form.name" variant="ghost" size="sm" class="!text-red-600" :disabled="busy" @click="remove">Delete</AppButton>
            <span v-else />
            <div class="flex gap-2">
              <AppButton variant="secondary" :disabled="busy" @click="form = null">Cancel</AppButton>
              <AppButton :loading="busy" @click="save">Save</AppButton>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
