<script setup>
import { onMounted, ref, computed, reactive } from "vue";
import { call } from "@/composables/useFrappeApi";
import { useSessionStore } from "@/stores/session";
import { useRealtime } from "@/composables/useRealtime";
import MusicAvatar from "@/components/MusicAvatar.vue";

const session = useSessionStore();

const myAssignments = ref([]);
const sentSwaps = ref([]);
const receivedSwaps = ref([]);
const declineModal = ref(null);   // assignment row
const swapModal = ref(null);      // assignment row
const planModal = ref(null);      // assignment row, sub-pane: 'songs' | 'practice'
const planTab = ref("songs");
const swapCandidates = ref([]);
const swapPicked = ref(null);
const swapReason = ref("");
const declineReason = ref("");
const busy = reactive({});
const message = ref("");

const myMember = computed(() => session.churchMember);

onMounted(async () => {
  if (!session.ready) await session.refresh();
  await loadMine();
  await loadSwaps();
});

useRealtime("music_team_event", async (msg) => {
  if (["assignment_set", "assignment_cleared", "schedule_published",
       "decline_resolved", "assignment_confirmed",
       "swap_requested", "swap_accepted", "swap_rejected", "swap_cancelled"].includes(msg.action)) {
    await Promise.all([loadMine(), loadSwaps()]);
  }
});

async function loadMine() {
  if (!myMember.value) { myAssignments.value = []; return; }
  myAssignments.value = await call(
    "church_management.api.music_team.my_assignments",
    { member: myMember.value }
  ) || [];
}

async function loadSwaps() {
  if (!myMember.value) { sentSwaps.value = []; receivedSwaps.value = []; return; }
  const [sent, received] = await Promise.all([
    call("church_management.api.music_team.list_swap_requests", { member: myMember.value, direction: "sent", status: "pending" }),
    call("church_management.api.music_team.list_swap_requests", { member: myMember.value, direction: "received", status: "pending" }),
  ]);
  sentSwaps.value = sent || [];
  receivedSwaps.value = received || [];
}

const confirmedAssignments = computed(() => myAssignments.value.filter(a => a.confirmed));
const pendingAssignments = computed(() => myAssignments.value.filter(a => !a.confirmed));
const next = computed(() => pendingAssignments.value[0] || confirmedAssignments.value[0] || null);
const upcomingRest = computed(() => myAssignments.value.filter((a, i) => a !== next.value));

