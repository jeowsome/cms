<script setup>
import { onMounted, ref, computed } from "vue";
import { useMusicTeamStore } from "@/stores/musicTeam";
import { useRealtime } from "@/composables/useRealtime";
import MusicHeader from "@/components/MusicHeader.vue";
import MusicAvatar from "@/components/MusicAvatar.vue";

const store = useMusicTeamStore();
const SERVICES = [
  { id: "am", label: "Morning", time: "9:00 AM", short: "AM", st: "Morning" },
  { id: "pm", label: "Evening", time: "6:00 PM", short: "PM", st: "Evening" },
];

const focusSunday = ref("");
const picker = ref(null); // { iso, service, role }

onMounted(async () => {
  await Promise.all([store.loadCatalog(), store.loadLineup(), store.loadUnavailability()]);
  focusSunday.value = store.computedSundays[0]?.iso || "";
});

useRealtime("music_team_event", async (msg) => {
  if (["assignment_set", "assignment_cleared", "decline_created", "decline_resolved", "schedule_published"].includes(msg.action)) {
    await store.loadLineup();
  }
  if (msg.action === "unavailability_added" || msg.action === "unavailability_removed") {
    await store.loadUnavailability();
  }
});

function declineCount(iso) {
  return store.openDeclines.filter(d => d.sunday_date === iso).length;
}

function fmtRelative(dt) {
  if (!dt) return "";
  const now = new Date();
  const then = new Date(dt);
  const diffH = (now - then) / 36e5;
  if (diffH < 1) return Math.max(0, Math.round(diffH * 60)) + "m ago";
  if (diffH < 24) return Math.round(diffH) + "h ago";
  return Math.round(diffH / 24) + "d ago";
}

function slotInfo(iso, svc, roleName) {
  return store.lineup?.[iso]?.[svc]?.[roleName] || null;
}

function memberFor(slot) {
  if (!slot?.member) return null;
  return store.memberById[slot.member] || { name: slot.member, full_name: slot.member_name };
}

function isUnavailable(memberId) {
  return memberId ? store.isUnavailable(memberId, focusSunday.value) : null;
}

function openDeclineFor(iso, svc, roleName, memberId) {
  return store.openDeclines.find(
    d => d.sunday_date === iso && d.service_time?.toLowerCase() === (svc === "am" ? "morning" : "evening")
      && d.music_role === roleName && d.member === memberId
  );
}

const previousMonth = () => {
  let i = store.MONTHS.indexOf(store.month);
  if (i <= 0) { store.month = "December"; store.year -= 1; }
  else store.month = store.MONTHS[i - 1];
  store.loadLineup().then(() => focusSunday.value = store.computedSundays[0]?.iso || "");
};
const nextMonth = () => {
  let i = store.MONTHS.indexOf(store.month);
  if (i >= 11) { store.month = "January"; store.year += 1; }
  else store.month = store.MONTHS[i + 1];
  store.loadLineup().then(() => focusSunday.value = store.computedSundays[0]?.iso || "");
};

async function publish() {
  if (!confirm("Publish the schedule? Members will be notified.")) return;
  await store.publishSchedule();
}

// --- Picker -----------------------------------------------------------------

const search = ref("");

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

const pickerCurrent = computed(() => {
  if (!picker.value) return null;
  return slotInfo(picker.value.iso, picker.value.service, picker.value.role)?.member || null;
});

async function pick(memberId, memberName) {
  const { iso, service, role } = picker.value;
  await store.setSlot(iso, service, role, memberId, memberName || "");
  picker.value = null;
  search.value = "";
}
</script>

