<script setup>
import { computed, ref, watch } from "vue";
import { useQuery } from "@pinia/colada";
import { call } from "@/composables/useFrappeApi";
import CurrencyDisplay from "@/components/CurrencyDisplay.vue";
import AppButton from "@/components/AppButton.vue";

const props = defineProps({
  item: { type: Object, default: null },
  type: { type: String, default: "item" },
  disbursementName: { type: String, default: "" },
});

const emit = defineEmits(["close", "claim", "updated"]);

const isOpen = computed(() => !!props.item);
const state = computed(() => props.item?.status || "Unclaimed");
const isClaimed = computed(() => state.value === "Claimed");
const isVoided = computed(() => state.value === "Voided");
const isUnclaimed = computed(() => state.value === "Unclaimed");
const hasWorker = computed(() => props.item && props.item.worker !== undefined && props.item.description === undefined);

const editForm = ref({ worker: "", purpose: "", department: "", source: "", is_planned: 0, amount: 0 });
// mode: null | "void" | "restore" | "reverse" | "edit-claim" | "delete"
const mode = ref(null);
const reason = ref("");
const claimForm = ref({ amount: 0, received_by: "", received_date: "", source: "" });
const busy = ref(false);
const showHistory = ref(false);

watch(
  () => props.item,
  (val) => {
    mode.value = null;
    reason.value = "";
    showHistory.value = false;
    if (val) {
      editForm.value = {
        worker: val.worker || "",
        purpose: val.purpose || "",
        department: val.department || "",
        source: val.source || "",
        is_planned: val.is_planned ? 1 : 0,
        amount: val.amount || 0,
      };
      claimForm.value = {
        amount: val.amount || 0,
        received_by: val.received_by || "",
        received_date: val.received_date || "",
        source: val.source || "",
      };
    }
  }
);

const { data: workers } = useQuery({
  key: ["workers"],
  query: () => call("church_management.api.disbursement.get_workers"),
  enabled: () => isOpen.value,
});
const { data: purposes } = useQuery({
  key: ["purposes"],
  query: () => call("church_management.api.disbursement.get_purposes"),
  enabled: () => isOpen.value,
});
const { data: departments } = useQuery({
  key: ["departments"],
  query: () => call("church_management.api.disbursement.get_departments"),
  enabled: () => isOpen.value,
});
const { data: accounts } = useQuery({
  key: ["accounts"],
  query: () => call("church_management.api.disbursement.get_source_accounts"),
  enabled: () => isOpen.value,
});
const { data: history, refetch: refetchHistory, isPending: historyLoading } = useQuery({
  key: () => ["line-history", props.disbursementName, props.item?.name],
  query: () =>
    call("church_management.api.disbursement.get_history", {
      disbursement_name: props.disbursementName,
      child_name: props.item.name,
    }),
  enabled: () => isOpen.value && showHistory.value && !!props.item?.name,
});

const fields = computed(() => {
  if (!props.item) return [];
  const i = props.item;
  const out = [];
  if (!isUnclaimed.value) {
    if (i.worker) out.push({ label: "Worker", value: i.worker });
    out.push({ label: "Source", value: i.source || "—" });
  }
  if (i.description) out.push({ label: "Description", value: i.description });
  if (isClaimed.value) {
    if (i.paid_by === "Creditor") {
      out.push({ label: "Paid by", value: i.creditor || "Creditor" });
      out.push({ label: "Date creditor paid", value: i.creditor_paid_date || "—" });
      if (i.creditor_reference) out.push({ label: "Creditor reference", value: i.creditor_reference });
      if (i.payable) out.push({ label: "Payable", value: i.payable });
    }
    out.push({ label: "Received By", value: i.received_by || "—" });
    out.push({ label: "Received Date", value: i.received_date || "—" });
  }
  if (isVoided.value) {
    out.push({ label: "Purpose", value: i.purpose || "—" });
    out.push({ label: "Department", value: i.department || "—" });
    out.push({ label: "Void reason", value: i.void_reason || "—" });
  }
  if (i.remarks) out.push({ label: "Remarks", value: i.remarks });
  return out;
});

function errMsg(err) {
  return err.messages?.[0] || err.message || "Something went wrong";
}

