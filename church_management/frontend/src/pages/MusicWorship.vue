<script setup>
import { onMounted, ref, reactive, computed } from "vue";
import { call } from "@/composables/useFrappeApi";
import { useMusicTeamStore } from "@/stores/musicTeam";
import { useRealtime } from "@/composables/useRealtime";
import MusicHeader from "@/components/MusicHeader.vue";
import MusicAvatar from "@/components/MusicAvatar.vue";

const store = useMusicTeamStore();
const plan = ref({ schedule: null, sundays: [] });
const loading = ref(false);
const saving = reactive({});
const message = reactive({});

// Lineup picker (reused worship-leader workflow on the same page)
const SERVICES = [
  { id: "am", label: "Morning", short: "AM", st: "Morning" },
  { id: "pm", label: "Evening", short: "PM", st: "Evening" },
];
const picker = ref(null); // { iso, service, role }
const search = ref("");

onMounted(async () => {
  await Promise.all([store.loadCatalog(), store.loadLineup(), store.loadUnavailability()]);
  await loadPlan();
});

useRealtime("music_team_event", async (msg) => {
  if (["worship_plan_updated"].includes(msg.action)) {
    await loadPlan();
  }
  if (["assignment_set", "assignment_cleared", "swap_accepted"].includes(msg.action)) {
    await store.loadLineup();
  }
});

async function loadPlan() {
  loading.value = true;
  try {
    plan.value = await call("church_management.api.music_team.get_worship_plan", {
      month: store.month, year: store.year,
    });
  } finally {
    loading.value = false;
  }
}

const previousMonth = async () => {
  let i = store.MONTHS.indexOf(store.month);
  if (i <= 0) { store.month = "December"; store.year -= 1; }
  else store.month = store.MONTHS[i - 1];
  await Promise.all([store.loadLineup(), loadPlan()]);
};
const nextMonth = async () => {
  let i = store.MONTHS.indexOf(store.month);
  if (i >= 11) { store.month = "January"; store.year += 1; }
  else store.month = store.MONTHS[i + 1];
  await Promise.all([store.loadLineup(), loadPlan()]);
};

async function savePlan(s) {
  saving[s.sunday_date] = true;
  message[s.sunday_date] = "";
  try {
    await call("church_management.api.music_team.set_worship_plan", {
      month: store.month, year: store.year,
      sunday_date: s.sunday_date,
      songs: s.songs ?? "",
      practice_datetime: s.practice_datetime || "",
      practice_location: s.practice_location ?? "",
      worship_leader_notes: s.worship_leader_notes ?? "",
    });
    message[s.sunday_date] = "Saved";
    setTimeout(() => { message[s.sunday_date] = ""; }, 1500);
  } catch (e) {
    message[s.sunday_date] = e.message || "Save failed";
  } finally {
    saving[s.sunday_date] = false;
  }
}

function fmtDate(iso) {
  return new Date(iso).toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" });
}

// --- Lineup helpers (mirrored from MusicLineup.vue) -------------------------

function slotInfo(iso, svc, roleName) {
  return store.lineup?.[iso]?.[svc]?.[roleName] || null;
}
function memberFor(slot) {
  if (!slot?.member) return null;
  return store.memberById[slot.member] || { name: slot.member, full_name: slot.member_name };
}
function usedInService(iso, svc, exceptRole) {
  const map = store.lineup?.[iso]?.[svc] || {};
  const used = new Set();
  for (const [role, slot] of Object.entries(map)) {
    if (role === exceptRole) continue;
    if (slot.member) used.add(slot.member);
  }
  return used;
}
const pickerList = computed(() => {
  if (!picker.value) return [];
  const { iso, service, role } = picker.value;
  const excluded = usedInService(iso, service, role);
  const q = search.value.trim().toLowerCase();
  return store.members
    .map(m => ({
      ...m,
      canRole: (m.roles || []).includes(role),
      isPreferred: m.preferred_role === role,
      excluded: excluded.has(m.name),
      unavail: store.isUnavailable(m.name, iso),
    }))
    .filter(m => !q || (m.full_name || "").toLowerCase().includes(q))
    .sort((a, b) => (b.isPreferred - a.isPreferred) || (b.canRole - a.canRole) || ((a.unavail ? 1 : 0) - (b.unavail ? 1 : 0)));
});
async function pick(memberId, memberName) {
  const { iso, service, role } = picker.value;
  await store.setSlot(iso, service, role, memberId, memberName);
  picker.value = null;
  search.value = "";
}
async function clearSlot() {
  const { iso, service, role } = picker.value;
  await store.setSlot(iso, service, role, "", "");
  picker.value = null;
  search.value = "";
}
</script>

