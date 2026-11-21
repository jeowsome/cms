<script setup>
import { ref } from "vue";
import { useQuery } from "@pinia/colada";
import { call } from "@/composables/useFrappeApi";
import PageHeader from "@/components/PageHeader.vue";
import AppButton from "@/components/AppButton.vue";
import CurrencyDisplay from "@/components/CurrencyDisplay.vue";

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const f = ref({ from_date: "", to_date: "", user: "", action: "", month: "", year: new Date().getFullYear(), text: "" });
const applied = ref({ ...f.value });

const { data: actions } = useQuery({ key: ["audit-actions"], query: () => call("church_management.api.finance.get_audit_actions") });
const { data: rows, isPending, error } = useQuery({
  key: () => ["audit-log", JSON.stringify(applied.value)],
  query: () => call("church_management.api.finance.search_audit_log", { ...applied.value, limit: 1000 }),
});
function search() {
  applied.value = { ...f.value };
}
function fmtWhen(ts) {
  return ts ? new Date(ts.replace(" ", "T")).toLocaleString("en-PH", { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" }) : "";
}
</script>

<template>
  <div class="px-4 sm:px-6 py-4 sm:py-6 max-w-6xl mx-auto w-full">
    <PageHeader title="Disbursement audit log" subtitle="Every claim, correction, void, payable and reimbursement. Entries can never be edited or deleted." />

    <div class="grid grid-cols-2 sm:grid-cols-7 gap-2 mb-4 bg-white rounded-2xl border border-gray-100 p-4 items-end">
      <div><label class="block text-[11px] font-semibold text-gray-500 uppercase mb-1">From</label><input v-model="f.from_date" type="date" class="cm-field" /></div>
      <div><label class="block text-[11px] font-semibold text-gray-500 uppercase mb-1">To</label><input v-model="f.to_date" type="date" class="cm-field" /></div>
      <div><label class="block text-[11px] font-semibold text-gray-500 uppercase mb-1">Action</label>
        <select v-model="f.action" class="cm-field cm-select"><option value="">Any</option><option v-for="a in actions || []" :key="a">{{ a }}</option></select></div>
      <div><label class="block text-[11px] font-semibold text-gray-500 uppercase mb-1">Month</label>
        <select v-model="f.month" class="cm-field cm-select"><option value="">Any</option><option v-for="m in MONTHS" :key="m">{{ m }}</option></select></div>
      <div><label class="block text-[11px] font-semibold text-gray-500 uppercase mb-1">Year</label><input v-model.number="f.year" type="number" class="cm-field" /></div>
      <div><label class="block text-[11px] font-semibold text-gray-500 uppercase mb-1">User (email)</label><input v-model="f.user" class="cm-field" /></div>
      <div class="col-span-2 sm:col-span-1 flex gap-2">
        <input v-model="f.text" class="cm-field" placeholder="Search…" @keyup.enter="search" />
        <AppButton @click="search">Go</AppButton>
      </div>
    </div>

    <div v-if="isPending" class="h-64 bg-white rounded-2xl border border-gray-100 animate-pulse" />
    <div v-else-if="error" class="p-4 bg-red-50 text-red-700 rounded-xl text-sm">{{ error.message }}</div>
    <div v-else class="bg-white rounded-2xl border border-gray-100 overflow-x-auto">
      <p class="px-4 pt-3 text-xs text-gray-500">{{ rows?.length || 0 }} entries{{ rows?.length === 1000 ? " (first 1000 — narrow the search)" : "" }}</p>
      <table class="min-w-full text-xs">
        <thead>
          <tr class="text-left text-[10px] text-gray-400 uppercase tracking-wider border-b border-gray-100">
            <th class="py-2 pl-4 pr-2">When</th><th class="py-2 pr-2">Who</th><th class="py-2 pr-2">Action</th><th class="py-2 pr-2">Month</th>
            <th class="py-2 pr-2">Line</th><th class="py-2 pr-2">Change</th><th class="py-2 pr-4">Reason</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-50">
          <tr v-for="r in rows || []" :key="r.name" class="align-top">
            <td class="py-1.5 pl-4 pr-2 whitespace-nowrap text-gray-500">{{ fmtWhen(r.timestamp) }}</td>
            <td class="py-1.5 pr-2 whitespace-nowrap">{{ r.user_name }}</td>
            <td class="py-1.5 pr-2 whitespace-nowrap font-semibold">{{ r.action }}</td>
            <td class="py-1.5 pr-2 whitespace-nowrap">
              <RouterLink v-if="r.disbursement && r.disbursement.includes('-')" :to="{ name: 'DisbursementForm', params: { name: r.disbursement } }" class="text-brand-600 hover:underline">{{ r.disbursement }}</RouterLink>
              <span v-else>{{ r.reference_name }}</span>
            </td>
            <td class="py-1.5 pr-2">{{ r.line_label }}<span class="block text-gray-400">{{ r.section }} · <CurrencyDisplay v-if="r.amount != null" :value="r.amount" size="xs" /></span></td>
            <td class="py-1.5 pr-2 whitespace-pre-line text-gray-600">{{ r.summary }}</td>
            <td class="py-1.5 pr-4 italic text-gray-500">{{ r.reason }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
