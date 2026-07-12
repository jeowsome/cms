<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useQuery } from "@pinia/colada";
import { call } from "@/composables/useFrappeApi";
import PageHeader from "@/components/PageHeader.vue";
import DataTable from "@/components/DataTable.vue";
import CurrencyDisplay from "@/components/CurrencyDisplay.vue";
import AppButton from "@/components/AppButton.vue";

const router = useRouter();
const deleteError = ref("");
const deletingName = ref("");

const {
  data: templates,
  isPending: loading,
  error,
  refetch,
} = useQuery({
  key: ["disbursement-templates"],
  query: () => call("church_management.api.disbursement.get_templates"),
});

const columns = [
  { key: "name", label: "Template" },
  { key: "company", label: "Company", hideOnMobile: true },
  { key: "weekly", label: "Weekly Items", align: "right", hideOnMobile: true },
  { key: "monthly", label: "Monthly Items", align: "right", hideOnMobile: true },
  { key: "actions", label: "", align: "right" },
];

function goTo(row) {
  router.push({ name: "TemplateForm", params: { name: row.name } });
}

async function removeTemplate(row, ev) {
  ev?.stopPropagation();
  if (!confirm(`Delete template "${row.name}"? This cannot be undone.`)) return;
  deleteError.value = "";
  deletingName.value = row.name;
  try {
    await call("church_management.api.disbursement.delete_template", { name: row.name });
    refetch();
  } catch (err) {
    deleteError.value = err.messages?.[0] || err.message || "Failed to delete template";
  } finally {
    deletingName.value = "";
  }
}
</script>

<template>
  <div class="px-4 sm:px-6 py-4 sm:py-6 max-w-5xl mx-auto w-full">
    <PageHeader title="Disbursement Templates" subtitle="Recurring allowance & expense patterns">
      <template #actions>
        <AppButton size="sm" @click="router.push({ name: 'TemplateForm', params: { name: 'new' } })">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          <span class="hidden sm:inline">New Template</span>
          <span class="sm:hidden">New</span>
        </AppButton>
      </template>
    </PageHeader>

    <div v-if="error || deleteError" class="mb-4 p-3 bg-red-50 text-red-700 rounded-xl text-sm flex items-center gap-2">
      <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
      </svg>
      {{ deleteError || error.message }}
    </div>

    <DataTable
      :columns="columns"
      :rows="templates || []"
      :loading="loading"
      row-clickable
      empty-text="No templates yet — create one to generate monthly disbursements faster"
      @row-click="goTo"
    >
      <template #cell-name="{ row }">
        <span class="font-semibold text-gray-900">{{ row.name }}</span>
      </template>
      <template #cell-company="{ row }">
        <span v-if="row.company_valid" class="text-gray-600">{{ row.company }}</span>
        <span v-else class="inline-flex items-center gap-1 text-xs font-semibold text-red-600 bg-red-50 border border-red-200 rounded-full px-2 py-0.5"
              :title="`Company '${row.company}' no longer exists — this template cannot generate`">
          <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
          </svg>
          missing company
        </span>
      </template>
      <template #cell-weekly="{ row }">
        <div class="text-right leading-tight">
          <span class="font-medium text-gray-900">{{ row.weekly_item_count }}</span>
          <div class="text-xs text-gray-400"><CurrencyDisplay :value="row.weekly_amount" size="xs" /> /wk</div>
        </div>
      </template>
      <template #cell-monthly="{ row }">
        <div class="text-right leading-tight">
          <span class="font-medium text-gray-900">{{ row.monthly_item_count }}</span>
          <div class="text-xs text-gray-400"><CurrencyDisplay :value="row.monthly_amount" size="xs" /> /mo</div>
        </div>
      </template>
      <template #cell-actions="{ row }">
        <div class="flex items-center justify-end gap-1" @click.stop>
          <button
            class="p-2 rounded-lg text-gray-400 hover:text-brand-600 hover:bg-brand-50 transition-colors"
            :aria-label="`Edit ${row.name}`"
            @click="goTo(row)"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L6.832 19.82a4.5 4.5 0 01-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 011.13-1.897L16.862 4.487z" />
            </svg>
          </button>
          <button
            class="p-2 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors disabled:opacity-40"
            :disabled="deletingName === row.name"
            :aria-label="`Delete ${row.name}`"
            @click="removeTemplate(row, $event)"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
            </svg>
          </button>
        </div>
      </template>

      <template #mobile-card="{ row }">
        <div class="flex items-center justify-between gap-3 w-full">
          <div class="min-w-0">
            <p class="font-semibold text-gray-900 text-sm truncate">{{ row.name }}</p>
            <p class="text-xs mt-0.5" :class="row.company_valid ? 'text-gray-400' : 'text-red-500 font-semibold'">
              {{ row.company_valid ? row.company : "⚠ missing company" }}
            </p>
            <p class="text-[11px] text-gray-400 mt-1">
              {{ row.weekly_item_count }} weekly · {{ row.monthly_item_count }} monthly
            </p>
          </div>
          <button
            class="p-2.5 rounded-lg text-gray-400 active:text-red-600 active:bg-red-50 shrink-0"
            :aria-label="`Delete ${row.name}`"
            @click="removeTemplate(row, $event)"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
            </svg>
          </button>
        </div>
      </template>
    </DataTable>
  </div>
</template>