function fmt(iso) {
  return new Date(iso).toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
}
function dayOfMonth(iso) { return new Date(iso).getDate(); }
function monthShort(iso) {
  return new Date(iso).toLocaleDateString("en-US", { month: "short" }).toUpperCase();
}
function fmtPracticeDt(iso) {
  if (!iso) return "";
  const d = new Date(iso.replace(" ", "T"));
  if (isNaN(d)) return iso;
  return d.toLocaleString("en-US", { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}
function openPlan(a, tab) {
  if (!a) return;
  planTab.value = tab || "songs";
  planModal.value = a;
}

function flash(text) {
  message.value = text;
  setTimeout(() => { message.value = ""; }, 1800);
}

async function confirmAssignment(a) {
  busy[a.row_name] = true;
  try {
    await call("church_management.api.music_team.confirm_assignment", { row_name: a.row_name });
    await loadMine();
    flash("Confirmed — see you there.");
  } catch (e) { flash(e.message || "Failed to confirm."); }
  finally { busy[a.row_name] = false; }
}

async function submitDecline() {
  const a = declineModal.value;
  if (!a) return;
  try {
    await call("church_management.api.music_team.decline_assignment", {
      sunday_date: a.sunday_date, service_time: a.service_time,
      music_role: a.music_role, member: a.member, reason: declineReason.value || "",
    });
    declineModal.value = null;
    declineReason.value = "";
    await loadMine();
    flash("Decline submitted.");
  } catch (e) { flash(e.message || "Failed to decline."); }
}

async function openSwap(a) {
  swapModal.value = a;
  swapPicked.value = null;
  swapReason.value = "";
  swapCandidates.value = [];
  try {
    swapCandidates.value = await call(
      "church_management.api.music_team.list_swap_candidates",
      {
        sunday_date: a.sunday_date, service_time: a.service_time,
        music_role: a.music_role, exclude_member: a.member,
      }
    ) || [];
  } catch (e) { flash(e.message || "Could not load candidates."); }
}

async function submitSwap() {
  const a = swapModal.value;
  if (!a || !swapPicked.value) return;
  try {
    await call("church_management.api.music_team.request_swap", {
      sunday_date: a.sunday_date, service_time: a.service_time,
      music_role: a.music_role, from_member: a.member,
      to_member: swapPicked.value, reason: swapReason.value || "",
    });
    swapModal.value = null;
    swapPicked.value = null;
    swapReason.value = "";
    await loadSwaps();
    flash("Swap request sent.");
  } catch (e) { flash(e.message || "Failed to request swap."); }
}

async function respondSwap(req, response) {
  try {
    await call("church_management.api.music_team.respond_swap", { name: req.name, response });
    await Promise.all([loadSwaps(), loadMine()]);
    flash(response === "accept" ? "Swap accepted." : "Swap declined.");
  } catch (e) { flash(e.message || "Failed to respond."); }
}

async function cancelSwap(req) {
  if (!window.confirm("Cancel this swap request?")) return;
  try {
    await call("church_management.api.music_team.cancel_swap", { name: req.name });
    await loadSwaps();
    flash("Swap cancelled.");
  } catch (e) { flash(e.message || "Failed to cancel."); }
}
</script>

<template>
  <div class="bg-[#f0eee9] w-full min-h-full">
    <div class="max-w-[440px] mx-auto bg-white min-h-screen shadow-2xl relative" style="border-radius: 0; overflow: hidden;">

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
            <MusicAvatar v-if="myMember" :id="myMember" :name="session.user" :size="44" ring="ring-2 ring-white/30" />
          </div>

          <div v-if="next">
            <p class="text-[10px] font-black uppercase tracking-[0.2em] text-rose-200 mb-1">
              {{ next.confirmed ? "Confirmed · Next" : "Next up" }}
            </p>
            <p class="font-display text-3xl font-bold leading-tight">{{ fmt(next.sunday_date) }}</p>
            <p class="text-rose-100 text-sm mt-1">{{ next.service_time }} service</p>
            <div class="mt-4 inline-flex items-center gap-2 bg-white/20 backdrop-blur px-3 py-2 rounded-xl ring-1 ring-white/30">
              <span class="font-bold text-sm uppercase tracking-wider">{{ next.music_role }}</span>
              <span v-if="next.confirmed" class="text-[10px] font-black bg-emerald-500/90 text-white rounded-full px-2 py-0.5">CONFIRMED</span>
            </div>
          </div>
          <div v-else-if="!myMember" class="text-rose-100 text-sm mt-2">
            Your account isn't linked to a Church Member yet — ask the leader to link you.
          </div>
          <div v-else class="text-rose-100 text-sm mt-2">You have no upcoming assignments.</div>
        </div>
      </div>

      <!-- Quick actions -->
      <div v-if="next" class="px-6 -mt-3 relative z-10">
        <div class="bg-white rounded-2xl shadow-lg ring-1 ring-ink-100 p-3 grid grid-cols-3 gap-2">
          <button @click="confirmAssignment(next)" :disabled="busy[next.row_name] || next.confirmed"
                  class="flex flex-col items-center gap-0.5 p-2.5 rounded-xl transition disabled:opacity-50"
                  :class="next.confirmed ? 'bg-emerald-50 text-emerald-700 cursor-default' : 'hover:bg-emerald-50 text-emerald-700'">
            <span class="text-xl">✅</span>
            <span class="text-[11px] font-bold">{{ next.confirmed ? "Confirmed" : "I'm in" }}</span>
            <span class="text-[9px] text-ink-400">Confirm</span>
          </button>
          <button @click="openSwap(next)"
                  class="flex flex-col items-center gap-0.5 p-2.5 rounded-xl hover:bg-amber-50 text-amber-700">
            <span class="text-xl">🔄</span>
            <span class="text-[11px] font-bold">Swap</span>
            <span class="text-[9px] text-ink-400">Find replacement</span>
          </button>
          <button @click="declineModal = next"
                  class="flex flex-col items-center gap-0.5 p-2.5 rounded-xl hover:bg-rose-50 text-rose-700">
            <span class="text-xl">🚫</span>
            <span class="text-[11px] font-bold">Decline</span>
            <span class="text-[9px] text-ink-400">Can't make it</span>
          </button>
        </div>

        <!-- Worship plan peek (songs + practice) -->
        <div v-if="next.songs || next.practice_datetime || next.worship_leader_notes"
             class="bg-white rounded-2xl shadow ring-1 ring-ink-100 mt-2 p-3 grid grid-cols-2 gap-2">
          <button @click="openPlan(next, 'songs')"
                  class="flex items-center gap-2 p-2 rounded-xl hover:bg-rose-50 text-left disabled:opacity-50"
                  :disabled="!next.songs">
            <span class="text-xl">🎵</span>
            <div class="min-w-0 flex-1">
              <div class="text-[11px] font-bold text-ink-900">Songs</div>
              <div class="text-[10px] text-ink-500 truncate">
                {{ next.songs ? (next.songs.split('\n').filter(s => s.trim()).length + ' song(s)') : 'No songs yet' }}
              </div>
            </div>
          </button>
          <button @click="openPlan(next, 'practice')"
                  class="flex items-center gap-2 p-2 rounded-xl hover:bg-rose-50 text-left disabled:opacity-50"
                  :disabled="!next.practice_datetime">
            <span class="text-xl">📅</span>
            <div class="min-w-0 flex-1">
              <div class="text-[11px] font-bold text-ink-900">Practice</div>
              <div class="text-[10px] text-ink-500 truncate">
                {{ next.practice_datetime ? fmtPracticeDt(next.practice_datetime) : 'Not scheduled' }}
              </div>
            </div>
          </button>
        </div>
      </div>

      <!-- Toast -->
      <div v-if="message" class="px-6 mt-3">
        <div class="text-[12px] font-medium px-3 py-2 rounded-lg bg-ink-900 text-white text-center">{{ message }}</div>
      </div>

      <!-- Pending swap requests received -->
      <div v-if="receivedSwaps.length" class="px-6 pt-5">
        <h3 class="text-[10px] font-black uppercase tracking-widest text-amber-700 mb-2">Swap requests for you</h3>
        <div class="space-y-2">
          <div v-for="r in receivedSwaps" :key="r.name"
               class="bg-amber-50 ring-1 ring-amber-200 rounded-xl p-3">
            <div class="flex items-start gap-3">
              <div class="text-center w-12 shrink-0">
                <div class="text-[9px] font-black uppercase tracking-wider text-amber-700">{{ monthShort(r.sunday_date) }}</div>
                <div class="font-display text-2xl font-bold text-ink-900 leading-none">{{ dayOfMonth(r.sunday_date) }}</div>
              </div>
              <div class="flex-1 min-w-0">
                <div class="text-sm font-semibold text-ink-900 truncate">{{ r.from_member_name }} wants to swap</div>
                <div class="text-[11px] text-ink-700">{{ r.service_time }} · <span class="font-bold">{{ r.music_role }}</span></div>
                <div v-if="r.reason" class="text-[11px] text-ink-500 mt-1 italic">"{{ r.reason }}"</div>
                <div class="flex gap-2 mt-2">
                  <button @click="respondSwap(r, 'accept')"
                          class="px-3 py-1 text-[11px] font-bold bg-emerald-600 text-white rounded-lg hover:bg-emerald-700">Accept</button>
                  <button @click="respondSwap(r, 'reject')"
                          class="px-3 py-1 text-[11px] font-bold bg-white text-ink-700 ring-1 ring-ink-200 rounded-lg hover:bg-ink-50">Decline</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Pending swap requests sent -->
      <div v-if="sentSwaps.length" class="px-6 pt-4">
        <h3 class="text-[10px] font-black uppercase tracking-widest text-ink-400 mb-2">Your pending swap requests</h3>
        <div class="space-y-2">
          <div v-for="r in sentSwaps" :key="r.name"
               class="flex items-center gap-3 bg-ink-50/50 rounded-xl p-3 border border-ink-100">
            <div class="text-center w-12 shrink-0">
              <div class="text-[9px] font-black uppercase tracking-wider text-ink-400">{{ monthShort(r.sunday_date) }}</div>
              <div class="font-display text-2xl font-bold text-ink-900 leading-none">{{ dayOfMonth(r.sunday_date) }}</div>
            </div>
            <div class="flex-1 min-w-0">
              <div class="text-xs font-semibold text-ink-900 truncate">→ {{ r.to_member_name }}</div>
              <div class="text-[11px] text-ink-500">{{ r.service_time }} · {{ r.music_role }}</div>
            </div>
            <button @click="cancelSwap(r)" class="text-[11px] text-rose-700 hover:underline font-semibold">Cancel</button>
          </div>
        </div>
      </div>

      <!-- Upcoming list -->
      <div class="px-6 py-6">
        <div class="flex items-center justify-between mb-3">
          <h3 class="text-[10px] font-black uppercase tracking-widest text-ink-400">Upcoming · {{ upcomingRest.length }}</h3>
        </div>
        <div class="space-y-2">
          <div v-for="a in upcomingRest" :key="a.row_name"
               class="flex items-center gap-3 bg-ink-50/50 rounded-xl p-3 border border-ink-100">
            <div class="text-center shrink-0 w-12">
              <div class="text-[9px] font-black uppercase tracking-wider text-ink-400">{{ monthShort(a.sunday_date) }}</div>
              <div class="font-display text-2xl font-bold text-ink-900 leading-none">{{ dayOfMonth(a.sunday_date) }}</div>
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-1.5">
                <span class="text-xs font-semibold text-ink-900">{{ a.service_time }}</span>
                <span v-if="a.confirmed" class="text-[9px] font-black bg-emerald-100 text-emerald-700 rounded-full px-1.5 py-0.5">CONFIRMED</span>
              </div>
              <div class="text-[11px] text-ink-500 truncate">{{ a.month }} {{ a.year }} · <span class="font-bold">{{ a.music_role }}</span></div>
            </div>
            <div class="flex gap-1">
              <button v-if="!a.confirmed" @click="confirmAssignment(a)" :disabled="busy[a.row_name]"
                      class="px-2 py-1 text-[10px] font-bold bg-emerald-600 text-white rounded hover:bg-emerald-700 disabled:opacity-50">✓</button>
              <button @click="openSwap(a)"
                      class="px-2 py-1 text-[10px] font-bold bg-amber-100 text-amber-700 rounded hover:bg-amber-200">↔</button>
              <button @click="declineModal = a"
                      class="px-2 py-1 text-[10px] font-bold bg-rose-100 text-rose-700 rounded hover:bg-rose-200">✕</button>
            </div>
          </div>
          <div v-if="!upcomingRest.length && !next" class="text-center text-ink-400 text-sm py-6">
            No assignments yet.
          </div>
        </div>
      </div>
    </div>

    <!-- Decline modal -->
    <div v-if="declineModal" class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-black/40" @click="declineModal = null" />
      <div class="relative bg-white w-full max-w-md rounded-2xl shadow-2xl overflow-hidden">
        <div class="px-5 py-4 border-b border-ink-100">
          <h2 class="font-bold text-lg text-ink-900">Decline assignment</h2>
          <p class="text-xs text-ink-500 mt-1">{{ fmt(declineModal.sunday_date) }} · {{ declineModal.service_time }} · {{ declineModal.music_role }}</p>
        </div>
        <div class="p-5">
          <label class="text-[10px] font-black uppercase tracking-widest text-ink-400 block mb-1.5">Reason</label>
          <textarea v-model="declineReason" rows="3"
                    class="w-full px-3 py-2 bg-ink-50 border border-ink-200 rounded-lg text-sm focus:bg-white focus:border-rose-500 outline-none"
                    placeholder="Let the worship leader know why…" />
          <p class="text-[11px] text-ink-500 mt-2">
            Tip: prefer the <button class="text-amber-700 font-bold underline" @click="openSwap(declineModal); declineModal = null;">Swap</button> flow if you can find your own replacement.
          </p>
        </div>
        <div class="px-5 py-4 border-t border-ink-100 flex justify-end gap-2">
          <button @click="declineModal = null" class="px-3 py-2 text-xs font-medium text-ink-600 hover:bg-ink-50 rounded-lg">Cancel</button>
          <button @click="submitDecline" class="px-4 py-2 text-xs font-bold bg-rose-600 text-white rounded-lg hover:bg-rose-700">Submit decline</button>
        </div>
      </div>
    </div>

    <!-- Worship plan modal (read-only for member) -->
    <div v-if="planModal" class="fixed inset-0 z-50 flex items-end md:items-center justify-center p-0 md:p-4">
      <div class="absolute inset-0 bg-black/40" @click="planModal = null" />
      <div class="relative bg-white w-full md:max-w-md rounded-t-2xl md:rounded-2xl shadow-2xl overflow-hidden max-h-[85vh] flex flex-col">
        <div class="px-5 py-4 border-b border-ink-100">
          <div class="text-[10px] font-black uppercase tracking-widest text-rose-700">Worship plan</div>
          <h2 class="font-bold text-lg text-ink-900">{{ fmt(planModal.sunday_date) }} · {{ planModal.service_time }}</h2>
          <div v-if="planModal.theme || planModal.sermon_title" class="text-[11px] text-ink-500 mt-1">
            <span v-if="planModal.theme">{{ planModal.theme }}</span>
            <span v-if="planModal.theme && planModal.sermon_title"> · </span>
            <span v-if="planModal.sermon_title">{{ planModal.sermon_title }}</span>
          </div>
        </div>
        <div class="px-5 pt-3 border-b border-ink-100 flex gap-1">
          <button @click="planTab = 'songs'"
                  class="px-3 py-1.5 text-[11px] font-bold border-b-2 transition-colors"
                  :class="planTab === 'songs' ? 'text-rose-700 border-rose-500' : 'text-ink-500 border-transparent hover:text-ink-700'">
            Songs
          </button>
          <button @click="planTab = 'practice'"
                  class="px-3 py-1.5 text-[11px] font-bold border-b-2 transition-colors"
                  :class="planTab === 'practice' ? 'text-rose-700 border-rose-500' : 'text-ink-500 border-transparent hover:text-ink-700'">
            Practice
          </button>
          <button v-if="planModal.worship_leader_notes" @click="planTab = 'notes'"
                  class="px-3 py-1.5 text-[11px] font-bold border-b-2 transition-colors"
                  :class="planTab === 'notes' ? 'text-rose-700 border-rose-500' : 'text-ink-500 border-transparent hover:text-ink-700'">
            Notes
          </button>
        </div>
        <div class="flex-1 overflow-y-auto p-5">
          <div v-if="planTab === 'songs'">
            <div v-if="planModal.songs" class="space-y-1">
              <div v-for="(line, i) in planModal.songs.split('\n').filter(s => s.trim())" :key="i"
                   class="flex items-start gap-2 text-sm text-ink-900">
                <span class="text-[10px] font-black text-ink-400 w-5 mt-0.5">{{ i + 1 }}.</span>
                <span class="flex-1">{{ line }}</span>
              </div>
            </div>
            <div v-else class="text-[12px] text-ink-400 italic">Worship Leader hasn't posted songs yet.</div>
          </div>

          <div v-else-if="planTab === 'practice'" class="space-y-3">
            <div>
              <div class="text-[10px] font-black uppercase tracking-widest text-ink-400">When</div>
              <div class="text-sm text-ink-900 mt-0.5">
                {{ planModal.practice_datetime ? fmtPracticeDt(planModal.practice_datetime) : "Not scheduled yet." }}
              </div>
            </div>
            <div>
              <div class="text-[10px] font-black uppercase tracking-widest text-ink-400">Where</div>
              <div class="text-sm text-ink-900 mt-0.5">
                {{ planModal.practice_location || "—" }}
              </div>
            </div>
          </div>

          <div v-else-if="planTab === 'notes'" class="text-sm text-ink-900 whitespace-pre-line">
            {{ planModal.worship_leader_notes }}
          </div>
        </div>
        <div class="px-5 py-3 border-t border-ink-100 flex justify-end">
          <button @click="planModal = null" class="px-3 py-2 text-xs font-medium text-ink-600 hover:bg-ink-50 rounded-lg">Close</button>
        </div>
      </div>
    </div>

    <!-- Swap modal -->
    <div v-if="swapModal" class="fixed inset-0 z-50 flex items-end md:items-center justify-center p-0 md:p-4">
      <div class="absolute inset-0 bg-black/40" @click="swapModal = null" />
      <div class="relative bg-white w-full md:max-w-md rounded-t-2xl md:rounded-2xl shadow-2xl overflow-hidden max-h-[80vh] flex flex-col">
        <div class="px-5 py-4 border-b border-ink-100">
          <h2 class="font-bold text-lg text-ink-900">Request swap</h2>
          <p class="text-xs text-ink-500 mt-1">{{ fmt(swapModal.sunday_date) }} · {{ swapModal.service_time }} · {{ swapModal.music_role }}</p>
        </div>
        <div class="flex-1 overflow-y-auto">
          <div class="px-5 pt-4">
            <label class="text-[10px] font-black uppercase tracking-widest text-ink-400 block mb-1.5">Pick replacement</label>
            <div v-if="!swapCandidates.length" class="text-[12px] text-ink-400 italic">No eligible team members for this slot.</div>
            <div v-else class="space-y-1">
              <button v-for="m in swapCandidates" :key="m.name" @click="swapPicked = m.name"
                      class="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left transition"
                      :class="swapPicked === m.name ? 'bg-amber-50 ring-1 ring-amber-300' : 'hover:bg-ink-50'">
                <MusicAvatar :id="m.name" :name="m.full_name" :size="28" />
                <div class="flex-1 min-w-0">
                  <div class="text-sm font-semibold text-ink-900 truncate">{{ m.full_name }}</div>
                  <div class="text-[10px] text-ink-500">Knows {{ swapModal.music_role }}</div>
                </div>
                <span v-if="swapPicked === m.name" class="text-amber-700 text-sm">●</span>
              </button>
            </div>
          </div>
          <div class="px-5 pt-4 pb-2">
            <label class="text-[10px] font-black uppercase tracking-widest text-ink-400 block mb-1.5">Reason (optional)</label>
            <textarea v-model="swapReason" rows="2"
                      class="w-full px-3 py-2 bg-ink-50 border border-ink-200 rounded-lg text-sm focus:bg-white focus:border-amber-500 outline-none"
                      placeholder="So they know why you're asking…" />
          </div>
        </div>
        <div class="px-5 py-4 border-t border-ink-100 flex justify-end gap-2">
          <button @click="swapModal = null" class="px-3 py-2 text-xs font-medium text-ink-600 hover:bg-ink-50 rounded-lg">Cancel</button>
          <button @click="submitSwap" :disabled="!swapPicked"
                  class="px-4 py-2 text-xs font-bold bg-amber-600 text-white rounded-lg hover:bg-amber-700 disabled:opacity-50">Send swap request</button>
        </div>
      </div>
    </div>
  </div>
</template>
