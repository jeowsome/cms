<script setup>
import { computed, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useQuery, useQueryCache } from "@pinia/colada";
import { call } from "@/composables/useFrappeApi";
import PageHeader from "@/components/PageHeader.vue";
import AppButton from "@/components/AppButton.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import CurrencyDisplay from "@/components/CurrencyDisplay.vue";
import CollectionEntryTable from "@/components/CollectionEntryTable.vue";
import MathInput from "@/components/MathInput.vue";
import MemberModal from "@/components/MemberModal.vue";

const route = useRoute();
const router = useRouter();
const queryCache = useQueryCache();

const isNew = computed(() => route.params.name === "new");

// ---------------------------------------------------------------------------
// Local editable document
// ---------------------------------------------------------------------------
const form = reactive({
  name: null,
  docstatus: 0,
  date: defaultDate(),
  cost_center: "",
  attendees: null,
  benevolence_collection: 0,
  benevolence_collection_cls: 0,
  loose_collection: 0,
  loose_collection_cls: 0,
  sunday_school_collection: 0,
  journal_entry: null,
  tithes_collection: [],
  offering_collection: [],
  mission_collection: [],
  collection_tally: [],
});

const dirty = ref(false);
const saving = ref(false);
const submitting = ref(false);
const deleting = ref(false);
const errorMsg = ref("");
const savedFlash = ref(false);
const showSubmitConfirm = ref(false);
const showDeleteConfirm = ref(false);

