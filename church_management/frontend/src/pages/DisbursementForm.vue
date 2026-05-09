<script setup>
import { ref, computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useQuery } from "@pinia/colada";
import { call } from "@/composables/useFrappeApi";
import PageHeader from "@/components/PageHeader.vue";
import AppButton from "@/components/AppButton.vue";
import CurrencyDisplay from "@/components/CurrencyDisplay.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import WeekTab from "@/components/WeekTab.vue";

const route = useRoute();
const router = useRouter();
const activeTab = ref(1);
const summaryOpen = ref(true);
const isNew = computed(() => route.params.name === "new");

const {
  data: disbursement,
  isPending: loading,
  error,
  refetch,
} = useQuery({
  key: () => ["disbursement", route.params.name],
  query: () => call("church_management.api.disbursement.get_detail", { name: route.params.name }),
  enabled: () => !isNew.value,
});

function isClaimed(i) {
  return i.status === "Claimed" || (!!i.received_by && !!i.received_date);
}

// Collect items only from weeks that actually exist in the month, so the summary
// matches the per-tab counts (April has only 4 Sundays — week_5 child rows are ghosts).
const allItems = computed(() => {
  const ws = weeks.value;
  const result = [];
  for (const w of ws) {
    for (const row of w.items) result.push(row);
    for (const row of w.expenses) result.push(row);
  }
  for (const row of monthlyItems.value) result.push(row);
  for (const row of monthlyExpenses.value) result.push(row);
  return result;
});

// Summary stats
const totalClaimed = computed(() =>
  allItems.value
    .filter(isClaimed)
    .reduce((sum, i) => sum + (i.amount || 0), 0)
);

const totalPlanned = computed(() =>
  allItems.value
    .filter((i) => i.is_planned)
    .reduce((sum, i) => sum + (i.amount || 0), 0)
);

const totalCount = computed(() => allItems.value.length);
const claimedCount = computed(() => allItems.value.filter(isClaimed).length);
const unclaimedCount = computed(() => totalCount.value - claimedCount.value);

const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

function sundaysOfMonth(year, monthIdx) {
  const result = [];
  const daysInMonth = new Date(year, monthIdx + 1, 0).getDate();
  for (let i = 1; i <= daysInMonth; i++) {
    const dt = new Date(year, monthIdx, i);
    if (dt.getDay() === 0) result.push(dt);
  }
  return result;
}

const today = new Date();
today.setHours(0, 0, 0, 0);

const weeks = computed(() => {
  if (!disbursement.value) return [];
  const d = disbursement.value;

  const monthIdx = monthNames.indexOf(d.month_recorded);
  if (monthIdx === -1 || !d.year_recorded) return [];
  const year = parseInt(d.year_recorded);
  const sundays = sundaysOfMonth(year, monthIdx).slice(0, 5);

  const isPastMonth =
    year < today.getFullYear() ||
    (year === today.getFullYear() && monthIdx < today.getMonth());

  return sundays.map((sunday, idx) => {
    const num = idx + 1;
    const items = d[`disbursement_item_week_${num}`] || [];
    const expenses = d[`expense_item_week_${num}`] || [];
    const hasUnclaimed = [...items, ...expenses].some((i) => !isClaimed(i));
    const overdue = isPastMonth && hasUnclaimed;
    return { num, items, expenses, sunday, overdue };
  });
});

const isPastMonth = computed(() => {
  if (!disbursement.value) return false;
  const monthIdx = monthNames.indexOf(disbursement.value.month_recorded);
  if (monthIdx === -1 || !disbursement.value.year_recorded) return false;
  const year = parseInt(disbursement.value.year_recorded);
  return (
    year < today.getFullYear() ||
    (year === today.getFullYear() && monthIdx < today.getMonth())
  );
});

function fmtSunday(dt) {
  if (!dt) return "";
  return dt.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}