async function run(method, params, { close = true } = {}) {
  busy.value = true;
  try {
    const res = await call(`church_management.api.disbursement.${method}`, {
      disbursement_name: props.disbursementName,
      child_name: props.item.name,
      ...params,
    });
    if (res?.warnings?.length) alert(res.warnings.join("\n\n"));
    emit("updated");
    if (close) emit("close");
    return res;
  } catch (err) {
    alert(errMsg(err));
  } finally {
    busy.value = false;
  }
}

function saveItem() {
  const updates = isClaimed.value
    ? { purpose: editForm.value.purpose, department: editForm.value.department }
    : { ...editForm.value };
  if (!hasWorker.value) delete updates.worker;
  return run("update_item", {
    child_doctype: props.item.doctype || "Disbursement Week Item",
    updates: JSON.stringify(updates),
  });
}

function needReason() {
  if ((reason.value || "").trim().length < 5) {
    alert("Please type a reason (at least 5 characters).");
    return true;
  }
  return false;
}

function confirmMode() {
  if (mode.value === "delete") {
    return run("delete_item", { reason: reason.value });
  }
  if (needReason()) return;
  if (mode.value === "void") return run("void_line", { reason: reason.value });
  if (mode.value === "restore") return run("unvoid_line", { reason: reason.value });
  if (mode.value === "reverse") return run("reverse_claim", { reason: reason.value });
  if (mode.value === "edit-claim") {
    const changes = {};
    for (const k of ["amount", "received_by", "received_date", "source"]) {
      const before = k === "amount" ? Number(props.item[k] || 0) : props.item[k] || "";
      const after = k === "amount" ? Number(claimForm.value[k] || 0) : claimForm.value[k] || "";
      if (before !== after) changes[k] = after;
    }
    if (!Object.keys(changes).length) {
      alert("Nothing changed.");
      return;
    }
    return run("edit_claim", { changes: JSON.stringify(changes), reason: reason.value });
  }
}

const modeTitle = computed(
  () =>
    ({
      void: "Void this line",
      restore: "Restore this line",
      reverse: "Reverse this claim",
      "edit-claim": "Correct this claim",
      delete: "Delete this line",
    })[mode.value] || ""
);
const modeHelp = computed(
  () =>
    ({
      void: "A voided line is discontinued and will never be paid. It stays visible, greyed out, but is left out of pending, totals and every report.",
      restore: "The line goes back to Unclaimed and counts again.",
      reverse: "The line goes back to Unclaimed and Received By / Received Date are cleared. The claim stays in the history.",
      "edit-claim": "Fix a claim made with the wrong amount, person, date or account. The old and new values are kept in the history.",
      delete: "Only for a line added by mistake. To stop a real commitment, Void it instead.",
    })[mode.value] || ""
);

function openHistory() {
  showHistory.value = !showHistory.value;
  if (showHistory.value) refetchHistory();
}

