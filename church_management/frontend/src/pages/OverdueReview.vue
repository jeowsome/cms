<script setup>
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { useQuery } from "@pinia/colada";
import { call } from "@/composables/useFrappeApi";
import PageHeader from "@/components/PageHeader.vue";
import AppButton from "@/components/AppButton.vue";
import CurrencyDisplay from "@/components/CurrencyDisplay.vue";

const router = useRouter();
const year = ref(new Date().getFullYear());
const { data: lines, isPending, error, refetch } = useQuery({
  key: () => ["overdue-lines", year.value],
  query: () => call("church_management.api.disbursement.get_overdue_lines", { year: year.value }),
});
const total = computed(() => (lines.value || []).reduce((s, l) => s + (l.amount || 0), 0));

const voiding = ref(null);
const reason = ref("Discontinued — will not be paid");
const busy = ref(false);

async function confirmVoid() {
  if ((reason.value || "").trim().length < 5) return alert("Please type a reason.");
  busy.value = true;
  try {
    const res = await call("church_management.api.disbursement.void_line", {
      disbursement_name: voiding.value.disbursement, child_name: voiding.value.row_name, reason: reason.value,
    });
    if (res?.warnings?.length) alert(res.warnings.join("\n\n"));
    voiding.value = null;
    refetch();
  } catch (e) {
    alert(e.messages?.[0] || e.message);
  } finally {
    busy.value = false;
  }
}
function openMonth(l) {
  router.push({ name: "DisbursementForm", params: { name: l.disbursement } });
}
function ageClass(d) {
  return d > 90 ? "bg-red-100 text-red-700" : d > 30 ? "bg-amber-100 text-amber-700" : "bg-gray-100 text-gray-600";
}
</script>

<template>
  <div class="px-4 sm:px-6 py-4 sm:py-6 max-w-5xl mx-auto w-full">
    <PageHeader title="Overdue review" subtitle="Unclaimed lines past their due date, oldest first. Pay them, or void the ones that will never be paid.">
      <template #actions>
        <select v-model.number="year" class="cm-field cm-select w-28">
          <option v-for="y in [year - 1, year, year + 1]" :key="y" :value="y">{{ y }}</option>
        </select>
      </template>
    </PageHeader>

    <div v-if="isPending" class="h-64 bg-white rounded-2xl border border-gray-100 animate-pulse" />
    <div v-else-if="error" class="p-4 bg-red-50 text-red-700 rounded-xl text-sm">{{ error.message }}</div>
    <template v-else>
      <p class="text-sm text-gray-600 mb-3">{{ lines?.length || 0 }} overdue lines · <CurrencyDisplay :value="total" weight="bold" /></p>
      <div v-if="!lines?.length" class="py-10 text-center text-sm text-gray-400 bg-white rounded-2xl border border-dashed border-gray-200">Nothing overdue. 🎉</div>
      <div v-else class="bg-white rounded-2xl border border-gray-100 overflow-x-auto">
        <table class="min-w-full text-sm">
          <thead>
            <tr class="text-left text-[10px] text-gray-400 font-black uppercase tracking-widest border-b border-gray-100 bg-gray-50/50">
              <th class="py-3 pl-4 pr-2">Overdue</th><th class="py-3 pr-2">Month</th><th class="py-3 pr-2">Line</th>
              <th class="py-3 pr-2">Purpose · Department</th><th class="py-3 pr-2 text-right">Amount</th><th class="py-3 pr-4"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50">
            <tr v-for="l in lines" :key="l.row_name" class="align-top">
              <td class="py-2.5 pl-4 pr-2"><span class="px-2 py-0.5 rounded-full text-[11px] font-bold" :class="ageClass(l.days_overdue)">{{ l.days_overdue }} days</span></td>
              <td class="py-2.5 pr-2 whitespace-nowrap">{{ l.month }}<span class="block text-[11px] text-gray-400">{{ l.section }}</span></td>
              <td class="py-2.5 pr-2 font-semibold text-gray-900">{{ l.label }}<span class="block text-[11px] text-gray-400 font-normal">{{ l.fund }} · due {{ l.due }}</span></td>
              <td class="py-2.5 pr-2 text-gray-600">{{ l.purpose }}<span class="block text-[11px] text-gray-400">{{ l.department }}</span></td>
              <td class="py-2.5 pr-2 text-right"><CurrencyDisplay :value="l.amount" /></td>
              <td class="py-2.5 pr-4 whitespace-nowrap text-right space-x-1">
                <AppButton size="sm" variant="secondary" @click="openMonth(l)">Open to pay</AppButton>
                <AppButton size="sm" variant="outline" @click="voiding = l; reason = 'Discontinued — will not be paid'">Void</AppButton>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <Teleport to="body">
      <div v-if="voiding" class="fixed inset-0 z-[70] flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-black/40" @click="voiding = null" />
        <div class="relative bg-white rounded-2xl shadow-xl w-full max-w-sm p-5 space-y-3">
          <h3 class="text-base font-bold">Void “{{ voiding.label }}”?</h3>
          <p class="text-xs text-gray-600">{{ voiding.month }} {{ voiding.year }} · <CurrencyDisplay :value="voiding.amount" size="xs" />. It stays on the month, greyed out, and is left out of pending, totals and every report.</p>
          <textarea v-model="reason" rows="2" class="cm-field resize-none" />
          <div class="flex gap-2">
            <AppButton variant="secondary" class="flex-1" @click="voiding = null">Cancel</AppButton>
            <AppButton variant="danger" class="flex-1" :loading="busy" @click="confirmVoid">Void line</AppButton>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