function fmtSundayLong(dt) {
  if (!dt) return "";
  return dt.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
}
function isoDate(dt) {
  if (!dt) return "";
  const y = dt.getFullYear();
  const m = String(dt.getMonth() + 1).padStart(2, "0");
  const d = String(dt.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

const monthlyItems = computed(() => disbursement.value?.monthly_disbursement_items || []);
const monthlyExpenses = computed(() => disbursement.value?.monthly_expense_items || []);

const tabs = computed(() => {
  const t = weeks.value.map((w) => {
    const all = [...w.items, ...w.expenses];
    const totalCount = all.length;
    const claimedCount = all.filter(isClaimed).length;
    const unclaimedCount = totalCount - claimedCount;
    const unclaimedAmount = all.filter(i => !isClaimed(i)).reduce((sum, i) => sum + (i.amount || 0), 0);
    
    let display = null;
    if (totalCount > 0) {
      if (unclaimedAmount > 0) {
        display = `${unclaimedCount}/${claimedCount}`;
      } else {
        display = `${totalCount}`;
      }
    }

    return {
      key: w.num,
      label: `W${w.num}`,
      fullLabel: `Week ${w.num}`,
      sundayShort: fmtSunday(w.sunday),
      countDisplay: display,
      overdue: w.overdue,
    };
  });
  
  const mAll = [...monthlyItems.value, ...monthlyExpenses.value];
  const mTotal = mAll.length;
  const mClaimed = mAll.filter(isClaimed).length;
  const mUnclaimedCount = mTotal - mClaimed;
  const mUnclaimedAmount = mAll.filter(i => !isClaimed(i)).reduce((sum, i) => sum + (i.amount || 0), 0);

  let mDisplay = null;
  if (mTotal > 0) {
    if (mUnclaimedAmount > 0) {
      mDisplay = `${mUnclaimedCount}/${mClaimed}`;
    } else {
      mDisplay = `${mTotal}`;
    }
  }

  t.push({
    key: 0,
    label: "Monthly",
    fullLabel: "Monthly",
    sundayShort: "",
    countDisplay: mDisplay,
    overdue: isPastMonth.value && mUnclaimedCount > 0,
  });
  return t;
});

const status = computed(() => {
  if (!disbursement.value) return "Draft";
  const ds = disbursement.value.docstatus;
  return ds === 1 ? "Submitted" : ds === 2 ? "Cancelled" : "Draft";
});

function onClaimed() {
  refetch();
}
</script>

<template>
  <div class="px-4 sm:px-6 py-4 sm:py-6 max-w-5xl mx-auto w-full">
    <!-- Header -->
    <PageHeader
      :title="isNew ? 'New Disbursement' : route.params.name"
      :subtitle="isNew ? 'Create monthly disbursement' : `${disbursement?.month_recorded || ''} ${disbursement?.year_recorded || ''}`"
    >
      <template #actions>
        <div class="flex items-center gap-2">
          <StatusBadge v-if="!isNew && disbursement" :status="status" />
          <AppButton variant="ghost" size="sm" @click="router.push({ name: 'DisbursementList' })">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
            </svg>
            <span class="hidden sm:inline">Back</span>
          </AppButton>
        </div>
      </template>
    </PageHeader>

    <!-- Loading -->
    <div v-if="loading" class="space-y-3">
      <div class="h-12 bg-white rounded-2xl border border-gray-100 animate-pulse" />
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div v-for="i in 4" :key="i" class="h-20 bg-white rounded-2xl border border-gray-100 animate-pulse" />
      </div>
      <div class="h-64 bg-white rounded-2xl border border-gray-100 animate-pulse" />
    </div>

    <!-- Error -->
    <div v-else-if="error" class="p-4 bg-red-50 text-red-700 rounded-xl text-sm">
      {{ error.message }}
    </div>

    <!-- Content -->
    <template v-else-if="disbursement || isNew">
      <!-- Collapsible Summary Section -->
      <div v-if="disbursement" class="mb-5">
        <button
          @click="summaryOpen = !summaryOpen"
          class="w-full flex items-center justify-between px-4 py-3 bg-white rounded-2xl border border-gray-100 transition-colors hover:bg-gray-50"
          :class="summaryOpen ? 'rounded-b-none border-b-0' : ''"
        >
          <div class="flex items-center gap-2.5">
            <span class="text-sm font-bold text-gray-800">Summary</span>
            <span class="text-xs text-gray-400">
              {{ claimedCount }}/{{ totalCount }} claimed
            </span>
          </div>
          <svg
            class="w-4 h-4 text-gray-400 transition-transform duration-200"
            :class="summaryOpen ? 'rotate-180' : ''"
            fill="none" stroke="currentColor" viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        <Transition name="collapse">
          <div
            v-show="summaryOpen"
            class="bg-white border border-gray-100 border-t-0 rounded-b-2xl overflow-hidden"
          >
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3">
              <!-- Total Claimed -->
              <div class="bg-green-50/70 rounded-xl p-3.5">
                <p class="text-[11px] text-green-600 uppercase tracking-wide font-medium">Total Claimed</p>
                <div class="mt-1.5">
                  <CurrencyDisplay :value="totalClaimed" size="lg" />
                </div>
              </div>

              <!-- Planned Amount -->
              <div class="bg-blue-50/70 rounded-xl p-3.5">
                <p class="text-[11px] text-blue-600 uppercase tracking-wide font-medium">Planned Amount</p>
                <div class="mt-1.5">
                  <CurrencyDisplay :value="totalPlanned" size="lg" />
                </div>
              </div>

              <!-- Unclaimed / Total -->
              <div class="bg-amber-50/70 rounded-xl p-3.5">
                <p class="text-[11px] text-amber-600 uppercase tracking-wide font-medium">Unclaimed</p>
                <div class="mt-1.5 flex items-baseline gap-1">
                  <span class="text-xl font-black text-amber-700">{{ unclaimedCount }}</span>
                  <span class="text-sm text-amber-500 font-medium">/ {{ totalCount }}</span>
                </div>
              </div>

              <!-- Month / Year -->
              <div class="bg-gray-50/70 rounded-xl p-3.5">
                <p class="text-[11px] text-gray-500 uppercase tracking-wide font-medium">Period</p>
                <span class="text-lg sm:text-xl font-black text-gray-900 mt-1.5 block leading-tight">
                  {{ disbursement.month_recorded }}
                  <span class="text-sm font-semibold text-gray-400">{{ disbursement.year_recorded }}</span>
                </span>
              </div>
            </div>
          </div>
        </Transition>
      </div>

      <!-- Tabs + Content -->
      <div v-if="weeks.length" class="bg-white rounded-2xl border border-gray-100 overflow-hidden shadow-sm">
        <!-- Scrollable tab bar -->
        <div class="border-b border-gray-100 overflow-x-auto scrollbar-hide bg-gray-50/50">
          <div class="flex w-full px-1 sm:px-2">
            <button
              v-for="tab in tabs"
              :key="tab.key"
              @click="activeTab = tab.key"
              class="relative flex-1 min-w-0 px-2 sm:px-4 py-3 sm:py-4 text-sm font-bold whitespace-nowrap transition-all border-b-2 outline-none group"
              :class="[
                activeTab === tab.key
                  ? 'border-brand-500 text-brand-600 bg-white/60'
                  : 'border-transparent text-gray-400 hover:text-gray-600 hover:bg-gray-100/50',
                tab.overdue ? 'overdue-blink-tab' : ''
              ]"
            >
              <div class="flex flex-col items-center gap-1 transition-transform active:scale-95">
                <div class="flex items-baseline gap-1">
                  <span class="sm:hidden text-[13px]">{{ tab.label }}</span>
                  <span class="hidden sm:inline">{{ tab.fullLabel }}</span>
                </div>
                <span
                  v-if="tab.sundayShort"
                  class="text-[10px] font-semibold leading-none"
                  :class="tab.overdue ? 'text-red-600' : (activeTab === tab.key ? 'text-brand-500' : 'text-gray-400')"
                >
                  {{ tab.sundayShort }}
                </span>
                <span
                  v-if="tab.countDisplay"
                  class="text-[9px] px-2 py-0.5 rounded-full font-black tracking-widest leading-none border"
                  :class="tab.overdue
                    ? 'bg-red-50 text-red-700 border-red-200'
                    : (activeTab === tab.key ? 'bg-brand-50 text-brand-700 border-brand-100' : 'bg-gray-100 text-gray-500 border-gray-200 group-hover:border-gray-300')"
                >
                  {{ tab.countDisplay }}
                </span>
              </div>
            </button>
          </div>
        </div>

        <!-- Tab panels -->
        <div class="p-4 sm:p-6 min-h-[400px]">
          <!-- Week tabs -->
          <template v-if="activeTab > 0">
            <WeekTab
              v-for="week in weeks"
              v-show="activeTab === week.num"
              :key="week.num"
              :items="week.items"
              :expenses="week.expenses"
              :week-num="week.num"
              :sunday-iso="isoDate(week.sunday)"
              :sunday-label="fmtSundayLong(week.sunday)"
              :overdue="week.overdue"
              :disbursement-name="route.params.name"
              @claimed="onClaimed"
            />
          </template>

          <!-- Monthly tab -->
          <WeekTab
            v-if="activeTab === 0"
            :items="monthlyItems"
            :expenses="monthlyExpenses"
            :week-num="0"
            label="Monthly"
            :overdue="isPastMonth"
            :disbursement-name="route.params.name"
            @claimed="onClaimed"
          />
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.collapse-enter-active,
.collapse-leave-active {
  transition: all 0.2s ease;
  overflow: hidden;
}
.collapse-enter-from,
.collapse-leave-to {
  opacity: 0;
  max-height: 0;
}
.collapse-enter-to,
.collapse-leave-from {
  opacity: 1;
  max-height: 500px;
}
</style>
