<script setup>
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useQuery, useQueryCache } from "@pinia/colada";
import { call } from "@/composables/useFrappeApi";
import { useSessionStore } from "@/stores/session";
import PageHeader from "@/components/PageHeader.vue";
import AppButton from "@/components/AppButton.vue";
import CurrencyDisplay from "@/components/CurrencyDisplay.vue";
import InviteDonationModal from "@/components/InviteDonationModal.vue";
import PurposeModal from "@/components/PurposeModal.vue";

const props = defineProps({ name: { type: String, required: true } });

const router = useRouter();
const session = useSessionStore();
const queryCache = useQueryCache();

const rows = ref([]);
const expenseRows = ref([]);
const saving = ref(false);
const deleting = ref(false);
const errorMsg = ref("");
const savedMsg = ref("");
const dirty = ref(false);
const showInvite = ref(false);
const showPurposes = ref(false);
const pendingDelete = ref(null); // row index awaiting delete confirmation

const { data: doc, isPending: loading, error } = useQuery({
  key: () => ["donation", props.name],
  query: () => call("church_management.api.donation.get_detail", { name: props.name }),
});

const { data: purposes } = useQuery({
  key: ["donation-purposes"],
  query: () => call("church_management.api.donation.get_purposes"),
  staleTime: 5 * 60 * 1000,
});

function blankRow() {
  return {
    name: null,
    date_donated: new Date().toISOString().slice(0, 10),
    amount_donated: null,
    donation_type: "Cash",
    purpose: "",
    description: "",
    approval_status: "",
    journal_entry: null,
    approved_by: null,
  };
}

watch(
  doc,
  (d) => {
    if (!d) return;
    rows.value = (d.donated_amounts || []).map((r) => ({
      name: r.name || null,
      date_donated: r.date_donated || "",
      amount_donated: r.amount_donated ?? null,
      donation_type: r.donation_type || "Cash",
      purpose: r.purpose || "",
      description: r.description || "",
      approval_status: r.approval_status || "",
      journal_entry: r.journal_entry || null,
      approved_by: r.approved_by || null,
    }));
    expenseRows.value = (d.expenses || []).map((r) => ({
      date_spent: r.date_spent || "",
      amount_spent: r.amount_spent ?? null,
      description: r.description || "",
    }));
    dirty.value = false;
  },
  { immediate: true }
);

// Shown wherever a mission entry needs explaining.
const MISSION_HINT =
  "Mission donations become part of the church Mission Funds and are subject to admin approval " +
  "before they count as mission funding. They are not part of your department's spendable balance.";

// Mission purposes need admin approval before they post to the ledger.
const missionSet = computed(
  () => new Set((purposes.value || []).filter((p) => p.is_mission).map((p) => p.name))
);
function isApproved(r) {
  return r.approval_status === "Approved";
}
function isMissionRow(r) {
  return !isApproved(r) && missionSet.value.has(r.purpose);
}

function addRow() {
  rows.value.push(blankRow());
  dirty.value = true;
}
function rowIsEmpty(r) {
  return !Number(r.amount_donated) && !r.purpose && !r.description;
}
function requestRemoveRow(i) {
  // Approved rows are posted to the ledger — the server would restore them
  // anyway, so don't even offer.
  if (isApproved(rows.value[i])) return;
  // Untouched rows vanish without ceremony; real entries need a confirmation.
  if (rowIsEmpty(rows.value[i])) {
    removeRow(i);
    return;
  }
  pendingDelete.value = i;
}
function removeRow(i) {
  rows.value.splice(i, 1);
  pendingDelete.value = null;
  dirty.value = true;
}
function markDirty() {
  dirty.value = true;
  savedMsg.value = "";
}

function blankExpense() {
  return {
    date_spent: new Date().toISOString().slice(0, 10),
    amount_spent: null,
    description: "",
  };
}
function addExpense() {
  expenseRows.value.push(blankExpense());
  dirty.value = true;
}
function removeExpense(i) {
  const r = expenseRows.value[i];
  const hasContent = Number(r.amount_spent) || r.description;
  if (hasContent && !window.confirm("Remove this expense? This only takes effect once you save.")) return;
  expenseRows.value.splice(i, 1);
  dirty.value = true;
}