function defaultDate() {
  const now = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}:00`;
}

const readOnly = computed(() => form.docstatus !== 0);

// ---------------------------------------------------------------------------
// Server data: detail, member cache, defaults (denominations + cost center)
// ---------------------------------------------------------------------------
const { data: detail, error: loadError, isPending: loadingDetail } = useQuery({
  key: () => ["collection", route.params.name],
  query: () => call("church_management.api.collection.get_detail", { name: route.params.name }),
  enabled: () => !isNew.value,
});

// Members are cached for 30 minutes — envelope lookups are instant and the
// list is fetched once, not per keystroke.
const { data: members } = useQuery({
  key: ["church-members"],
  query: () => call("church_management.api.collection.get_members"),
  staleTime: 30 * 60 * 1000,
});

const { data: defaults } = useQuery({
  key: ["collection-defaults"],
  query: () => call("church_management.api.collection.get_new_defaults"),
  staleTime: 30 * 60 * 1000,
});

const membersMap = computed(() => {
  const map = new Map();
  for (const m of members.value || []) {
    map.set(String(m.name).trim().toUpperCase(), m);
    if (m.envelope_number) map.set(String(m.envelope_number).trim().toUpperCase(), m);
  }
  return map;
});

function childRow(row) {
  return {
    number: row.number || "",
    first_name: row.first_name || "",
    last_name: row.last_name || "",
    amount: row.amount ?? null,
    account_type: row.account_type || "Cash",
  };
}

function hydrate(doc) {
  form.name = doc.name;
  form.docstatus = doc.docstatus;
  form.date = doc.date;
  form.cost_center = doc.cost_center || "";
  form.attendees = doc.attendees ?? null;
  form.benevolence_collection = doc.benevolence_collection || 0;
  form.benevolence_collection_cls = doc.benevolence_collection_cls || 0;
  form.loose_collection = doc.loose_collection || 0;
  form.loose_collection_cls = doc.loose_collection_cls || 0;
  form.sunday_school_collection = doc.sunday_school_collection || 0;
  form.journal_entry = doc.journal_entry || null;
  form.tithes_collection = (doc.tithes_collection || []).map(childRow);
  form.offering_collection = (doc.offering_collection || []).map(childRow);
  form.mission_collection = (doc.mission_collection || []).map(childRow);
  form.collection_tally = (doc.collection_tally || []).map((r) => ({
    denum_name: r.denum_name,
    denomination: r.denomination,
    quantity: r.quantity || 0,
    quantity_coins: r.quantity_coins || 0,
    total: r.total || 0,
  }));
  dirty.value = false;
}

watch(detail, (doc) => doc && hydrate(doc), { immediate: true });

// Prefill: default cost center + a full denomination tally for fresh/blank docs
watch(
  [defaults, () => form.collection_tally.length, readOnly],
  ([def]) => {
    if (!def) return;
    if (!form.cost_center && def.default_cost_center) form.cost_center = def.default_cost_center;
    if (!form.collection_tally.length && !readOnly.value) {
      form.collection_tally = def.denominations.map((d) => ({
        denum_name: d.name,
        denomination: d.denomination,
        quantity: 0,
        quantity_coins: 0,
        total: 0,
      }));
    }
  },
  { immediate: true }
);

// Start each entry table with one empty row so typing can begin immediately
watch(
  [isNew, members],
  () => {
    if (isNew.value && !form.tithes_collection.length) {
      for (const key of ["tithes_collection", "offering_collection", "mission_collection"]) {
        form[key].push({ number: "", first_name: "", last_name: "", amount: null, account_type: "Cash" });
      }
    }
  },
  { immediate: true }
);

// ---------------------------------------------------------------------------
// Live totals — mirrors Collection.validate() on the server
// ---------------------------------------------------------------------------
function tableStats(rows) {
  let cash = 0, cls = 0, cashCount = 0, clsCount = 0;
  for (const row of rows) {
    const amt = row.amount || 0;
    if (row.account_type === "Cash") { cash += amt; cashCount++; }
    else { cls += amt; clsCount++; }
  }
  return { cash, cls, cashCount, clsCount, all: cash + cls };
}

const tithes = computed(() => tableStats(form.tithes_collection));
const offering = computed(() => tableStats(form.offering_collection));
const mission = computed(() => tableStats(form.mission_collection));

const grandCash = computed(
  () =>
    tithes.value.cash + offering.value.cash + mission.value.cash +
    (form.benevolence_collection || 0) + (form.loose_collection || 0) +
    (form.sunday_school_collection || 0)
);
const grandCls = computed(
  () =>
    tithes.value.cls + offering.value.cls + mission.value.cls +
    (form.benevolence_collection_cls || 0) + (form.loose_collection_cls || 0)
);
const allGrand = computed(() => grandCash.value + grandCls.value);

const tallyTotal = computed(() =>
  form.collection_tally.reduce((sum, r) => sum + (r.total || 0), 0)
);
const tallyDiff = computed(() => Math.round((tallyTotal.value - grandCash.value) * 100) / 100);
const tallyBalanced = computed(() => tallyTotal.value > 0 && tallyDiff.value === 0);

function onTallyQty(row) {
  const coins = row.denum_name === "20" ? row.quantity_coins || 0 : 0;
  row.total = (row.denomination || 0) * ((row.quantity || 0) + coins);
  dirty.value = true;
}

// Coin denominations: ₱20 has a coin variant (quantity_coins); 10/5/1/0.25 are
// always coins — mirrors compute_tally_total() on the server.
const COIN_DENOMS = new Set(["10", "5", "1", "0.25"]);
const coins = computed(() => {
  let value = 0, pieces = 0;
  for (const row of form.collection_tally) {
    if (row.denum_name === "20") {
      value += (row.denomination || 0) * (row.quantity_coins || 0);
      pieces += row.quantity_coins || 0;
    } else if (COIN_DENOMS.has(String(row.denum_name))) {
      value += (row.denomination || 0) * (row.quantity || 0);
      pieces += row.quantity || 0;
    }
  }
  return { value: Math.round(value * 100) / 100, pieces };
});

// Per-type breakdown for the bottom summary
const summaryRows = computed(() => [
  { label: "Tithes", cash: tithes.value.cash, cls: tithes.value.cls, count: form.tithes_collection.filter((r) => r.number || r.amount).length },
  { label: "Offering", cash: offering.value.cash, cls: offering.value.cls, count: form.offering_collection.filter((r) => r.number || r.amount).length },
  { label: "Mission", cash: mission.value.cash, cls: mission.value.cls, count: form.mission_collection.filter((r) => r.number || r.amount).length },
  { label: "Benevolence", cash: form.benevolence_collection || 0, cls: form.benevolence_collection_cls || 0, count: null },
  { label: "Loose", cash: form.loose_collection || 0, cls: form.loose_collection_cls || 0, count: null },
  { label: "Sunday School", cash: form.sunday_school_collection || 0, cls: null, count: null },
]);

// ---------------------------------------------------------------------------
// New-member modal (from unknown envelope numbers or manual)
// ---------------------------------------------------------------------------
const showMemberModal = ref(false);
const memberPrefill = ref("");

function onCreateMember(row) {
  memberPrefill.value = row?.number || "";
  showMemberModal.value = true;
}

function onMemberSaved() {
  // Refresh the cached member list — unknown-envelope rows resolve instantly
  queryCache.invalidateQueries({ key: ["church-members"] });
}

// ---------------------------------------------------------------------------
// Date / service
// ---------------------------------------------------------------------------
const dateLocal = computed({
  get: () => (form.date ? form.date.slice(0, 16).replace(" ", "T") : ""),
  set: (v) => {
    form.date = v ? v.replace("T", " ") + ":00" : "";
    dirty.value = true;
  },
});

const serviceTag = computed(() => {
  const hour = parseInt(form.date?.slice(11, 13) || "0", 10);
  return hour <= 12 ? "MORNING" : "EVENING";
});

// ---------------------------------------------------------------------------
// Tabs
// ---------------------------------------------------------------------------
const activeTab = ref("tithes");
const tabs = computed(() => [
  { key: "tithes", label: "Tithes", count: form.tithes_collection.length, total: tithes.value.all },
  { key: "offering", label: "Offering", count: form.offering_collection.length, total: offering.value.all },
  { key: "mission", label: "Mission", count: form.mission_collection.length, total: mission.value.all },
  {
    key: "others", label: "Others", count: null,
    total:
      (form.benevolence_collection || 0) + (form.benevolence_collection_cls || 0) +
      (form.loose_collection || 0) + (form.loose_collection_cls || 0) +
      (form.sunday_school_collection || 0),
  },
  { key: "tally", label: "Cash Tally", count: null, total: tallyTotal.value, tally: true },
]);

// ---------------------------------------------------------------------------
// Validation + save/submit/delete
// ---------------------------------------------------------------------------
const TABLES = [
  ["tithes_collection", "Tithes", "tithes"],
  ["offering_collection", "Offering", "offering"],
  ["mission_collection", "Mission", "mission"],
];

function validate() {
  if (!form.date) return { msg: "Date and time of the service is required.", tab: "tithes" };
  for (const [field, label, tab] of TABLES) {
    for (let i = 0; i < form[field].length; i++) {
      const row = form[field][i];
      if (!row.number && !row.amount) continue;
      if (row.number && !membersMap.value.get(String(row.number).trim().toUpperCase())) {
        return { msg: `${label} row ${i + 1}: no member found for envelope "${row.number}". Fix the number or clear it.`, tab };
      }
    }
  }
  return null;
}

function buildPayload() {
  const payload = {
    name: form.name,
    date: form.date,
    cost_center: form.cost_center || null,
    attendees: form.attendees || 0,
    benevolence_collection: form.benevolence_collection || 0,
    benevolence_collection_cls: form.benevolence_collection_cls || 0,
    loose_collection: form.loose_collection || 0,
    loose_collection_cls: form.loose_collection_cls || 0,
    sunday_school_collection: form.sunday_school_collection || 0,
  };
  for (const [field] of TABLES) {
    payload[field] = form[field]
      .filter((row) => row.number || row.amount)
      .map((row) => {
        const member = membersMap.value.get(String(row.number).trim().toUpperCase());
        return {
          number: member ? member.name : "",
          first_name: member?.firstname || "",
          last_name: member?.lastname || "",
          amount: row.amount || 0,
          account_type: row.account_type || "Cash",
        };
      });
  }
  payload.collection_tally = form.collection_tally.map((r) => ({
    denum_name: r.denum_name,
    quantity: r.quantity || 0,
    quantity_coins: r.quantity_coins || 0,
    total: r.total || 0,
  }));
  return payload;
}

async function save() {
  errorMsg.value = "";
  const problem = validate();
  if (problem) {
    errorMsg.value = problem.msg;
    activeTab.value = problem.tab;
    return null;
  }
  saving.value = true;
  try {
    const wasNew = !form.name;
    const doc = await call("church_management.api.collection.save_collection", { doc: buildPayload() });
    hydrate(doc);
    if (wasNew) router.replace({ name: "CollectionForm", params: { name: doc.name } });
    savedFlash.value = true;
    setTimeout(() => (savedFlash.value = false), 2000);
    return doc;
  } catch (e) {
    errorMsg.value = e.message || "Failed to save.";
    return null;
  } finally {
    saving.value = false;
  }
}

async function doSubmit() {
  submitting.value = true;
  errorMsg.value = "";
  try {
    const saved = await save();
    if (!saved) return;
    const doc = await call("church_management.api.collection.submit_collection", { name: saved.name });
    hydrate(doc);
    showSubmitConfirm.value = false;
  } catch (e) {
    errorMsg.value = e.message || "Failed to submit.";
    showSubmitConfirm.value = false;
  } finally {
    submitting.value = false;
  }
}

async function doDelete() {
  deleting.value = true;
  errorMsg.value = "";
  try {
    await call("church_management.api.collection.delete_collection", { name: form.name });
    router.replace({ name: "CollectionList" });
  } catch (e) {
    errorMsg.value = e.message || "Failed to delete.";
    showDeleteConfirm.value = false;
  } finally {
    deleting.value = false;
  }
}

const status = computed(() =>
  form.docstatus === 1 ? "Submitted" : form.docstatus === 2 ? "Cancelled" : "Draft"
);
</script>

<template>
  <div class="px-4 sm:px-6 py-4 sm:py-6 max-w-5xl mx-auto w-full">
    <PageHeader
      :title="isNew ? 'New Collection' : String(route.params.name)"
      :subtitle="isNew ? 'Record a service\'s collections' : ''"
    >
      <template #actions>
        <div class="flex items-center gap-2">
          <Transition name="fade">
            <span v-if="savedFlash" class="inline-flex items-center gap-1 text-xs font-semibold text-green-600 anim-pop">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
              </svg>
              Saved
            </span>
          </Transition>
          <StatusBadge :status="status" />
          <AppButton variant="ghost" size="sm" @click="router.push({ name: 'CollectionList' })">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
            </svg>
            <span class="hidden sm:inline">Back</span>
          </AppButton>
        </div>
      </template>
    </PageHeader>

    <!-- Load error / loading -->
    <div v-if="loadError" class="p-4 bg-red-50 text-red-700 rounded-xl text-sm">{{ loadError.message }}</div>
    <div v-else-if="!isNew && loadingDetail" class="space-y-3">
      <div class="h-20 bg-white rounded-2xl border border-gray-100 animate-pulse" />
      <div class="h-64 bg-white rounded-2xl border border-gray-100 animate-pulse" />
    </div>

    <template v-else>
      <!-- Error banner -->
      <div v-if="errorMsg" class="mb-4 p-3 bg-red-50 text-red-700 rounded-xl text-sm flex items-start gap-2">
        <svg class="w-4 h-4 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
        </svg>
        <span class="whitespace-pre-line">{{ errorMsg }}</span>
      </div>

      <!-- Journal entry banner (after submit) -->
      <div v-if="form.journal_entry" class="mb-4 p-3 bg-green-50 text-green-800 rounded-xl text-sm flex items-center gap-2">
        <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        Posted to the books —
        <a
          :href="`/app/journal-entry/${encodeURIComponent(form.journal_entry)}`"
          target="_blank" rel="noopener"
          class="font-semibold underline hover:text-green-900"
        >{{ form.journal_entry }}</a>
      </div>

      <!-- Service info + grand totals -->
      <div class="bg-white rounded-2xl border border-gray-100 p-4 mb-5">
        <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1.4fr)_repeat(3,minmax(0,1fr))] gap-4 items-end">
          <div>
            <label class="text-[10px] font-medium text-gray-400 uppercase tracking-wider flex items-center gap-1.5 mb-1">
              Service date &amp; time
              <span
                class="text-[9px] px-1.5 py-0.5 rounded-full font-black tracking-wider"
                :class="serviceTag === 'MORNING' ? 'bg-amber-50 text-amber-700' : 'bg-indigo-50 text-indigo-700'"
                title="Morning (until 12:59) or Evening service — sets the record name"
              >{{ serviceTag }}</span>
            </label>
            <input v-model="dateLocal" type="datetime-local" :disabled="readOnly" class="cm-field tabular" />
          </div>
          <div class="bg-gray-50/70 rounded-xl p-3">
            <p class="text-[11px] text-gray-500 uppercase tracking-wide font-medium">Cash</p>
            <div class="mt-1"><CurrencyDisplay :value="grandCash" size="lg" /></div>
          </div>
          <div class="bg-sky-50/70 rounded-xl p-3">
            <p class="text-[11px] text-sky-600 uppercase tracking-wide font-medium">Cashless</p>
            <div class="mt-1"><CurrencyDisplay :value="grandCls" size="lg" /></div>
          </div>
          <div class="bg-green-50/70 rounded-xl p-3">
            <p class="text-[11px] text-green-600 uppercase tracking-wide font-medium">Grand Total</p>
            <div class="mt-1"><CurrencyDisplay :value="allGrand" size="lg" /></div>
          </div>
        </div>

        <!-- Tally check strip -->
        <div
          class="mt-3 flex items-center gap-2 rounded-xl px-3 py-2 text-xs font-semibold"
          :class="tallyBalanced ? 'bg-green-50 text-green-700' : tallyTotal > 0 ? 'bg-amber-50 text-amber-700' : 'bg-gray-50 text-gray-400'"
        >
          <svg v-if="tallyBalanced" class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m0 3h.008v.008H12v-.008zM21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <template v-if="tallyBalanced">Denomination tally matches the cash total.</template>
          <template v-else-if="tallyTotal > 0">
            Tally is <CurrencyDisplay :value="Math.abs(tallyDiff)" size="xs" weight="bold" />
            {{ tallyDiff > 0 ? "over" : "short of" }} the cash total.
          </template>
          <template v-else>No cash tally counted yet.</template>
        </div>
      </div>

      <!-- Tabs -->
      <div class="bg-white rounded-2xl border border-gray-100 overflow-hidden shadow-sm">
        <div class="border-b border-gray-100 overflow-x-auto scrollbar-hide bg-gray-50/50">
          <div class="flex w-full px-1 sm:px-2">
            <button
              v-for="tab in tabs"
              :key="tab.key"
              class="relative flex-1 min-w-0 px-2 sm:px-4 py-3 text-sm font-bold whitespace-nowrap transition-all border-b-2 outline-none"
              :class="
                activeTab === tab.key
                  ? 'border-brand-500 text-brand-600 bg-white/60'
                  : 'border-transparent text-gray-400 hover:text-gray-600 hover:bg-gray-100/50'
              "
              @click="activeTab = tab.key"
            >
              <div class="flex flex-col items-center gap-1">
                <span class="flex items-center gap-1">
                  {{ tab.label }}
                  <svg
                    v-if="tab.tally && tallyBalanced"
                    class="w-3.5 h-3.5 text-green-500"
                    fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"
                  >
                    <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                  </svg>
                  <span v-else-if="tab.count" class="text-[10px] font-black text-gray-400">({{ tab.count }})</span>
                </span>
                <CurrencyDisplay :value="tab.total" size="xs" :weight="activeTab === tab.key ? 'bold' : ''" />
              </div>
            </button>
          </div>
        </div>

        <div class="p-4 sm:p-6 min-h-[320px]">
          <!-- Entry tables -->
          <CollectionEntryTable
            v-show="activeTab === 'tithes'"
            :rows="form.tithes_collection"
            :members-map="membersMap"
            title="Tithes"
            accent="brand"
            :disabled="readOnly"
            @dirty="dirty = true"
            @create-member="onCreateMember"
          />
          <CollectionEntryTable
            v-show="activeTab === 'offering'"
            :rows="form.offering_collection"
            :members-map="membersMap"
            title="Offering"
            accent="violet"
            :disabled="readOnly"
            @dirty="dirty = true"
            @create-member="onCreateMember"
          />
          <CollectionEntryTable
            v-show="activeTab === 'mission'"
            :rows="form.mission_collection"
            :members-map="membersMap"
            title="Mission"
            accent="teal"
            :disabled="readOnly"
            @dirty="dirty = true"
            @create-member="onCreateMember"
          />

          <!-- Others: math-enabled money fields -->
          <div v-show="activeTab === 'others'" class="max-w-2xl space-y-5">
            <div class="flex items-start gap-2 rounded-xl bg-brand-50/60 px-3 py-2.5 text-xs text-brand-700">
              <svg class="w-4 h-4 shrink-0 mt-0.5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" />
              </svg>
              <span>
                These fields do the math for you: counting mixed bills? Type
                <code class="font-bold">(50*3)+20+5+5</code> and press <b>Enter</b> — no calculator needed.
              </span>
            </div>

            <div class="flex flex-col sm:flex-row sm:items-end gap-2 sm:gap-4">
              <label class="w-full sm:w-32 shrink-0 text-sm font-semibold text-gray-700 sm:pb-3">Benevolence</label>
              <div class="flex-1 min-w-0">
                <span class="block text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1">Cash</span>
                <MathInput v-model="form.benevolence_collection" :disabled="readOnly" @update:model-value="dirty = true" />
              </div>
              <div class="flex-1 min-w-0">
                <span class="block text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1">Cashless (GCash / Bank)</span>
                <MathInput v-model="form.benevolence_collection_cls" :disabled="readOnly" @update:model-value="dirty = true" />
              </div>
            </div>

            <div class="flex flex-col sm:flex-row sm:items-end gap-2 sm:gap-4">
              <label class="w-full sm:w-32 shrink-0 text-sm font-semibold text-gray-700 sm:pb-3">Loose</label>
              <div class="flex-1 min-w-0">
                <span class="block text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1">Cash</span>
                <MathInput v-model="form.loose_collection" :disabled="readOnly" @update:model-value="dirty = true" />
              </div>
              <div class="flex-1 min-w-0">
                <span class="block text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1">Cashless (GCash / Bank)</span>
                <MathInput v-model="form.loose_collection_cls" :disabled="readOnly" @update:model-value="dirty = true" />
              </div>
            </div>

            <div class="flex flex-col sm:flex-row sm:items-end gap-2 sm:gap-4">
              <label class="w-full sm:w-32 shrink-0 text-sm font-semibold text-gray-700 sm:pb-3">Sunday School</label>
              <div class="flex-1 min-w-0">
                <span class="block text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1">Cash</span>
                <MathInput v-model="form.sunday_school_collection" :disabled="readOnly" @update:model-value="dirty = true" />
              </div>
              <div class="flex-1 min-w-0 hidden sm:flex items-center text-xs text-gray-300 italic pb-3">cash only</div>
            </div>

            <div class="flex flex-col sm:flex-row sm:items-end gap-2 sm:gap-4 pt-2 border-t border-gray-100">
              <label class="w-full sm:w-32 shrink-0 text-sm font-semibold text-gray-700 sm:pb-3">Attendees</label>
              <div class="flex-1 min-w-0">
                <span class="block text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1">Headcount</span>
                <input
                  v-model.number="form.attendees"
                  type="number" min="0" inputmode="numeric" placeholder="0"
                  :disabled="readOnly"
                  class="cm-field text-right tabular"
                  @input="dirty = true"
                />
              </div>
              <div class="hidden sm:block flex-1" />
            </div>
          </div>

          <!-- Cash tally -->
          <div v-show="activeTab === 'tally'" class="max-w-xl">
            <p class="text-xs text-gray-500 mb-4">
              Count the physical cash per denomination — the tally should match the
              <b>Cash</b> grand total before submitting.
            </p>

            <div class="flex items-center gap-2 px-1 pb-2 text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
              <span class="w-16 shrink-0">Denom.</span>
              <span class="flex-1">Quantity</span>
              <span class="w-28 text-right shrink-0">Total</span>
            </div>

            <div class="space-y-1.5">
              <div v-for="row in form.collection_tally" :key="row.denum_name" class="flex items-center gap-2">
                <span class="w-16 shrink-0 font-bold text-gray-700 tabular text-sm">₱{{ row.denum_name }}</span>
                <div class="flex-1 flex items-center gap-1.5">
                  <input
                    v-model.number="row.quantity"
                    type="number" min="0" inputmode="numeric" placeholder="0"
                    :disabled="readOnly"
                    class="cm-field !h-10 !w-20 text-center tabular"
                    :title="row.denum_name === '20' ? '₱20 bills' : undefined"
                    @input="onTallyQty(row)"
                    @focus="$event.target.select()"
                  />
                  <template v-if="row.denum_name === '20'">
                    <span class="text-[10px] text-gray-400 font-medium">bills</span>
                    <input
                      v-model.number="row.quantity_coins"
                      type="number" min="0" inputmode="numeric" placeholder="0"
                      :disabled="readOnly"
                      title="₱20 coins"
                      class="cm-field !h-10 !w-20 text-center tabular"
                      @input="onTallyQty(row)"
                      @focus="$event.target.select()"
                    />
                    <span class="text-[10px] text-gray-400 font-medium">coins</span>
                  </template>
                  <span v-else-if="COIN_DENOMS.has(String(row.denum_name))" class="text-[10px] text-gray-400 font-medium">coins</span>
                </div>
                <div class="w-28 text-right shrink-0"><CurrencyDisplay :value="row.total" /></div>
              </div>
            </div>

            <div class="flex items-center justify-between gap-3 mt-4 pt-3 border-t border-gray-100">
              <span
                class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border bg-amber-50 text-amber-700 border-amber-100"
                title="₱20 coins plus all ₱10 / ₱5 / ₱1 / ₱0.25"
              >
                Coins · {{ coins.pieces }} pc<template v-if="coins.pieces !== 1">s</template>
                <CurrencyDisplay :value="coins.value" size="xs" weight="bold" />
              </span>
              <div class="flex items-baseline gap-2">
                <span class="text-xs font-semibold text-gray-500 uppercase tracking-wider">Tally total</span>
                <CurrencyDisplay :value="tallyTotal" weight="bold" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Collection summary -->
      <div class="mt-5 bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
        <div class="px-4 sm:px-5 py-3 border-b border-gray-100 flex items-center justify-between gap-2">
          <div class="flex items-center gap-2">
            <svg class="w-4 h-4 text-brand-500" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5m.75-9l3-3 2.148 2.148A12.061 12.061 0 0116.5 7.605" />
            </svg>
            <h2 class="text-sm font-bold text-gray-800">Collection Summary</h2>
          </div>
          <span v-if="form.attendees" class="text-xs text-gray-400 font-medium">{{ form.attendees }} attendees</span>
        </div>

        <div class="overflow-x-auto">
          <table class="min-w-full text-sm">
            <thead class="bg-gray-50/80">
              <tr class="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">
                <th class="px-4 sm:px-5 py-2.5 text-left">Type</th>
                <th class="px-3 py-2.5 text-right">Count</th>
                <th class="px-3 py-2.5 text-right">Cash</th>
                <th class="px-3 py-2.5 text-right">Cashless</th>
                <th class="px-4 sm:px-5 py-2.5 text-right">Total</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-50">
              <tr v-for="row in summaryRows" :key="row.label" class="hover:bg-gray-50/60 transition-colors">
                <td class="px-4 sm:px-5 py-2.5 font-semibold text-gray-700 whitespace-nowrap">{{ row.label }}</td>
                <td class="px-3 py-2.5 text-right text-gray-500 tabular">{{ row.count ?? "—" }}</td>
                <td class="px-3 py-2.5 text-right whitespace-nowrap"><CurrencyDisplay :value="row.cash" /></td>
                <td class="px-3 py-2.5 text-right whitespace-nowrap">
                  <CurrencyDisplay v-if="row.cls !== null" :value="row.cls" />
                  <span v-else class="text-xs text-gray-300 italic">cash only</span>
                </td>
                <td class="px-4 sm:px-5 py-2.5 text-right whitespace-nowrap">
                  <CurrencyDisplay :value="row.cash + (row.cls || 0)" weight="bold" />
                </td>
              </tr>
            </tbody>
            <tfoot>
              <tr class="bg-gray-50/80 border-t border-gray-100">
                <td class="px-4 sm:px-5 py-3 font-black text-gray-900 uppercase text-xs tracking-wider">Grand Total</td>
                <td />
                <td class="px-3 py-3 text-right whitespace-nowrap"><CurrencyDisplay :value="grandCash" weight="bold" /></td>
                <td class="px-3 py-3 text-right whitespace-nowrap"><CurrencyDisplay :value="grandCls" weight="bold" /></td>
                <td class="px-4 sm:px-5 py-3 text-right whitespace-nowrap"><CurrencyDisplay :value="allGrand" size="lg" /></td>
              </tr>
            </tfoot>
          </table>
        </div>

        <!-- Coins + tally strip -->
        <div class="px-4 sm:px-5 py-3 border-t border-gray-100 flex flex-wrap items-center gap-2">
          <span
            class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border bg-amber-50 text-amber-700 border-amber-100"
            title="₱20 coins plus all ₱10 / ₱5 / ₱1 / ₱0.25 from the cash tally"
          >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Coins · {{ coins.pieces }} pc<template v-if="coins.pieces !== 1">s</template>
            <CurrencyDisplay :value="coins.value" size="xs" weight="bold" />
          </span>
          <span
            class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border"
            :class="tallyBalanced ? 'bg-green-50 text-green-700 border-green-100' : 'bg-gray-50 text-gray-600 border-gray-200'"
          >
            Cash tally
            <CurrencyDisplay :value="tallyTotal" size="xs" weight="bold" />
          </span>
          <span
            v-if="tallyTotal > 0 && !tallyBalanced"
            class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border bg-red-50 text-red-700 border-red-100"
          >
            {{ tallyDiff > 0 ? "Over" : "Short" }}
            <CurrencyDisplay :value="Math.abs(tallyDiff)" size="xs" weight="bold" />
          </span>
        </div>
      </div>

      <!-- Action bar -->
      <div v-if="!readOnly" class="sticky bottom-0 z-30 mt-5 -mx-4 sm:-mx-6 px-4 sm:px-6 py-3 bg-gray-50/90 backdrop-blur border-t border-gray-200 flex items-center justify-between gap-3">
        <AppButton
          v-if="form.name"
          variant="ghost" size="sm"
          class="!text-red-600 hover:!bg-red-50"
          :disabled="saving || submitting"
          @click="showDeleteConfirm = true"
        >
          Delete draft
        </AppButton>
        <span v-else class="text-xs text-gray-400 hidden sm:block">
          Saving keeps a draft — submitting posts the Journal Entry.
        </span>
        <div class="flex items-center gap-2">
          <AppButton variant="secondary" :loading="saving" :disabled="submitting" @click="save">
            Save draft
          </AppButton>
          <AppButton :loading="submitting" :disabled="saving" @click="showSubmitConfirm = true">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
            </svg>
            Submit
          </AppButton>
        </div>
      </div>
    </template>

    <!-- Submit confirmation -->
    <Teleport to="body">
      <div v-if="showSubmitConfirm" class="fixed inset-0 z-[60] flex items-end sm:items-center justify-center p-4">
        <div class="absolute inset-0 bg-gray-900/40 backdrop-blur-sm" @click="!submitting && (showSubmitConfirm = false)" />
        <div class="relative bg-white rounded-2xl shadow-2xl w-full max-w-md p-5 anim-pop">
          <h3 class="text-base font-bold text-gray-900">Submit this collection?</h3>
          <p class="mt-2 text-sm text-gray-600">
            Submitting posts a <b>Journal Entry</b> to the church books and locks this record.
            You won't be able to edit amounts afterwards.
          </p>
          <div
            v-if="!tallyBalanced && tallyTotal > 0"
            class="mt-3 p-2.5 rounded-xl bg-amber-50 text-amber-700 text-xs font-semibold flex items-center gap-2"
          >
            <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m0 3h.008v.008H12v-.008zM21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Heads up: the cash tally is off by <CurrencyDisplay :value="Math.abs(tallyDiff)" size="xs" weight="bold" />.
          </div>
          <div class="mt-4 grid grid-cols-2 gap-3 text-sm bg-gray-50 rounded-xl p-3">
            <span class="text-gray-500">Grand total</span>
            <span class="text-right"><CurrencyDisplay :value="allGrand" weight="bold" /></span>
            <span class="text-gray-500">Service</span>
            <span class="text-right font-semibold text-gray-800">{{ form.date?.slice(0, 10) }} {{ serviceTag }}</span>
          </div>
          <div class="mt-5 flex justify-end gap-2">
            <AppButton variant="secondary" size="sm" :disabled="submitting" @click="showSubmitConfirm = false">Cancel</AppButton>
            <AppButton size="sm" :loading="submitting" @click="doSubmit">Submit &amp; post entry</AppButton>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- New member (from unknown envelope) -->
    <MemberModal
      :is-open="showMemberModal"
      :prefill-envelope="memberPrefill"
      @close="showMemberModal = false"
      @saved="onMemberSaved"
    />

    <!-- Delete confirmation -->
    <Teleport to="body">
      <div v-if="showDeleteConfirm" class="fixed inset-0 z-[60] flex items-end sm:items-center justify-center p-4">
        <div class="absolute inset-0 bg-gray-900/40 backdrop-blur-sm" @click="!deleting && (showDeleteConfirm = false)" />
        <div class="relative bg-white rounded-2xl shadow-2xl w-full max-w-sm p-5 anim-pop">
          <h3 class="text-base font-bold text-gray-900">Delete this draft?</h3>
          <p class="mt-2 text-sm text-gray-600">
            <b>{{ form.name }}</b> and all its entered rows will be permanently removed.
          </p>
          <div class="mt-5 flex justify-end gap-2">
            <AppButton variant="secondary" size="sm" :disabled="deleting" @click="showDeleteConfirm = false">Cancel</AppButton>
            <AppButton variant="danger" size="sm" :loading="deleting" @click="doDelete">Delete</AppButton>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
