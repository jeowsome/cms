<script setup>
import { computed, ref, watch } from "vue";
import { useQuery } from "@pinia/colada";
import { call } from "@/composables/useFrappeApi";
import PageHeader from "@/components/PageHeader.vue";
import AppButton from "@/components/AppButton.vue";
import CurrencyDisplay from "@/components/CurrencyDisplay.vue";

const API = "church_management.api.finance.";
const todayIso = new Date().toISOString().slice(0, 10);

const { data: owe, isPending, error, refetch: refetchOwe } = useQuery({
  key: ["who-we-owe"],
  query: () => call(API + "who_we_owe"),
});
const { data: creditors, refetch: refetchCreditors } = useQuery({
  key: ["creditors-all"],
  query: () => call(API + "get_creditors"),
});
const { data: accounts } = useQuery({ key: ["accounts"], query: () => call("church_management.api.disbursement.get_source_accounts") });
const { data: purposes } = useQuery({ key: ["purposes"], query: () => call("church_management.api.disbursement.get_purposes") });
const { data: departments } = useQuery({ key: ["departments"], query: () => call("church_management.api.disbursement.get_departments") });

const selected = ref("");
watch(creditors, (list) => {
  if (!selected.value && list?.length) selected.value = list[0].name;
});
const { data: history, refetch: refetchHistory } = useQuery({
  key: () => ["creditor-history", selected.value],
  query: () => call(API + "creditor_history", { creditor: selected.value }),
  enabled: () => !!selected.value,
});
function refreshAll() {
  refetchOwe();
  refetchHistory();
}

const FUND_OF = (acc) => {
  const s = (acc || "").toLowerCase();
  return s.includes("white gift") ? "White Gift" : s.includes("mission") ? "Mission" : s.includes("benevolence") ? "Benevolence" : "General";
};

// ---------- reimburse
const reimb = ref(null);
async function openReimburse(creditor) {
  const items = await call(API + "get_open_payables", { creditor });
  reimb.value = {
    creditor, posting_date: todayIso, source_account: "", received_by: "", reference: "", remarks: "",
    items: items.map((i) => ({ ...i, pay: 0 })),
  };
}
const reimbFund = computed(() => (reimb.value?.source_account ? FUND_OF(reimb.value.source_account) : null));
const reimbTotal = computed(() => (reimb.value?.items || []).reduce((s, i) => s + (Number(i.pay) || 0), 0));
const busy = ref(false);
async function submitReimburse() {
  const r = reimb.value;
  const allocations = r.items.filter((i) => Number(i.pay) > 0).map((i) => ({ payable: i.name, amount: Number(i.pay) }));
  if (!r.source_account || !r.received_by || !allocations.length) return alert("Choose the account, who received it, and at least one amount.");
  busy.value = true;
  try {
    const name = await call(API + "create_reimbursement", {
      creditor: r.creditor, posting_date: r.posting_date, source_account: r.source_account,
      received_by: r.received_by, reference: r.reference, remarks: r.remarks, allocations: JSON.stringify(allocations),
    });
    alert(`Reimbursement ${name} recorded.`);
    reimb.value = null;
    refreshAll();
  } catch (e) {
    alert(e.messages?.[0] || e.message);
  } finally {
    busy.value = false;
  }
}

// ---------- direct payable
const direct = ref(null);
function openDirect() {
  direct.value = { creditor: selected.value || "", posting_date: todayIso, amount: null, fund: "General", purpose: "", department: "", description: "", reference: "" };
}
async function submitDirect() {
  const d = direct.value;
  if (!d.creditor || !d.amount || !d.purpose || !d.department || !d.description) return alert("Fill in creditor, amount, purpose, department and description.");
  busy.value = true;
  try {
    await call(API + "create_direct_payable", { ...d });
    direct.value = null;
    refreshAll();
  } catch (e) {
    alert(e.messages?.[0] || e.message);
  } finally {
    busy.value = false;
  }
}

// ---------- cancel a reimbursement (to correct it)
async function cancelReimbursement(name) {
  const reason = prompt(`Why is ${name} being cancelled? (It is kept in the history.)`);
  if (!reason) return;
  try {
    await call(API + "cancel_reimbursement", { name, reason });
    refreshAll();
  } catch (e) {
    alert(e.messages?.[0] || e.message);
  }
}

// ---------- new creditor
async function addCreditor() {
  const name = prompt("Creditor name (e.g. a school or organisation that paid for the church):");
  if (!name) return;
  try {
    selected.value = await call(API + "save_creditor", { creditor_name: name });
    refetchCreditors();
  } catch (e) {
    alert(e.messages?.[0] || e.message);
  }
}
function ageClass(d) {
  return d > 90 ? "bg-red-100 text-red-700" : d > 30 ? "bg-amber-100 text-amber-700" : "bg-gray-100 text-gray-600";
}
</script>