const totals = computed(() => {
  let cash = 0;
  let cashless = 0;
  let mission = 0;
  for (const r of rows.value) {
    const amt = Number(r.amount_donated) || 0;
    if (r.donation_type === "GCash") cashless += amt;
    else cash += amt;
    // Mission entries are set aside for the Mission funds — not spendable here.
    if (missionSet.value.has(r.purpose) || r.approval_status === "Pending" || r.approval_status === "Approved")
      mission += amt;
  }
  const expenses = expenseRows.value.reduce((s, r) => s + (Number(r.amount_spent) || 0), 0);
  const total = cash + cashless;
  const spendable = total - mission;
  return { cash, cashless, total, mission, expenses, spendable, remaining: spendable - expenses };
});

const hasMissionRows = computed(() =>
  rows.value.some(
    (r) => missionSet.value.has(r.purpose) || r.approval_status === "Pending" || r.approval_status === "Approved"
  )
);

// Everyone invited to record on this document: assigned_to + assignees table.
const recorders = computed(() => {
  const d = doc.value;
  if (!d) return [];
  const extra = (d.assignees || []).map((a) => a.user).filter((u) => u && u !== d.assigned_to);
  return [...(d.assigned_to ? [d.assigned_to] : []), ...extra];
});

const removingRecorder = ref(null); // recorder email currently being removed

async function removeRecorder(user) {
  errorMsg.value = "";
  savedMsg.value = "";
  if (dirty.value) {
    errorMsg.value = "Save your changes first, then remove the recorder.";
    return;
  }
  if (!window.confirm(`Remove ${user} from this record? They will no longer see it.`)) return;
  removingRecorder.value = user;
  try {
    const res = await call("church_management.api.donation.remove_recorder", {
      donation: props.name,
      user,
    });
    queryCache.setQueryData(["donation", props.name], res);
    queryCache.invalidateQueries({ key: ["donations"] });
    savedMsg.value = `${user} removed from this record.`;
  } catch (e) {
    errorMsg.value = e.message || "Failed to remove recorder.";
  } finally {
    removingRecorder.value = null;
  }
}

const approving = ref(null); // row name currently being approved

async function approveRow(row) {
  errorMsg.value = "";
  savedMsg.value = "";
  if (!row.name || dirty.value) {
    errorMsg.value = "Save your changes first, then approve.";
    return;
  }
  approving.value = row.name;
  try {
    const res = await call("church_management.api.donation.approve_mission_item", {
      donation: props.name,
      row_name: row.name,
    });
    queryCache.setQueryData(["donation", props.name], res);
    queryCache.invalidateQueries({ key: ["donations"] });
    savedMsg.value = "Mission entry approved — posted to the ledger.";
  } catch (e) {
    errorMsg.value = e.message || "Failed to approve.";
  } finally {
    approving.value = null;
  }
}

async function save() {
  errorMsg.value = "";
  savedMsg.value = "";
  const items = rows.value.filter((r) => Number(r.amount_donated) || r.purpose || r.description);
  for (const r of items) {
    if (isApproved(r)) continue; // locked server-side; sent only to keep order
    if (!r.date_donated) {
      errorMsg.value = "Every entry needs a date.";
      return;
    }
    if (!(Number(r.amount_donated) > 0)) {
      errorMsg.value = "Every entry needs an amount greater than zero.";
      return;
    }
  }
  const expenses = expenseRows.value.filter((r) => Number(r.amount_spent) || r.description);
  for (const r of expenses) {
    if (!r.date_spent) {
      errorMsg.value = "Every expense needs a date.";
      return;
    }
    if (!(Number(r.amount_spent) > 0)) {
      errorMsg.value = "Every expense needs an amount greater than zero.";
      return;
    }
  }
  saving.value = true;
  try {
    const saved = await call("church_management.api.donation.save_donation", {
      doc: { name: props.name, donated_amounts: items, expenses },
    });
    queryCache.setQueryData(["donation", props.name], saved);
    queryCache.invalidateQueries({ key: ["donations"] });
    dirty.value = false;
    savedMsg.value = "Saved.";
  } catch (e) {
    errorMsg.value = e.message || "Failed to save.";
  } finally {
    saving.value = false;
  }
}

function onInvited() {
  // assigned_to changed server-side — refresh the doc and the list totals.
  queryCache.invalidateQueries({ key: ["donation", props.name] });
  queryCache.invalidateQueries({ key: ["donations"] });
}

async function removeDonation() {
  if (!window.confirm(`Delete ${props.name}? This removes all its entries.`)) return;
  deleting.value = true;
  errorMsg.value = "";
  try {
    await call("church_management.api.donation.delete_donation", { name: props.name });
    queryCache.invalidateQueries({ key: ["donations"] });
    router.replace("/donations");
  } catch (e) {
    errorMsg.value = e.message || "Failed to delete.";
    deleting.value = false;
  }
}
</script>

