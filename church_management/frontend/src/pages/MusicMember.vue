<script setup>
import { onMounted, ref, computed, reactive } from "vue";
import { call } from "@/composables/useFrappeApi";
import { useMusicTeamStore } from "@/stores/musicTeam";
import { useRealtime } from "@/composables/useRealtime";
import MusicAvatar from "@/components/MusicAvatar.vue";

const store = useMusicTeamStore();
const memberFilter = ref("");
const myAssignments = ref([]);
const declined = reactive({});
const showDecline = ref(null); // assignment row

onMounted(async () => {
  await store.loadCatalog();
  // pick the first member as default for demo; in production this would come
  // from the logged-in user's linked Church Member
  if (store.members.length && !memberFilter.value) {
    memberFilter.value = store.members[0].name;
  }
  await loadMine();
});

useRealtime("music_team_event", (msg) => {
  if (["assignment_set", "assignment_cleared", "schedule_published", "decline_resolved"].includes(msg.action)) {
    loadMine();
  }
});

async function loadMine() {
  if (!memberFilter.value) return;
  myAssignments.value = await call(
    "church_management.api.music_team.my_assignments",
    { member: memberFilter.value }
  ) || [];
}

const me = computed(() => store.memberById[memberFilter.value]);
const next = computed(() => myAssignments.value.find(a => !declined[a.row_name]));
const rest = computed(() => myAssignments.value.filter((a, i) => i > 0 && !declined[a.row_name]));

function fmt(iso) {
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}
function dayOfMonth(iso) { return new Date(iso).getDate(); }
function monthShort(iso) {
  return new Date(iso).toLocaleDateString("en-US", { month: "short" }).toUpperCase();
}

const declineForm = reactive({ reason: "" });

async function submitDecline() {
  const a = showDecline.value;
  if (!a) return;
  await call("church_management.api.music_team.decline_assignment", {
    sunday_date: a.sunday_date,
    service_time: a.service_time,
    music_role: a.music_role,
    member: a.member,
    reason: declineForm.reason || "",
  });
  declined[a.row_name] = true;
  showDecline.value = null;
  declineForm.reason = "";
}
</script>