function fmtWhen(ts) {
  if (!ts) return "";
  return new Date(ts.replace(" ", "T")).toLocaleString("en-PH", {
    month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit",
  });
}
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="isOpen" class="fixed inset-0 z-[60] flex items-end sm:items-center justify-center" @click.self="emit('close')">
        <div class="absolute inset-0 bg-black/40" @click="emit('close')" />

        <div class="relative w-full sm:max-w-md bg-white rounded-t-2xl sm:rounded-2xl shadow-xl max-h-[90vh] flex flex-col">
          <div class="sm:hidden flex justify-center pt-3 pb-1">
            <div class="w-8 h-1 rounded-full bg-gray-300" />
          </div>

          <!-- Header -->
          <div class="flex items-start justify-between px-5 pt-3 sm:pt-5 pb-3 border-b border-gray-100">
            <div class="min-w-0">
              <h3 class="text-base font-bold text-gray-900 truncate">
                {{ item?.worker || item?.description || "Item Detail" }}
              </h3>
              <div class="flex items-center gap-2 mt-1">
                <span
                  class="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full"
                  :class="isClaimed ? 'bg-green-50 text-green-700' : isVoided ? 'bg-gray-100 text-gray-600' : 'bg-amber-50 text-amber-700'"
                >
                  <span class="w-1.5 h-1.5 rounded-full" :class="isClaimed ? 'bg-green-400' : isVoided ? 'bg-gray-400' : 'bg-amber-400'" />
                  {{ state }}
                </span>
                <span v-if="item?.amount_edited" class="text-xs text-gray-400 line-through">
                  <CurrencyDisplay :value="item?.original_amount" size="xs" />
                </span>
                <span :class="isVoided ? 'line-through' : ''"><CurrencyDisplay :value="item?.amount" /></span>
              </div>
            </div>
            <button @click="emit('close')" class="p-1.5 -mr-1 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors" aria-label="Close">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>

          <!-- Body -->
          <div class="flex-1 overflow-y-auto px-5 py-4 space-y-4">
            <!-- Correction / void / restore panel -->
            <div v-if="mode" class="p-3 rounded-xl border space-y-3" :class="mode === 'void' || mode === 'delete' ? 'bg-red-50/60 border-red-100' : 'bg-amber-50/60 border-amber-100'">
              <div>
                <p class="text-sm font-bold text-gray-900">{{ modeTitle }}</p>
                <p class="text-xs text-gray-600 mt-0.5">{{ modeHelp }}</p>
              </div>
              <template v-if="mode === 'edit-claim'">
                <div class="grid grid-cols-2 gap-2">
                  <div>
                    <label class="block text-[11px] font-semibold text-gray-500 uppercase tracking-wide mb-1">Amount</label>
                    <input v-model.number="claimForm.amount" type="number" min="0" step="0.01" class="cm-field text-right tabular" />
                  </div>
                  <div>
                    <label class="block text-[11px] font-semibold text-gray-500 uppercase tracking-wide mb-1">Received date</label>
                    <input v-model="claimForm.received_date" type="date" class="cm-field" />
                  </div>
                </div>
                <div>
                  <label class="block text-[11px] font-semibold text-gray-500 uppercase tracking-wide mb-1">Received by</label>
                  <select v-model="claimForm.received_by" class="cm-field cm-select">
                    <option value="">—</option>
                    <option v-for="w in workers" :key="w.name" :value="w.name">{{ w.full_name }}</option>
                  </select>
                </div>
                <div>
                  <label class="block text-[11px] font-semibold text-gray-500 uppercase tracking-wide mb-1">Source account</label>
                  <select v-model="claimForm.source" class="cm-field cm-select">
                    <option v-for="a in accounts" :key="a.name" :value="a.name">{{ a.account_name || a.name }}</option>
                  </select>
                </div>
              </template>
              <div>
                <label class="block text-[11px] font-semibold text-gray-500 uppercase tracking-wide mb-1">
                  Reason <span v-if="mode !== 'delete'" class="text-red-500">*</span>
                </label>
                <textarea v-model="reason" rows="2" class="cm-field resize-none"
                  :placeholder="mode === 'void' ? 'e.g. Discontinued — will not be paid' : 'Why is this being changed?'" />
              </div>
              <div class="flex gap-2">
                <AppButton variant="secondary" size="sm" class="flex-1" @click="mode = null">Cancel</AppButton>
                <AppButton :variant="mode === 'void' || mode === 'delete' ? 'danger' : 'primary'" size="sm" class="flex-1" :loading="busy" @click="confirmMode">
                  {{ modeTitle }}
                </AppButton>
              </div>
            </div>

            <!-- Edit form: everything while unclaimed; only purpose/department once claimed -->
            <div v-if="!isVoided && !mode" class="space-y-3 p-3 bg-gray-50 rounded-xl border border-gray-100">
              <div v-if="hasWorker && isUnclaimed">
                <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">Worker</label>
                <select v-model="editForm.worker" class="cm-field cm-select">
                  <option value="">Select Worker</option>
                  <option v-for="w in workers" :key="w.name" :value="w.name">{{ w.full_name }}</option>
                </select>
              </div>
              <div class="grid grid-cols-2 gap-2">
                <div>
                  <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">Purpose</label>
                  <select v-model="editForm.purpose" class="cm-field cm-select">
                    <option value="">Select Purpose</option>
                    <option v-for="p in purposes" :key="p.name" :value="p.name">{{ p.name }}</option>
                  </select>
                </div>
                <div>
                  <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">Department <span class="text-red-500">*</span></label>
                  <select v-model="editForm.department" class="cm-field cm-select">
                    <option value="">Select Department</option>
                    <option v-for="d in departments" :key="d.name" :value="d.name">{{ d.name }}</option>
                  </select>
                </div>
              </div>
              <template v-if="isUnclaimed">
                <div>
                  <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">Source</label>
                  <select v-model="editForm.source" class="cm-field cm-select">
                    <option value="">Select Source</option>
                    <option v-for="a in accounts" :key="a.name" :value="a.name">{{ a.account_name || a.name }}</option>
                  </select>
                </div>
                <div>
                  <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">
                    Amount
                    <span v-if="item?.amount_edited" class="ml-1 text-[10px] text-amber-600 normal-case font-bold">edited</span>
                  </label>
                  <input v-model.number="editForm.amount" type="number" min="0" step="0.01" class="cm-field text-right tabular" />
                  <p v-if="item?.amount_edited" class="mt-1 text-[11px] text-gray-500">
                    Original: <span class="line-through ml-1"><CurrencyDisplay :value="item.original_amount" size="xs" /></span>
                  </p>
                </div>
                <div v-if="item?.is_planned !== undefined">
                  <label class="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">Is Planned</label>
                  <select v-model="editForm.is_planned" class="cm-field cm-select">
                    <option :value="1">Yes</option>
                    <option :value="0">No</option>
                  </select>
                </div>
              </template>
              <AppButton variant="outline" size="sm" class="w-full" :loading="busy" @click="saveItem">Save details</AppButton>
            </div>

            <!-- Read-only fields -->
            <div class="space-y-2">
              <div v-for="field in fields" :key="field.label" class="flex items-start justify-between gap-4 py-1">
                <span class="text-xs text-gray-400 uppercase tracking-wider shrink-0">{{ field.label }}</span>
                <span class="text-sm font-medium text-gray-800 text-right break-words">{{ field.value }}</span>
              </div>
            </div>

            <!-- History -->
            <div class="border-t border-gray-100 pt-3">
              <button class="text-xs font-bold text-brand-600 uppercase tracking-wider" @click="openHistory">
                {{ showHistory ? "Hide history" : "Show history" }}
              </button>
              <div v-if="showHistory" class="mt-2 space-y-2">
                <p v-if="historyLoading" class="text-xs text-gray-400">Loading…</p>
                <p v-else-if="!history?.length" class="text-xs text-gray-400">No changes recorded yet.</p>
                <div v-for="h in history || []" :key="h.name" class="text-xs border-l-2 pl-2.5" :class="h.action === 'Void' || h.action === 'Reverse Claim' ? 'border-amber-300' : 'border-gray-200'">
                  <p class="font-bold text-gray-800">{{ h.action }} <span class="font-normal text-gray-400">· {{ fmtWhen(h.timestamp) }} · {{ h.user_name }}</span></p>
                  <p class="text-gray-600 whitespace-pre-line">{{ h.summary }}</p>
                  <p v-if="h.reason" class="text-gray-500 italic">“{{ h.reason }}”</p>
                </div>
              </div>
            </div>
          </div>

          <!-- Footer actions -->
          <div v-if="!mode" class="px-5 py-4 border-t border-gray-100 flex flex-wrap gap-2">
            <template v-if="isUnclaimed">
              <button @click="mode = 'delete'" :disabled="busy" title="Delete line"
                class="w-10 flex-shrink-0 flex items-center justify-center rounded-xl border border-red-200 text-red-600 hover:bg-red-50 disabled:opacity-50">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
              </button>
              <AppButton variant="outline" class="flex-1" @click="mode = 'void'; reason = 'Discontinued — will not be paid'">Void</AppButton>
              <AppButton class="flex-1" @click="emit('claim', item)">Claim</AppButton>
            </template>
            <template v-else-if="isClaimed">
              <AppButton variant="outline" class="flex-1" @click="mode = 'reverse'">Reverse claim</AppButton>
              <AppButton class="flex-1" @click="mode = 'edit-claim'">Edit claim</AppButton>
            </template>
            <template v-else>
              <AppButton class="flex-1" @click="mode = 'restore'">Restore line</AppButton>
            </template>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-enter-active,
.modal-leave-active { transition: opacity 0.2s ease; }
.modal-enter-active > div:last-child,
.modal-leave-active > div:last-child { transition: transform 0.2s ease; }
.modal-enter-from,
.modal-leave-to { opacity: 0; }
.modal-enter-from > div:last-child { transform: translateY(100%); }
@media (min-width: 640px) {
  .modal-enter-from > div:last-child { transform: translateY(16px) scale(0.95); }
}
</style>
