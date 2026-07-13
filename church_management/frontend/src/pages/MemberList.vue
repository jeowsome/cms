<script setup>
import { computed, ref } from "vue";
import { useQuery, useQueryCache } from "@pinia/colada";
import { call } from "@/composables/useFrappeApi";
import PageHeader from "@/components/PageHeader.vue";
import DataTable from "@/components/DataTable.vue";
import AppButton from "@/components/AppButton.vue";
import MemberModal from "@/components/MemberModal.vue";

const queryCache = useQueryCache();
const search = ref("");
const showModal = ref(false);
const editing = ref(null); // null → create

const {
  data: members,
  isPending: loading,
  error,
  refetch,
} = useQuery({
  key: ["church-members-full"],
  query: () => call("church_management.api.member.get_list"),
});

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase();
  const list = members.value || [];
  if (!q) return list;
  return list.filter((m) =>
    [m.envelope_number, m.firstname, m.lastname, m.contact_number, m.email_address]
      .some((v) => String(v || "").toLowerCase().includes(q))
  );
});

const columns = [
  { key: "envelope_number", label: "Envelope" },
  { key: "member", label: "Name" },
  { key: "contact_number", label: "Contact", hideOnMobile: true },
  { key: "email_address", label: "Email", hideOnMobile: true },
  { key: "birthday", label: "Birthday", hideOnMobile: true },
  { key: "member_since", label: "Since", hideOnMobile: true },
];

function fmtBirthday(iso) {
  if (!iso) return "—";
  const d = new Date(iso + "T00:00:00");
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function openCreate() {
  editing.value = null;
  showModal.value = true;
}

function openEdit(row) {
  editing.value = { ...row };
  showModal.value = true;
}

function onSaved() {
  refetch();
  // Keep the collection-entry envelope cache in sync too
  queryCache.invalidateQueries({ key: ["church-members"] });
}
</script>

<template>
  <div class="px-4 sm:px-6 py-4 sm:py-6 max-w-5xl mx-auto w-full">
    <PageHeader title="Church Members" :subtitle="`${(members || []).length} members · envelope numbers resolve collection entries`">
      <template #actions>
        <AppButton size="sm" @click="openCreate">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          <span class="hidden sm:inline">New Member</span>
          <span class="sm:hidden">New</span>
        </AppButton>
      </template>
    </PageHeader>

    <!-- Search -->
    <div class="relative mb-4 max-w-md">
      <svg class="w-4 h-4 text-gray-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
      </svg>
      <input
        v-model="search"
        type="search"
        placeholder="Search by envelope, name, contact, email…"
        class="cm-field !pl-10"
      />
    </div>

    <div v-if="error" class="mb-4 p-3 bg-red-50 text-red-700 rounded-xl text-sm">{{ error.message }}</div>

    <DataTable
      :columns="columns"
      :rows="filtered"
      :loading="loading"
      row-clickable
      :empty-text="search ? 'No members match your search' : 'No members yet'"
      @row-click="openEdit"
    >
      <template #cell-envelope_number="{ value }">
        <span class="inline-flex items-center justify-center min-w-[2.5rem] px-2 py-0.5 rounded-lg bg-brand-50 text-brand-700 font-bold tabular text-xs">
          {{ value || "—" }}
        </span>
      </template>
      <template #cell-member="{ row }">
        <span class="font-semibold text-gray-900">{{ row.firstname }} {{ row.lastname }}</span>
      </template>
      <template #cell-contact_number="{ value }">
        <span class="tabular">{{ value || "—" }}</span>
      </template>
      <template #cell-email_address="{ value }">
        <span class="text-gray-500">{{ value || "—" }}</span>
      </template>
      <template #cell-birthday="{ value }">
        <span class="text-gray-500">{{ fmtBirthday(value) }}</span>
      </template>
      <template #cell-member_since="{ value }">
        <span class="text-gray-500">{{ value || "—" }}</span>
      </template>

      <!-- Mobile card -->
      <template #mobile-card="{ row }">
        <div class="flex items-center gap-3 w-full">
          <span class="inline-flex items-center justify-center min-w-[2.75rem] px-2 py-1.5 rounded-xl bg-brand-50 text-brand-700 font-bold tabular text-sm shrink-0">
            {{ row.envelope_number || "—" }}
          </span>
          <div class="min-w-0 flex-1">
            <p class="font-semibold text-gray-900 text-sm truncate">{{ row.firstname }} {{ row.lastname }}</p>
            <p class="text-xs text-gray-400 truncate mt-0.5">
              {{ row.contact_number || row.email_address || "No contact info" }}
            </p>
          </div>
          <svg class="w-4 h-4 text-gray-300 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
          </svg>
        </div>
      </template>
    </DataTable>

    <MemberModal
      :is-open="showModal"
      :member="editing"
      @close="showModal = false"
      @saved="onSaved"
    />
  </div>
</template>