<template>
  <div class="bg-white w-full min-h-full">
    <MusicHeader title="Music Team — Lineup"
                 :subtitle="`${store.month} ${store.year} · ${store.computedSundays.length} Sundays · Morning + Evening`">
      <button @click="previousMonth" class="px-3 py-1.5 text-xs font-medium text-ink-600 hover:bg-ink-50 rounded-lg">← Prev</button>
      <button @click="nextMonth" class="px-3 py-1.5 text-xs font-medium text-ink-600 hover:bg-ink-50 rounded-lg">Next →</button>
      <div class="w-px h-5 bg-ink-200" />
      <span v-if="store.scheduleStatus" class="text-[10px] font-bold uppercase tracking-widest px-2 py-1 rounded"
            :class="store.scheduleStatus === 'Published' ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'">
        {{ store.scheduleStatus }}
      </span>
      <button @click="publish" class="px-3.5 py-1.5 text-xs font-semibold bg-rose-600 text-white rounded-lg hover:bg-rose-700 shadow-sm flex items-center gap-1.5">
        <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5"/></svg>
        Publish &amp; notify
      </button>
    </MusicHeader>

    <!-- Sunday selector -->
    <div class="border-b border-ink-100 px-6 py-3 flex items-center gap-2 bg-ink-50/40 overflow-x-auto">
      <button v-for="s in store.computedSundays" :key="s.iso" @click="focusSunday = s.iso"
        class="px-3.5 py-2 rounded-xl text-xs font-semibold transition-colors flex items-center gap-2 shrink-0"
        :class="focusSunday === s.iso ? 'bg-rose-600 text-white shadow-sm' : 'bg-white border border-ink-200 text-ink-700 hover:border-rose-300'">
        <span>{{ new Date(s.iso).toLocaleDateString("en-US", { month: "short", day: "numeric" }) }}</span>
        <span class="text-[10px] font-medium" :class="focusSunday === s.iso ? 'text-rose-100' : 'text-ink-400'">{{ s.theme || '—' }}</span>
        <span v-if="declineCount(s.iso) > 0" class="text-[9px] font-bold rounded-full px-1.5 py-0.5"
              :class="focusSunday === s.iso ? 'bg-white/20 text-white' : 'bg-amber-100 text-amber-700'">
          {{ declineCount(s.iso) }}!
        </span>
      </button>
    </div>

    <!-- AM / PM grid -->
    <div v-if="focusSunday" class="grid grid-cols-1 md:grid-cols-2 gap-px bg-ink-100">
      <div v-for="svc in SERVICES" :key="svc.id" class="bg-white p-5">
        <div class="flex items-baseline justify-between mb-3">
          <div>
            <div class="text-[10px] font-black text-ink-400 uppercase tracking-widest">{{ svc.label }} Service</div>
            <div class="font-display font-bold text-2xl text-ink-900">{{ svc.time }}</div>
          </div>
          <div class="text-[10px] font-black text-rose-700 uppercase tracking-widest bg-rose-50 px-2 py-1 rounded-md">{{ svc.short }}</div>
        </div>

        <div class="space-y-1.5">
          <div v-for="r in store.roles" :key="r.name"
               @click="picker = { iso: focusSunday, service: svc.id, role: r.name }"
               class="group flex items-center gap-3 p-2 rounded-lg cursor-pointer transition-all"
               :class="(() => {
                 const slot = slotInfo(focusSunday, svc.id, r.name);
                 const m = memberFor(slot);
                 if (!m) return 'border border-dashed border-ink-200 hover:border-rose-400 hover:bg-rose-50/40';
                 if (openDeclineFor(focusSunday, svc.id, r.name, m.name)) return 'bg-amber-50 ring-1 ring-amber-300';
                 if (isUnavailable(m.name)) return 'bg-rose-50 ring-1 ring-rose-300';
                 return 'bg-ink-50/70 hover:bg-ink-100';
               })()">
            <div class="w-8 h-8 rounded-lg bg-brand-50 text-brand-700 flex items-center justify-center shrink-0">
              <span class="text-[10px] font-black uppercase">{{ r.tag_label.slice(0, 2) }}</span>
            </div>
            <div class="w-32 shrink-0">
              <div class="text-[11px] font-bold text-ink-900 truncate">{{ r.tag_label }}</div>
            </div>
            <template v-if="slotInfo(focusSunday, svc.id, r.name)?.member">
              <div class="flex items-center gap-2 flex-1 min-w-0">
                <MusicAvatar :id="slotInfo(focusSunday, svc.id, r.name).member"
                             :name="slotInfo(focusSunday, svc.id, r.name).member_name" :size="28" />
                <div class="min-w-0">
                  <div class="text-xs font-semibold text-ink-900 truncate">
                    {{ slotInfo(focusSunday, svc.id, r.name).member_name }}
                  </div>
                  <div v-if="openDeclineFor(focusSunday, svc.id, r.name, slotInfo(focusSunday, svc.id, r.name).member)"
                       class="text-[10px] font-medium text-amber-700 truncate">
                    ⚠ Declined: {{ openDeclineFor(focusSunday, svc.id, r.name, slotInfo(focusSunday, svc.id, r.name).member).reason }}
                  </div>
                  <div v-else-if="isUnavailable(slotInfo(focusSunday, svc.id, r.name).member)"
                       class="text-[10px] font-medium text-rose-700 truncate">
                    On leave: {{ isUnavailable(slotInfo(focusSunday, svc.id, r.name).member).reason }}
                  </div>
                  <div v-else class="text-[10px] text-ink-400">
                    {{ memberById[slotInfo(focusSunday, svc.id, r.name).member]?.preferred_role === r.name ? "Preferred role" : "Available" }}
                  </div>
                </div>
              </div>
            </template>
            <div v-else class="flex-1 text-[11px] italic text-ink-400">Click to assign…</div>
            <button class="opacity-0 group-hover:opacity-100 px-2 py-1 text-[10px] font-bold text-rose-700 bg-rose-50 rounded transition-opacity">
              {{ slotInfo(focusSunday, svc.id, r.name)?.member ? 'Change' : 'Assign' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Open declines for focused Sunday -->
    <div v-if="focusSunday && declineCount(focusSunday) > 0"
         class="border-t border-amber-200 bg-amber-50/60 px-6 py-3">
      <div class="flex items-center gap-2 mb-2">
        <div class="w-2 h-2 rounded-full bg-amber-500 pulse-ring" />
        <div class="text-[10px] font-black text-amber-800 uppercase tracking-widest">
          {{ declineCount(focusSunday) }} open decline{{ declineCount(focusSunday) > 1 ? 's' : '' }} · needs reassignment
        </div>
      </div>
      <div v-for="d in store.openDeclines.filter(x => x.sunday_date === focusSunday)" :key="d.name"
           class="flex items-center gap-3 p-2 bg-white rounded-lg border border-amber-200 mb-1.5 last:mb-0">
        <MusicAvatar :id="d.member" :name="d.member_name" :size="28" />
        <div class="flex-1 min-w-0">
          <div class="text-xs"><span class="font-bold text-ink-900">{{ d.member_name }}</span>
            can't make <span class="font-bold">{{ d.music_role }}</span> · {{ d.service_time }}</div>
          <div class="text-[10px] text-ink-500">"{{ d.reason }}" · declined {{ fmtRelative(d.declined_at) }}</div>
        </div>
        <button @click="store.resolveDecline(d.name)"
          class="px-2.5 py-1 text-[10px] font-bold text-rose-700 bg-rose-100 hover:bg-rose-200 rounded">
          Mark resolved
        </button>
      </div>
    </div>

    <!-- Picker modal -->
    <div v-if="picker" class="fixed inset-0 z-50 flex items-center justify-center p-4 anim-fadein">
      <div class="absolute inset-0 bg-black/40" @click="picker = null" />
      <div class="relative bg-white w-full max-w-lg rounded-2xl shadow-2xl overflow-hidden anim-pop">
        <div class="px-5 py-4 border-b border-ink-100 flex items-center justify-between">
          <div>
            <div class="text-[10px] font-black text-rose-700 uppercase tracking-widest">
              {{ new Date(picker.iso).toLocaleDateString("en-US", { month: "short", day: "numeric" }) }} ·
              {{ picker.service === "am" ? "Morning" : "Evening" }}
            </div>
            <h2 class="font-bold text-lg text-ink-900 mt-0.5">Assign {{ picker.role }}</h2>
          </div>
          <button v-if="pickerCurrent" @click="pick('', '')"
            class="text-xs font-bold text-rose-700 hover:underline">Clear slot</button>
        </div>
        <div class="px-5 py-3 border-b border-ink-100">
          <input v-model="search" autofocus placeholder="Search members…"
            class="w-full px-3.5 py-2 text-sm bg-ink-50 border border-ink-200 rounded-xl focus:bg-white focus:border-rose-500 focus:ring-2 focus:ring-rose-100 outline-none" />
        </div>
        <div class="max-h-96 overflow-auto">
          <button v-for="m in pickerList" :key="m.name"
            :disabled="m.excluded || !!m.unavail"
            @click="pick(m.name, m.full_name)"
            class="w-full flex items-center gap-3 px-5 py-2.5 border-b border-ink-50 text-left transition-colors"
            :class="[
              m.name === pickerCurrent ? 'bg-rose-50/50' : '',
              (m.excluded || m.unavail || !m.canRole) ? 'opacity-60' : 'hover:bg-rose-50/40',
              (m.excluded || m.unavail) ? 'cursor-not-allowed' : ''
            ]">
            <MusicAvatar :id="m.name" :name="m.full_name" :size="32" />
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2">
                <span class="text-sm font-semibold text-ink-900 truncate">{{ m.full_name }}</span>
                <span v-if="m.isPreferred" class="text-[9px] font-bold text-amber-700 bg-amber-100 px-1.5 py-0.5 rounded">★ Preferred</span>
                <span v-if="m.name === pickerCurrent" class="text-[9px] font-bold text-rose-700 bg-rose-100 px-1.5 py-0.5 rounded">Current</span>
              </div>
              <div class="text-[11px] text-ink-500 mt-0.5">
                <span v-if="!m.canRole" class="font-semibold text-ink-400">Not approved for {{ picker.role }}</span>
                <span v-else-if="m.excluded" class="font-semibold text-ink-500">Already on this service</span>
                <span v-else-if="m.unavail" class="font-semibold text-rose-700">On leave: {{ m.unavail.reason }}</span>
                <span v-else>Plays: {{ (m.roles || []).join(" · ") || '—' }}</span>
              </div>
            </div>
          </button>
          <div v-if="!pickerList.length" class="px-5 py-8 text-center text-sm text-ink-400">No members found.</div>
        </div>
      </div>
    </div>
  </div>
</template>