<template>
  <div class="bg-[#f0eee9] min-h-full">
    <div class="max-w-3xl mx-auto bg-white min-h-screen shadow">
      <MusicHeader title="Worship Plan" subtitle="Songs, practice time, and lineup">
        <button class="px-2 py-1 text-xs font-medium text-ink-600 hover:bg-ink-50 rounded" @click="previousMonth">‹</button>
        <span class="text-xs font-bold text-ink-900 px-2">{{ store.month }} {{ store.year }}</span>
        <button class="px-2 py-1 text-xs font-medium text-ink-600 hover:bg-ink-50 rounded" @click="nextMonth">›</button>
      </MusicHeader>

      <div v-if="loading" class="px-6 py-10 text-center text-ink-400 text-sm">Loading plan…</div>

      <div v-else-if="!plan.schedule" class="px-6 py-10 text-center text-ink-400 text-sm">
        No Ministry Schedule exists for {{ store.month }} {{ store.year }} yet.
        Ask the music leader to create one in the Lineup view.
      </div>

      <div v-else class="px-6 py-6 space-y-5">
        <div v-for="s in plan.sundays" :key="s.sunday_date"
             class="bg-white rounded-2xl border border-ink-100 shadow-sm overflow-hidden">

          <!-- Header per Sunday -->
          <div class="px-5 py-3 bg-gradient-to-r from-rose-50 to-white border-b border-ink-100 flex items-center justify-between">
            <div>
              <div class="text-[10px] font-black uppercase tracking-widest text-rose-700">{{ fmtDate(s.sunday_date) }}</div>
              <div class="text-xs text-ink-500 mt-0.5">
                <span v-if="s.theme">{{ s.theme }}</span>
                <span v-if="s.theme && s.sermon_title"> · </span>
                <span v-if="s.sermon_title">{{ s.sermon_title }}</span>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <span v-if="message[s.sunday_date]" class="text-[11px] font-medium text-emerald-700">{{ message[s.sunday_date] }}</span>
              <button @click="savePlan(s)" :disabled="saving[s.sunday_date]"
                      class="px-3 py-1.5 text-xs font-bold bg-rose-600 text-white rounded-lg hover:bg-rose-700 disabled:bg-ink-300">
                {{ saving[s.sunday_date] ? "Saving…" : "Save plan" }}
              </button>
            </div>
          </div>

          <!-- Songs + practice -->
          <div class="p-5 grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="md:col-span-2">
              <label class="text-[10px] font-black uppercase tracking-widest text-ink-400">Songs</label>
              <textarea v-model="s.songs" rows="5" placeholder="One song per line…"
                        class="mt-1 w-full px-3 py-2 bg-ink-50 border border-ink-200 rounded-lg text-sm font-mono focus:bg-white focus:border-rose-500 outline-none" />
            </div>

            <div>
              <label class="text-[10px] font-black uppercase tracking-widest text-ink-400">Practice date/time</label>
              <input v-model="s.practice_datetime" type="datetime-local"
                     class="mt-1 w-full px-3 py-2 bg-ink-50 border border-ink-200 rounded-lg text-sm focus:bg-white focus:border-rose-500 outline-none" />
            </div>
            <div>
              <label class="text-[10px] font-black uppercase tracking-widest text-ink-400">Practice location</label>
              <input v-model="s.practice_location" type="text" placeholder="Sanctuary, Music Room…"
                     class="mt-1 w-full px-3 py-2 bg-ink-50 border border-ink-200 rounded-lg text-sm focus:bg-white focus:border-rose-500 outline-none" />
            </div>

            <div class="md:col-span-2">
              <label class="text-[10px] font-black uppercase tracking-widest text-ink-400">Notes</label>
              <textarea v-model="s.worship_leader_notes" rows="2" placeholder="Anything else the team should know…"
                        class="mt-1 w-full px-3 py-2 bg-ink-50 border border-ink-200 rounded-lg text-sm focus:bg-white focus:border-rose-500 outline-none" />
            </div>
          </div>

          <!-- Lineup quick edit -->
          <div class="px-5 pb-5">
            <div class="text-[10px] font-black uppercase tracking-widest text-ink-400 mb-2">Lineup</div>
            <div v-for="svc in SERVICES" :key="svc.id" class="mb-3">
              <div class="text-[11px] font-semibold text-ink-700 mb-1">{{ svc.label }}</div>
              <div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
                <button v-for="role in store.roles" :key="role.name"
                        @click="picker = { iso: s.sunday_date, service: svc.id, role: role.name }"
                        class="text-left px-3 py-2 bg-ink-50 hover:bg-rose-50 rounded-lg ring-1 ring-ink-100 hover:ring-rose-300 transition">
                  <div class="text-[9px] font-black uppercase tracking-widest text-ink-400">{{ role.tag_label || role.name }}</div>
                  <div v-if="memberFor(slotInfo(s.sunday_date, svc.id, role.name))" class="flex items-center gap-1.5 mt-0.5">
                    <MusicAvatar :id="memberFor(slotInfo(s.sunday_date, svc.id, role.name)).name"
                                 :name="memberFor(slotInfo(s.sunday_date, svc.id, role.name)).full_name"
                                 :size="20" />
                    <span class="text-xs font-semibold text-ink-900 truncate">
                      {{ memberFor(slotInfo(s.sunday_date, svc.id, role.name)).full_name }}
                    </span>
                  </div>
                  <div v-else class="text-[11px] text-ink-400 mt-0.5 italic">Unassigned</div>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Picker modal -->
    <div v-if="picker" class="fixed inset-0 z-50 flex items-end md:items-center justify-center p-0 md:p-4">
      <div class="absolute inset-0 bg-black/40" @click="picker = null; search = ''" />
      <div class="relative bg-white w-full md:max-w-md rounded-t-2xl md:rounded-2xl shadow-2xl overflow-hidden max-h-[80vh] flex flex-col">
        <div class="px-5 py-3 border-b border-ink-100 flex items-center justify-between">
          <div>
            <div class="text-[10px] font-black uppercase tracking-widest text-ink-400">{{ picker.role }}</div>
            <div class="text-xs text-ink-700">{{ picker.iso }} · {{ picker.service.toUpperCase() }}</div>
          </div>
          <button @click="picker = null; search = ''" class="text-ink-400 hover:text-ink-700">✕</button>
        </div>
        <div class="px-5 py-2 border-b border-ink-100">
          <input v-model="search" placeholder="Search team…"
                 class="w-full px-3 py-2 bg-ink-50 border border-ink-200 rounded-lg text-sm focus:bg-white focus:border-rose-500 outline-none" />
        </div>
        <div class="flex-1 overflow-y-auto divide-y divide-ink-100">
          <button v-for="m in pickerList" :key="m.name" @click="!m.excluded && pick(m.name, m.full_name)"
                  :disabled="m.excluded"
                  class="w-full px-4 py-2 flex items-center gap-3 hover:bg-rose-50 disabled:opacity-40 disabled:hover:bg-white">
            <MusicAvatar :id="m.name" :name="m.full_name" :size="28" />
            <div class="flex-1 text-left min-w-0">
              <div class="text-sm font-semibold text-ink-900 truncate">{{ m.full_name }}</div>
              <div class="text-[10px] text-ink-500">
                <span v-if="m.isPreferred" class="text-rose-700 font-bold">Preferred · </span>
                <span v-if="m.canRole">Knows role</span>
                <span v-else class="text-ink-400">No tag for this role</span>
                <span v-if="m.unavail" class="text-amber-700"> · Unavailable</span>
                <span v-if="m.excluded" class="text-ink-400"> · Already in service</span>
              </div>
            </div>
          </button>
        </div>
        <div class="px-5 py-3 border-t border-ink-100 flex justify-between">
          <button @click="clearSlot"
                  class="text-[11px] text-rose-700 hover:underline font-semibold">Clear slot</button>
          <button @click="picker = null; search = ''"
                  class="text-[11px] text-ink-500 hover:text-ink-700">Cancel</button>
        </div>
      </div>
    </div>
  </div>
</template>