<template>
  <div class="bg-[#f0eee9] w-full min-h-full">
    <div class="max-w-[440px] mx-auto bg-white min-h-screen shadow-2xl relative" style="border-radius: 0; overflow: hidden;">
      <!-- Member switcher (only in this multi-tenant demo view) -->
      <div class="px-5 pt-3 pb-2 bg-white border-b border-ink-100 flex items-center gap-2">
        <span class="text-[10px] font-black text-ink-400 uppercase tracking-widest">View as</span>
        <select v-model="memberFilter" @change="loadMine"
                class="flex-1 px-2 py-1 bg-ink-50 border border-ink-200 rounded text-xs focus:bg-white focus:border-rose-500 outline-none">
          <option v-for="m in store.members" :key="m.name" :value="m.name">{{ m.full_name }}</option>
        </select>
      </div>

      <!-- Hero -->
      <div class="px-6 pt-6 pb-6 bg-gradient-to-br from-rose-600 to-rose-800 text-white relative overflow-hidden"
           style="border-bottom-left-radius: 28px; border-bottom-right-radius: 28px;">
        <div class="absolute -top-10 -right-10 w-40 h-40 rounded-full bg-white/10" />
        <div class="absolute top-20 -left-8 w-24 h-24 rounded-full bg-white/5" />
        <div class="relative">
          <div class="flex items-center justify-between mb-6">
            <div>
              <p class="text-[10px] font-black uppercase tracking-[0.2em] text-rose-200">Music Team</p>
              <p class="font-display text-2xl font-bold mt-0.5">My Schedule</p>
            </div>
            <MusicAvatar v-if="me" :id="me.name" :name="me.full_name" :size="44" ring="ring-2 ring-white/30" />
          </div>

          <div v-if="next">
            <p class="text-[10px] font-black uppercase tracking-[0.2em] text-rose-200 mb-1">Next up</p>
            <p class="font-display text-3xl font-bold leading-tight">{{ fmt(next.sunday_date) }}</p>
            <p class="text-rose-100 text-sm mt-1">{{ next.service_time }} service</p>
            <div class="mt-4 inline-flex items-center gap-2 bg-white/20 backdrop-blur px-3 py-2 rounded-xl ring-1 ring-white/30">
              <span class="font-bold text-sm uppercase tracking-wider">{{ next.music_role }}</span>
            </div>
          </div>
          <div v-else class="text-rose-100 text-sm mt-2">You have no upcoming assignments.</div>
        </div>
      </div>

      <!-- Quick actions -->
      <div v-if="next" class="px-6 -mt-3 relative z-10">
        <div class="bg-white rounded-2xl shadow-lg ring-1 ring-ink-100 p-3 grid grid-cols-3 gap-2">
          <button class="flex flex-col items-center gap-0.5 p-2.5 rounded-xl hover:bg-ink-50">
            <span class="text-xl">🎵</span>
            <span class="text-[11px] font-bold text-ink-900">Songs</span>
            <span class="text-[9px] text-ink-400">View list</span>
          </button>
          <button class="flex flex-col items-center gap-0.5 p-2.5 rounded-xl hover:bg-ink-50">
            <span class="text-xl">📅</span>
            <span class="text-[11px] font-bold text-ink-900">Practice</span>
            <span class="text-[9px] text-ink-400">Schedule</span>
          </button>
          <button @click="showDecline = next"
                  class="flex flex-col items-center gap-0.5 p-2.5 rounded-xl hover:bg-rose-50">
            <span class="text-xl">🚫</span>
            <span class="text-[11px] font-bold text-rose-700">Can't make it</span>
            <span class="text-[9px] text-ink-400">Decline</span>
          </button>
        </div>
      </div>

      <!-- Upcoming list -->
      <div class="px-6 py-6">
        <div class="flex items-center justify-between mb-3">
          <h3 class="text-[10px] font-black uppercase tracking-widest text-ink-400">Upcoming · {{ rest.length }}</h3>
        </div>
        <div class="space-y-2">
          <div v-for="a in rest" :key="a.row_name"
               class="flex items-center gap-3 bg-ink-50/50 rounded-xl p-3 border border-ink-100">
            <div class="text-center shrink-0 w-12">
              <div class="text-[9px] font-black uppercase tracking-wider text-ink-400">{{ monthShort(a.sunday_date) }}</div>
              <div class="font-display text-2xl font-bold text-ink-900 leading-none">{{ dayOfMonth(a.sunday_date) }}</div>
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-1.5">
                <span class="text-xs font-semibold text-ink-900">{{ a.service_time }}</span>
              </div>
              <div class="text-[11px] text-ink-500 truncate">{{ a.month }} {{ a.year }}</div>
            </div>
            <div class="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-rose-50 text-rose-700 ring-1 ring-rose-200">
              <span class="text-[10px] font-bold uppercase tracking-wider">{{ a.music_role }}</span>
            </div>
          </div>
          <div v-if="!rest.length && !next" class="text-center text-ink-400 text-sm py-6">
            No assignments yet.
          </div>
        </div>
      </div>
    </div>

    <!-- Decline modal -->
    <div v-if="showDecline" class="fixed inset-0 z-50 flex items-center justify-center p-4 anim-fadein">
      <div class="absolute inset-0 bg-black/40" @click="showDecline = null" />
      <div class="relative bg-white w-full max-w-md rounded-2xl shadow-2xl overflow-hidden anim-pop">
        <div class="px-5 py-4 border-b border-ink-100">
          <h2 class="font-bold text-lg text-ink-900">Decline assignment</h2>
          <p class="text-xs text-ink-500 mt-1">{{ fmt(showDecline.sunday_date) }} · {{ showDecline.service_time }} · {{ showDecline.music_role }}</p>
        </div>
        <div class="p-5">
          <label class="text-[10px] font-black uppercase tracking-widest text-ink-400 block mb-1.5">Reason</label>
          <textarea v-model="declineForm.reason" rows="3"
                    class="w-full px-3 py-2 bg-ink-50 border border-ink-200 rounded-lg text-sm focus:bg-white focus:border-rose-500 outline-none"
                    placeholder="Let the worship leader know why…" />
        </div>
        <div class="px-5 py-4 border-t border-ink-100 flex justify-end gap-2">
          <button @click="showDecline = null" class="px-3 py-2 text-xs font-medium text-ink-600 hover:bg-ink-50 rounded-lg">Cancel</button>
          <button @click="submitDecline" class="px-4 py-2 text-xs font-bold bg-rose-600 text-white rounded-lg hover:bg-rose-700">Submit decline</button>
        </div>
      </div>
    </div>
  </div>
</template>
