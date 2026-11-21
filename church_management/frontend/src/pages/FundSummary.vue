<script setup>
import { computed, ref, watch } from "vue";
import { useQuery } from "@pinia/colada";
import { call } from "@/composables/useFrappeApi";
import PageHeader from "@/components/PageHeader.vue";
import AppButton from "@/components/AppButton.vue";
import CurrencyDisplay from "@/components/CurrencyDisplay.vue";

const today = new Date();
const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const fromDate = ref(`${today.getFullYear()}-01-01`);
const toDate = ref(iso(new Date(today.getFullYear(), today.getMonth() + 1, 0)));
const applied = ref({ from: fromDate.value, to: toDate.value });

const { data: fs, isPending, error, refetch } = useQuery({
  key: () => ["fund-summary", applied.value.from, applied.value.to],
  query: () => call("church_management.api.finance.get_fund_summary", { from_date: applied.value.from, to_date: applied.value.to }),
});

function apply() {
  applied.value = { from: fromDate.value, to: toDate.value };
}

const ORDER = ["Mission", "Benevolence", "White Gift", "General"];
const fundRows = computed(() => (fs.value?.funds || []).slice().sort((a, b) => ORDER.indexOf(a.fund) - ORDER.indexOf(b.fund)));

// Comments per fund, saved with the period
const comments = ref({});
const saving = ref({});
const savedAt = ref({});
watch(fs, (v) => {
  if (!v) return;
  const c = {};
  for (const f of ORDER) c[f] = v.comments?.[f]?.comments || "";
  comments.value = c;
  savedAt.value = {};
});
async function saveComment(fund) {
  saving.value = { ...saving.value, [fund]: true };
  try {
    await call("church_management.api.finance.save_fund_comment", {
      from_date: fs.value.from_date, to_date: fs.value.to_date, fund, comments: comments.value[fund],
    });
    savedAt.value = { ...savedAt.value, [fund]: new Date().toLocaleTimeString() };
  } catch (e) {
    alert(e.messages?.[0] || e.message);
  } finally {
    saving.value = { ...saving.value, [fund]: false };
  }
}
</script>