<template>
  <div class="px-4 sm:px-6 py-4 sm:py-6 max-w-5xl mx-auto w-full">
    <PageHeader
      :title="doc ? `${doc.department} · ${doc.year}` : name"
      subtitle="Donation record"
    >
      <template #actions>
        <AppButton
          v-if="session.isDonationAdmin && doc"
          size="sm"
          variant="secondary"
          @click="showInvite = true"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75" />
          </svg>
          Invite
        </AppButton>
        <AppButton
          v-if="session.isDonationAdmin"
          size="sm"
          variant="danger"
          :loading="deleting"
          @click="removeDonation"
        >
          Delete
        </AppButton>
        <AppButton size="sm" :loading="saving" :disabled="!dirty" @click="save">Save</AppButton>
      </template>
    </PageHeader>

    <div class="mb-3">
      <RouterLink to="/donations" class="text-xs font-semibold text-brand-700 hover:underline">
        ← All donations
      </RouterLink>
    </div>

    <!-- Recorders: everyone invited to this record. Admins can remove them. -->
    <div v-if="recorders.length" class="mb-4 flex flex-wrap items-center gap-1.5">
      <span class="text-[11px] font-semibold text-gray-500 uppercase tracking-wider mr-1">Recorders</span>
      <span
        v-for="u in recorders"
        :key="u"
        class="inline-flex items-center gap-0.5 py-1 rounded-full bg-gray-100 text-xs font-medium text-gray-700"
        :class="session.isDonationAdmin ? 'pl-2.5 pr-1' : 'px-2.5'"
      >
        {{ u }}
        <button
          v-if="session.isDonationAdmin"
          type="button"
          class="w-5 h-5 rounded-full flex items-center justify-center text-gray-400 hover:text-rose-600 hover:bg-rose-100 transition-colors disabled:opacity-40"
          :disabled="removingRecorder === u"
          :aria-label="`Remove ${u} from this record`"
          :title="`Remove ${u} — they will no longer see this record`"
          @click="removeRecorder(u)"
        >
          <svg v-if="removingRecorder !== u" class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
          <svg v-else class="animate-spin w-3 h-3" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        </button>
      </span>
    </div>

    <div v-if="error" class="mb-4 p-3 bg-red-50 text-red-700 rounded-xl text-sm">{{ error.message }}</div>
    <div v-if="errorMsg" class="mb-4 p-3 bg-red-50 text-red-700 rounded-xl text-sm">{{ errorMsg }}</div>
    <div v-if="savedMsg" class="mb-4 p-3 bg-green-50 text-green-700 rounded-xl text-sm">{{ savedMsg }}</div>

    <div v-if="loading" class="py-16 text-center text-sm text-gray-400">Loading…</div>

    <template v-else-if="doc">
      <!-- Entries -->
      <div class="bg-white rounded-2xl border border-gray-200 overflow-hidden">
        <div class="hidden sm:grid grid-cols-[8.5rem_1fr_7.5rem_6.5rem_1fr_4.5rem] gap-2 px-4 py-2.5 bg-gray-50 border-b border-gray-100 text-[11px] font-semibold text-gray-500 uppercase tracking-wider">
          <span>Date</span>
          <span>Purpose</span>
          <span class="text-right">Amount</span>
          <span>Type</span>
          <span>Description</span>
          <span />
        </div>

        <p v-if="!rows.length" class="px-4 py-8 text-center text-sm text-gray-400">
          No entries yet — add the first donation below.
        </p>

        <div
          v-for="(row, i) in rows"
          :key="i"
          class="grid grid-cols-2 sm:grid-cols-[8.5rem_1fr_7.5rem_6.5rem_1fr_4.5rem] gap-2 px-4 py-3 border-b border-gray-100 items-center"
          :class="isApproved(row) ? 'bg-green-50/40' : ''"
        >
          <input v-model="row.date_donated" type="date" class="cm-field tabular" :disabled="isApproved(row)" @change="markDirty" />
          <select
            v-model="row.purpose"
            class="cm-field cm-select"
            :disabled="isApproved(row)"
            :title="(purposes || []).length ? (isMissionRow(row) ? MISSION_HINT : '') : 'No purposes defined yet — add them via Manage purposes below'"
            @change="markDirty"
          >
            <option value="">{{ (purposes || []).length ? "— Purpose —" : "No purposes yet" }}</option>
            <option v-for="p in purposes || []" :key="p.name" :value="p.name">{{ p.name }}</option>
          </select>
          <input
            v-model.number="row.amount_donated"
            type="number"
            min="0"
            step="0.01"
            inputmode="decimal"
            placeholder="0.00"
            class="cm-field text-right tabular"
            :disabled="isApproved(row)"
            @input="markDirty"
          />
          <select v-model="row.donation_type" class="cm-field cm-select" :disabled="isApproved(row)" @change="markDirty">
            <option>Cash</option>
            <option>GCash</option>
          </select>
          <input v-model="row.description" type="text" placeholder="Notes" class="cm-field" :disabled="isApproved(row)" @input="markDirty" />

          <div class="flex items-center gap-1 justify-self-end">
            <!-- Approved: locked, posted to ledger -->
            <span
              v-if="isApproved(row)"
              class="w-8 h-8 rounded-lg flex items-center justify-center bg-green-100 text-green-700"
              :title="`Approved by ${row.approved_by || 'admin'} — posted to ledger (${row.journal_entry || 'Journal Entry'}). This entry is locked.`"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
              </svg>
            </span>

            <template v-else-if="isMissionRow(row)">
              <!-- Admin: approve; posts the mission Journal Entry -->
              <button
                v-if="session.isDonationAdmin"
                type="button"
                class="w-8 h-8 rounded-lg flex items-center justify-center transition-colors"
                :class="!row.name || dirty
                  ? 'text-amber-300 cursor-not-allowed'
                  : 'text-amber-600 hover:text-green-700 hover:bg-green-50'"
                :disabled="approving === row.name"
                :title="!row.name || dirty ? 'Save first, then approve' : 'Approve — posts to the mission ledger'"
                @click="approveRow(row)"
              >
                <svg v-if="approving !== row.name" class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
                <svg v-else class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
              </button>
              <!-- Everyone else: pending marker -->
              <span
                v-else
                class="w-8 h-8 rounded-lg flex items-center justify-center bg-amber-50 text-amber-600"
                :title="`Awaiting admin approval. ${MISSION_HINT}`"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
                </svg>
              </span>
            </template>

            <button
              v-if="!isApproved(row)"
              type="button"
              class="w-8 h-8 rounded-lg flex items-center justify-center text-gray-300 hover:text-rose-600 hover:bg-rose-50 transition-colors"
              aria-label="Remove entry"
              @click="requestRemoveRow(i)"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <div class="px-4 py-3 flex items-center justify-between">
          <button
            type="button"
            class="text-xs font-semibold text-brand-700 hover:underline"
            @click="addRow"
          >
            + Add entry
          </button>
          <button
            type="button"
            class="text-xs font-semibold text-gray-400 hover:text-brand-700 hover:underline"
            @click="showPurposes = true"
          >
            Manage purposes
          </button>
        </div>

        <div
          v-if="hasMissionRows"
          class="px-4 py-2.5 bg-amber-50 border-t border-amber-100 flex items-start gap-2 text-xs text-amber-800"
        >
          <svg class="w-4 h-4 shrink-0 mt-0.5" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z" />
          </svg>
          <span>{{ MISSION_HINT }}</span>
        </div>
      </div>

      <!-- Expenses -->
      <div class="mt-6 bg-white rounded-2xl border border-gray-200 overflow-hidden">
        <div class="px-4 py-3 border-b border-gray-100">
          <h2 class="text-sm font-bold text-gray-900">Department Expenses</h2>
          <p class="text-xs text-gray-400 mt-0.5">
            Record what your department has spent, so you can track it against your collected donations
            (mission entries excluded — those go to the Mission Funds).
          </p>
        </div>

        <div class="hidden sm:grid grid-cols-[8.5rem_1fr_7.5rem_4.5rem] gap-2 px-4 py-2.5 bg-gray-50 border-b border-gray-100 text-[11px] font-semibold text-gray-500 uppercase tracking-wider">
          <span>Date</span>
          <span>Description</span>
          <span class="text-right">Amount</span>
          <span />
        </div>

        <p v-if="!expenseRows.length" class="px-4 py-6 text-center text-sm text-gray-400">
          No expenses recorded yet.
        </p>

        <div
          v-for="(row, i) in expenseRows"
          :key="i"
          class="grid grid-cols-2 sm:grid-cols-[8.5rem_1fr_7.5rem_4.5rem] gap-2 px-4 py-3 border-b border-gray-100 items-center"
        >
          <input v-model="row.date_spent" type="date" class="cm-field tabular" @change="markDirty" />
          <input v-model="row.description" type="text" placeholder="What was it spent on?" class="cm-field" @input="markDirty" />
          <input
            v-model.number="row.amount_spent"
            type="number"
            min="0"
            step="0.01"
            inputmode="decimal"
            placeholder="0.00"
            class="cm-field text-right tabular"
            @input="markDirty"
          />
          <button
            type="button"
            class="w-8 h-8 rounded-lg flex items-center justify-center justify-self-end text-gray-300 hover:text-rose-600 hover:bg-rose-50 transition-colors"
            aria-label="Remove expense"
            @click="removeExpense(i)"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="px-4 py-3">
          <button type="button" class="text-xs font-semibold text-brand-700 hover:underline" @click="addExpense">
            + Add expense
          </button>
        </div>
      </div>

      <!-- Totals -->
      <div class="mt-4 bg-white rounded-2xl border border-gray-200 px-4 py-3 flex flex-wrap items-center gap-x-8 gap-y-2">
        <div>
          <p class="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Cash</p>
          <CurrencyDisplay :value="totals.cash" />
        </div>
        <div>
          <p class="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">GCash</p>
          <CurrencyDisplay :value="totals.cashless" />
        </div>
        <div class="ml-auto text-right">
          <p class="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Total</p>
          <CurrencyDisplay :value="totals.total" size="lg" />
        </div>
      </div>

      <!-- Department budget: collected (excl. mission) vs spent -->
      <div class="mt-4 bg-white rounded-2xl border border-gray-200 px-4 py-3">
        <p class="text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-2">Department Budget</p>
        <div class="flex flex-wrap items-center gap-x-8 gap-y-2">
          <div>
            <p class="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Collected (excl. Mission)</p>
            <CurrencyDisplay :value="totals.spendable" />
          </div>
          <div v-if="totals.mission > 0" :title="MISSION_HINT" class="cursor-help">
            <p class="text-[11px] font-semibold text-amber-600 uppercase tracking-wider flex items-center gap-1">
              To Mission Funds
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z" />
              </svg>
            </p>
            <CurrencyDisplay :value="totals.mission" />
          </div>
          <div>
            <p class="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Expenses</p>
            <CurrencyDisplay :value="totals.expenses" />
          </div>
          <div class="ml-auto text-right">
            <p class="text-[11px] font-semibold uppercase tracking-wider" :class="totals.remaining < 0 ? 'text-rose-600' : 'text-gray-500'">
              Remaining
            </p>
            <CurrencyDisplay :value="totals.remaining" size="lg" colored />
          </div>
        </div>
        <p v-if="totals.remaining < 0" class="mt-2 text-xs text-rose-600">
          Your department has spent more than it collected (excluding mission entries).
        </p>
      </div>
    </template>

    <InviteDonationModal
      v-if="doc"
      :is-open="showInvite"
      :department="doc.department"
      :year="doc.year"
      @close="showInvite = false"
      @invited="onInvited"
    />
    <PurposeModal :is-open="showPurposes" @close="showPurposes = false" />

    <!-- Row delete confirmation -->
    <Teleport to="body">
      <div v-if="pendingDelete !== null" class="fixed inset-0 z-[60] flex items-end sm:items-center justify-center p-4">
        <div class="absolute inset-0 bg-gray-900/40 backdrop-blur-sm" @click="pendingDelete = null" />
        <div class="relative bg-white rounded-2xl shadow-2xl w-full max-w-sm p-5 anim-pop">
          <h3 class="text-base font-bold text-gray-900">Remove this entry?</h3>
          <p class="text-xs text-gray-500 mt-1">This only takes effect once you save.</p>
          <div v-if="rows[pendingDelete]" class="mt-3 p-3 rounded-xl bg-gray-50 border border-gray-100 text-sm">
            <div class="flex items-center justify-between gap-3">
              <div class="min-w-0">
                <p class="font-semibold text-gray-900 truncate">
                  {{ rows[pendingDelete].purpose || "No purpose" }}
                  <span class="text-gray-400 font-normal">· {{ rows[pendingDelete].donation_type }}</span>
                </p>
                <p class="text-xs text-gray-400 mt-0.5 truncate">
                  {{ rows[pendingDelete].date_donated || "No date" }}
                  <template v-if="rows[pendingDelete].description"> · {{ rows[pendingDelete].description }}</template>
                </p>
              </div>
              <CurrencyDisplay :value="Number(rows[pendingDelete].amount_donated) || 0" weight="bold" />
            </div>
          </div>
          <div class="mt-4 flex justify-end gap-2">
            <AppButton type="button" variant="secondary" size="sm" @click="pendingDelete = null">Cancel</AppButton>
            <AppButton type="button" variant="danger" size="sm" @click="removeRow(pendingDelete)">Remove entry</AppButton>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