<template>
  <div class="px-4 sm:px-6 py-4 sm:py-6 max-w-5xl mx-auto w-full">
    <PageHeader title="Creditors" subtitle="Expenses others paid for the church, and what we still owe them.">
      <template #actions>
        <div class="flex gap-2">
          <AppButton size="sm" variant="secondary" @click="addCreditor">New creditor</AppButton>
          <AppButton size="sm" @click="openDirect">Record expense they paid</AppButton>
        </div>
      </template>
    </PageHeader>

    <div v-if="isPending" class="h-40 bg-white rounded-2xl border border-gray-100 animate-pulse" />
    <div v-else-if="error" class="p-4 bg-red-50 text-red-700 rounded-xl text-sm">{{ error.message }}</div>
    <template v-else>
      <!-- Who we owe -->
      <div class="bg-white rounded-2xl border border-gray-100 p-4 mb-5">
        <div class="flex items-baseline justify-between mb-3">
          <h3 class="text-sm font-bold text-gray-900">Who we owe</h3>
          <span class="text-sm">Total <CurrencyDisplay :value="owe?.total || 0" weight="bold" /></span>
        </div>
        <p v-if="!owe?.creditors?.length" class="text-sm text-gray-400">We owe nobody right now.</p>
        <div v-for="c in owe?.creditors || []" :key="c.creditor" class="mb-4 last:mb-0">
          <div class="flex items-center justify-between gap-2">
            <p class="font-semibold text-gray-900">{{ c.creditor }}</p>
            <div class="flex items-center gap-2">
              <CurrencyDisplay :value="c.outstanding" weight="bold" />
              <AppButton size="sm" @click="openReimburse(c.creditor)">Reimburse</AppButton>
            </div>
          </div>
          <table class="w-full text-xs mt-1.5">
            <tbody class="divide-y divide-gray-50">
              <tr v-for="i in c.items" :key="i.name">
                <td class="py-1.5 pr-2"><span class="px-1.5 py-0.5 rounded-full font-bold" :class="ageClass(i.age_days)">{{ i.age_days }}d</span></td>
                <td class="py-1.5 pr-2 text-gray-700">{{ i.description }}<span class="block text-gray-400">{{ i.posting_date }} · {{ i.fund }} · {{ i.purpose }}{{ i.disbursement ? ' · ' + i.disbursement : '' }}</span></td>
                <td class="py-1.5 pr-2 text-right text-gray-400">of <CurrencyDisplay :value="i.amount" size="xs" /></td>
                <td class="py-1.5 text-right"><CurrencyDisplay :value="i.outstanding" size="xs" weight="bold" /></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- History -->
      <div class="bg-white rounded-2xl border border-gray-100 p-4">
        <div class="flex items-center justify-between gap-2 mb-3">
          <h3 class="text-sm font-bold text-gray-900">History</h3>
          <select v-model="selected" class="cm-field cm-select max-w-xs">
            <option v-for="c in creditors || []" :key="c.name" :value="c.name">{{ c.name }}</option>
          </select>
        </div>
        <p v-if="!history?.rows?.length" class="text-sm text-gray-400">Nothing recorded for this creditor yet.</p>
        <table v-else class="w-full text-xs">
          <thead>
            <tr class="text-left text-[10px] text-gray-400 uppercase tracking-wider border-b border-gray-100">
              <th class="py-2 pr-2">Date</th><th class="py-2 pr-2">What</th><th class="py-2 pr-2 text-right">Paid for us</th>
              <th class="py-2 pr-2 text-right">We repaid</th><th class="py-2 text-right">Balance</th><th />
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50">
            <tr v-for="h in history.rows" :key="h.document">
              <td class="py-1.5 pr-2 whitespace-nowrap">{{ h.date }}</td>
              <td class="py-1.5 pr-2">{{ h.description }}<span class="block text-gray-400">{{ h.document }} · {{ h.fund }}</span></td>
              <td class="py-1.5 pr-2 text-right"><CurrencyDisplay v-if="h.increase" :value="h.increase" size="xs" /></td>
              <td class="py-1.5 pr-2 text-right"><CurrencyDisplay v-if="h.decrease" :value="h.decrease" size="xs" /></td>
              <td class="py-1.5 text-right"><CurrencyDisplay :value="h.balance" size="xs" weight="bold" /></td>
              <td class="py-1.5 pl-2 text-right">
                <button v-if="h.type === 'We repaid'" class="text-[10px] font-bold text-red-600 uppercase" @click="cancelReimbursement(h.document)">Cancel</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <!-- Reimburse modal -->
    <Teleport to="body">
      <div v-if="reimb" class="fixed inset-0 z-[70] flex items-end sm:items-center justify-center sm:p-4">
        <div class="absolute inset-0 bg-black/40" @click="reimb = null" />
        <div class="relative bg-white rounded-t-2xl sm:rounded-2xl shadow-xl w-full sm:max-w-lg max-h-[90vh] flex flex-col">
          <div class="px-5 pt-5 pb-3 border-b border-gray-100">
            <h3 class="text-base font-bold">Reimburse {{ reimb.creditor }}</h3>
            <p class="text-xs text-gray-500 mt-0.5">Church money paid back. It is deducted from the account you choose, on this date. Pay part of an item if you are paying in instalments.</p>
          </div>
          <div class="px-5 py-4 space-y-3 overflow-y-auto">
            <div class="grid grid-cols-2 gap-2">
              <div><label class="block text-[11px] font-semibold text-gray-500 uppercase mb-1">Date paid</label><input v-model="reimb.posting_date" type="date" class="cm-field" /></div>
              <div><label class="block text-[11px] font-semibold text-gray-500 uppercase mb-1">Reference / receipt</label><input v-model="reimb.reference" class="cm-field" /></div>
            </div>
            <div>
              <label class="block text-[11px] font-semibold text-gray-500 uppercase mb-1">Paid from (account) <span class="text-red-500">*</span></label>
              <select v-model="reimb.source_account" class="cm-field cm-select">
                <option value="">Select account…</option>
                <option v-for="a in accounts || []" :key="a.name" :value="a.name">{{ a.account_name || a.name }}</option>
              </select>
            </div>
            <div><label class="block text-[11px] font-semibold text-gray-500 uppercase mb-1">Received by (their side) <span class="text-red-500">*</span></label><input v-model="reimb.received_by" class="cm-field" /></div>
            <div>
              <p class="text-[11px] font-semibold text-gray-500 uppercase mb-1">Items to settle</p>
              <div v-for="i in reimb.items" :key="i.name" class="flex items-center gap-2 py-1.5 border-b border-gray-50"
                   :class="reimbFund && i.fund !== reimbFund ? 'opacity-40' : ''">
                <div class="flex-1 text-xs">
                  {{ i.description }}
                  <span class="block text-gray-400">{{ i.fund }} · owed <CurrencyDisplay :value="i.outstanding" size="xs" /></span>
                </div>
                <button class="text-[10px] font-bold text-brand-600 uppercase" :disabled="reimbFund && i.fund !== reimbFund" @click="i.pay = i.outstanding">All</button>
                <input v-model.number="i.pay" type="number" min="0" step="0.01" class="cm-field w-28 text-right tabular" :disabled="reimbFund && i.fund !== reimbFund" />
              </div>
              <p v-if="reimbFund" class="text-[11px] text-gray-500 mt-1">Only {{ reimbFund }} fund items can be paid from this account.</p>
            </div>
          </div>
          <div class="px-5 py-4 border-t border-gray-100 flex items-center gap-3">
            <span class="text-sm flex-1">Total <CurrencyDisplay :value="reimbTotal" weight="bold" /></span>
            <AppButton variant="secondary" @click="reimb = null">Cancel</AppButton>
            <AppButton :loading="busy" @click="submitReimburse">Record reimbursement</AppButton>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Direct payable modal -->
    <Teleport to="body">
      <div v-if="direct" class="fixed inset-0 z-[70] flex items-end sm:items-center justify-center sm:p-4">
        <div class="absolute inset-0 bg-black/40" @click="direct = null" />
        <div class="relative bg-white rounded-t-2xl sm:rounded-2xl shadow-xl w-full sm:max-w-md p-5 space-y-3">
          <h3 class="text-base font-bold">Expense a creditor paid for us</h3>
          <p class="text-xs text-gray-500">For something that is not on a monthly disbursement. (If it is on a month, open that line and claim it as “Paid by a creditor” instead.)</p>
          <select v-model="direct.creditor" class="cm-field cm-select">
            <option value="">Creditor…</option>
            <option v-for="c in creditors || []" :key="c.name" :value="c.name">{{ c.name }}</option>
          </select>
          <input v-model="direct.description" class="cm-field" placeholder="What was it for?" />
          <div class="grid grid-cols-2 gap-2">
            <input v-model="direct.posting_date" type="date" class="cm-field" />
            <input v-model.number="direct.amount" type="number" min="0" step="0.01" class="cm-field text-right" placeholder="Amount" />
          </div>
          <div class="grid grid-cols-3 gap-2">
            <select v-model="direct.fund" class="cm-field cm-select"><option v-for="f in ['General', 'Mission', 'Benevolence', 'White Gift']" :key="f">{{ f }}</option></select>
            <select v-model="direct.purpose" class="cm-field cm-select"><option value="">Purpose…</option><option v-for="p in purposes || []" :key="p.name" :value="p.name">{{ p.name }}</option></select>
            <select v-model="direct.department" class="cm-field cm-select"><option value="">Department…</option><option v-for="d in departments || []" :key="d.name" :value="d.name">{{ d.name }}</option></select>
          </div>
          <input v-model="direct.reference" class="cm-field" placeholder="Receipt / reference (optional)" />
          <div class="flex gap-2">
            <AppButton variant="secondary" class="flex-1" @click="direct = null">Cancel</AppButton>
            <AppButton class="flex-1" :loading="busy" @click="submitDirect">Record</AppButton>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