<template>
  <div class="px-4 sm:px-6 py-4 sm:py-6 max-w-5xl mx-auto w-full">
    <PageHeader title="Fund Summary" :subtitle="fs ? `${fs.period} · ${fs.months} month${fs.months === 1 ? '' : 's'}` : ''" />

    <div class="flex flex-wrap items-end gap-3 mb-5 bg-white rounded-2xl border border-gray-100 p-4">
      <div>
        <label class="block text-[11px] font-semibold text-gray-500 uppercase tracking-wide mb-1">From</label>
        <input v-model="fromDate" type="date" class="cm-field" />
      </div>
      <div>
        <label class="block text-[11px] font-semibold text-gray-500 uppercase tracking-wide mb-1">To</label>
        <input v-model="toDate" type="date" class="cm-field" />
      </div>
      <AppButton @click="apply">Show</AppButton>
      <p class="text-xs text-gray-500 basis-full">
        Collections = posted collections (cash + cashless together; White Gift counts all years). Disbursements = claimed + unclaimed lines of the months in range; voided lines are left out.
      </p>
    </div>

    <div v-if="isPending" class="h-64 bg-white rounded-2xl border border-gray-100 animate-pulse" />
    <div v-else-if="error" class="p-4 bg-red-50 text-red-700 rounded-xl text-sm">{{ error.message }}</div>

    <template v-else-if="fs">
      <!-- Totals -->
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-5">
        <div class="bg-white rounded-2xl border border-gray-100 p-4">
          <p class="text-[11px] text-emerald-600 uppercase tracking-wide font-semibold">Total collections</p>
          <CurrencyDisplay :value="fs.collections.total" size="lg" />
          <dl class="mt-2 space-y-1 text-sm">
            <div v-for="f in ORDER" :key="f" class="flex justify-between"><dt class="text-gray-500">{{ f }}</dt><dd><CurrencyDisplay :value="fs.collections.by_fund[f]" /></dd></div>
          </dl>
        </div>
        <div class="bg-white rounded-2xl border border-gray-100 p-4">
          <p class="text-[11px] text-rose-600 uppercase tracking-wide font-semibold">Total disbursements</p>
          <CurrencyDisplay :value="fs.disbursements.total" size="lg" />
          <dl class="mt-2 space-y-1 text-sm">
            <div v-for="f in ORDER" :key="f" class="flex justify-between"><dt class="text-gray-500">{{ f }}</dt><dd><CurrencyDisplay :value="fs.disbursements.by_fund[f]" /></dd></div>
          </dl>
        </div>
        <div class="bg-white rounded-2xl border border-gray-100 p-4">
          <p class="text-[11px] uppercase tracking-wide font-semibold" :class="fs.surplus >= 0 ? 'text-emerald-600' : 'text-rose-600'">{{ fs.surplus >= 0 ? "Surplus" : "Deficit" }}</p>
          <CurrencyDisplay :value="fs.surplus" size="lg" colored />
          <p class="mt-2 text-xs text-gray-500">Total collections − total disbursements.</p>
        </div>
      </div>

      <!-- Per fund -->
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-5">
        <div v-for="f in fundRows" :key="f.fund" class="bg-white rounded-2xl border border-gray-100 p-4">
          <div class="flex items-center justify-between mb-2">
            <h3 class="text-sm font-bold text-gray-900">{{ f.fund }} Fund</h3>
            <span class="text-[10px] text-gray-400 uppercase tracking-wider">Total · per month</span>
          </div>
          <table class="w-full text-sm">
            <tbody>
              <tr><td class="text-gray-500 py-0.5">Collections</td><td class="text-right"><CurrencyDisplay :value="f.collections" /></td><td class="text-right text-gray-400"><CurrencyDisplay :value="f.avg_collections" size="xs" /></td></tr>
              <tr><td class="text-gray-500 py-0.5">Disbursements</td><td class="text-right"><CurrencyDisplay :value="f.disbursements" /></td><td class="text-right text-gray-400"><CurrencyDisplay :value="f.avg_disbursements" size="xs" /></td></tr>
              <tr class="border-t border-gray-100"><td class="font-semibold py-1">Balance</td><td class="text-right"><CurrencyDisplay :value="f.balance" weight="bold" colored /></td><td class="text-right"><CurrencyDisplay :value="f.avg_balance" size="xs" colored /></td></tr>
            </tbody>
          </table>
          <dl class="mt-2 pt-2 border-t border-dashed border-gray-100 text-xs space-y-0.5 text-gray-500">
            <div class="flex justify-between"><dt>Paid out (church money)</dt><dd><CurrencyDisplay :value="f.paid_out" size="xs" /></dd></div>
            <div class="flex justify-between"><dt>Pending claims</dt><dd><CurrencyDisplay :value="f.pending" size="xs" /></dd></div>
            <div class="flex justify-between"><dt>Owed to creditors</dt><dd><CurrencyDisplay :value="f.owed" size="xs" /></dd></div>
            <div class="flex justify-between font-semibold text-gray-700"><dt>After pending claims &amp; payables</dt><dd><CurrencyDisplay :value="f.after_pending_and_payables" size="xs" colored /></dd></div>
          </dl>
          <div class="mt-3">
            <label class="block text-[11px] font-semibold text-gray-500 uppercase tracking-wide mb-1">Comments for {{ f.fund }}</label>
            <textarea v-model="comments[f.fund]" rows="3" class="cm-field resize-y text-sm" placeholder="Notes for this period…" />
            <div class="flex items-center justify-end gap-2 mt-1">
              <span v-if="savedAt[f.fund]" class="text-[11px] text-emerald-600">Saved {{ savedAt[f.fund] }}</span>
              <AppButton size="sm" variant="outline" :loading="saving[f.fund]" @click="saveComment(f.fund)">Save comments</AppButton>
            </div>
          </div>
        </div>
      </div>

      <!-- General by purpose, by purpose, by department -->
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div class="bg-white rounded-2xl border border-gray-100 p-4">
          <h3 class="text-sm font-bold text-gray-900 mb-2">Disbursement per purpose</h3>
          <div v-for="(v, p) in fs.by_purpose" :key="p" class="flex justify-between text-sm py-0.5">
            <span class="text-gray-600">{{ p }}</span><CurrencyDisplay :value="v" />
          </div>
          <h4 class="text-xs font-bold text-gray-500 uppercase tracking-wide mt-4 mb-1">General fund by purpose</h4>
          <div v-for="(v, p) in fs.disbursements.general_by_purpose" :key="'g' + p" class="flex justify-between text-sm py-0.5">
            <span class="text-gray-600">{{ p }}</span><CurrencyDisplay :value="v" />
          </div>
        </div>
        <div class="bg-white rounded-2xl border border-gray-100 p-4">
          <h3 class="text-sm font-bold text-gray-900 mb-2">Disbursement per department</h3>
          <div v-for="d in fs.by_department" :key="d.department" class="mb-2">
            <div class="flex justify-between text-sm font-semibold"><span>{{ d.department }}</span><CurrencyDisplay :value="d.total" weight="bold" /></div>
            <div v-for="(v, p) in d.purposes" :key="p" class="flex justify-between text-xs text-gray-500 pl-3"><span>{{ p }}</span><CurrencyDisplay :value="v" size="xs" /></div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
