<script setup>
import { onMounted, ref, computed, reactive } from "vue";
import { useMusicTeamStore } from "@/stores/musicTeam";
import { useRealtime } from "@/composables/useRealtime";
import MusicHeader from "@/components/MusicHeader.vue";
import MusicAvatar from "@/components/MusicAvatar.vue";

const store = useMusicTeamStore();
const tab = ref("windows");
const showAdd = ref(false);

const KIND_STYLES = {
  vacation:  { bg: "bg-brand-50",  text: "text-brand-700",  ring: "ring-brand-200",  label: "Vacation" },
  medical:   { bg: "bg-amber-50",  text: "text-amber-700",  ring: "ring-amber-200",  label: "Medical" },
  suspended: { bg: "bg-rose-50",   text: "text-rose-700",   ring: "ring-rose-200",   label: "Suspended" },
  event:     { bg: "bg-violet-50", text: "text-violet-700", ring: "ring-violet-200", label: "Personal event" },
};

const form = reactive({ member: "", from_date: "", to_date: "", kind: "vacation", reason: "" });

onMounted(() => Promise.all([store.loadCatalog(), store.loadUnavailability(), store.loadDeclines()]));
useRealtime("music_team_event", (msg) => {
  if (msg.action.startsWith("unavailability_") || msg.action.startsWith("decline_")) {
    store.loadUnavailability(); store.loadDeclines();
  }
});

const byMember = computed(() => {
  const out = {};
  for (const w of store.unavailability) {
    (out[w.member] = out[w.member] || []).push(w);
  }
  return out;
});

const timeline = computed(() => {
  if (!store.unavailability.length) return null;
  const today = new Date();
  const start = new Date(today);
  start.setDate(start.getDate() - 14);
  const end = new Date(today);
  end.setDate(end.getDate() + 45);
  const total = Math.round((end - start) / 86400000) + 1;
  return { start, end, total };
});

function pct(iso) {
  if (!timeline.value) return 0;
  const { start, total } = timeline.value;
  return Math.max(0, Math.min(100, ((new Date(iso) - start) / 86400000) / total * 100));
}

function fmtRelative(dt) {
  if (!dt) return "";
  const diffH = (new Date() - new Date(dt)) / 36e5;
  if (diffH < 1) return Math.max(0, Math.round(diffH * 60)) + "m ago";
  if (diffH < 24) return Math.round(diffH) + "h ago";
  return Math.round(diffH / 24) + "d ago";
}

async function submit() {
  if (!form.member || !form.from_date || !form.to_date) return;
  await store.addUnavailability({ ...form });
  showAdd.value = false;
  Object.assign(form, { member: "", from_date: "", to_date: "", kind: "vacation", reason: "" });
}
</script>

<template>
  <div class="bg-white w-full min-h-full">
    <MusicHeader title="Unavailability &amp; Declines"
                 subtitle="Members on leave, suspended, or who declined a specific assignment.">
      <button @click="showAdd = true"
        class="px-3.5 py-1.5 text-xs font-semibold bg-rose-600 text-white rounded-lg hover:bg-rose-700 shadow-sm">
        + Mark unavailable
      </button>
    </MusicHeader>

    <div class="border-b border-ink-100 px-6 flex items-center gap-1 bg-white sticky top-[73px] z-[5]">
      <button v-for="t in [{id:'windows',label:'Unavailability windows', count: store.unavailability.length},
                            {id:'declines',label:'Decline log', count: store.declines.length}]"
              :key="t.id" @click="tab = t.id"
              class="px-4 py-3 text-xs font-semibold border-b-2 transition-colors flex items-center gap-2"
              :class="tab === t.id ? 'text-rose-700 border-rose-500' : 'text-ink-500 border-transparent hover:text-ink-700'">
        <span>{{ t.label }}</span>
        <span class="text-[10px] font-bold rounded-full px-1.5 py-0.5"
              :class="tab === t.id ? 'bg-rose-50 text-rose-700' : 'bg-ink-100 text-ink-500'">
          {{ t.count }}
        </span>
      </button>
    </div>

    <!-- Windows -->
    <div v-if="tab === 'windows'" class="p-6">
      <div v-if="!store.unavailability.length" class="text-center text-ink-400 py-12 text-sm">
        No unavailability windows logged.
      </div>
      <div v-else class="bg-white border border-ink-100 rounded-xl overflow-hidden">
        <div v-for="(windows, mid) in byMember" :key="mid"
             class="grid hover:bg-ink-50/30 border-b border-ink-100 last:border-b-0"
             :style="{ gridTemplateColumns: '200px 1fr' }">
          <div class="px-4 py-3 flex items-center gap-2.5 border-r border-ink-100">
            <MusicAvatar :id="mid" :name="windows[0].member_name" :size="28" />
            <div class="min-w-0">
              <div class="text-xs font-semibold text-ink-900 truncate">{{ windows[0].member_name }}</div>
              <div class="text-[10px] text-ink-400">{{ windows.length }} window{{ windows.length > 1 ? 's' : '' }}</div>
            </div>
          </div>
          <div class="relative h-14">
            <div v-for="w in windows" :key="w.name"
                 class="absolute top-2 bottom-2 ring-1 rounded-lg flex items-center px-2 overflow-hidden"
                 :class="[KIND_STYLES[w.kind]?.bg, KIND_STYLES[w.kind]?.ring]"
                 :style="{ left: pct(w.from_date) + '%', width: Math.max(2, pct(w.to_date) - pct(w.from_date) + 1) + '%' }">
              <div class="min-w-0">
                <div class="text-[10px] font-bold truncate" :class="KIND_STYLES[w.kind]?.text">
                  {{ KIND_STYLES[w.kind]?.label }}
                </div>
                <div class="text-[9px] text-ink-500 truncate">{{ w.reason }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Declines -->
    <div v-else class="p-6">
      <table class="w-full bg-white border border-ink-100 rounded-xl overflow-hidden">
        <thead>
          <tr class="bg-ink-50/50 border-b border-ink-100 text-[10px] font-black text-ink-400 uppercase tracking-widest">
            <th class="px-4 py-3 text-left">Member</th>
            <th class="px-4 py-3 text-left">Service</th>
            <th class="px-4 py-3 text-left">Role</th>
            <th class="px-4 py-3 text-left">Reason</th>
            <th class="px-4 py-3 text-left">Declined</th>
            <th class="px-4 py-3 text-left">Status</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-ink-100">
          <tr v-for="d in store.declines" :key="d.name" class="hover:bg-ink-50/30">
            <td class="px-4 py-3">
              <div class="flex items-center gap-2">
                <MusicAvatar :id="d.member" :name="d.member_name" :size="28" />
                <span class="text-xs font-semibold text-ink-900">{{ d.member_name }}</span>
              </div>
            </td>
            <td class="px-4 py-3 text-xs text-ink-700">
              <div class="font-semibold">{{ new Date(d.sunday_date).toLocaleDateString("en-US", { month: "short", day: "numeric" }) }}</div>
              <div class="text-[10px] text-ink-400 uppercase tracking-wider">{{ d.service_time }}</div>
            </td>
            <td class="px-4 py-3">
              <span class="text-[10px] font-bold uppercase tracking-widest text-ink-700 bg-ink-100 px-2 py-1 rounded">{{ d.music_role }}</span>
            </td>
            <td class="px-4 py-3 text-xs text-ink-700 italic max-w-xs truncate">"{{ d.reason }}"</td>
            <td class="px-4 py-3 text-[11px] text-ink-500 tabular">{{ fmtRelative(d.declined_at) }}</td>
            <td class="px-4 py-3">
              <span v-if="d.status === 'open'"
                    class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 text-[10px] font-semibold ring-1 ring-amber-200">
                <span class="w-1.5 h-1.5 rounded-full bg-amber-500 pulse-ring" />Needs reassignment
              </span>
              <span v-else-if="d.status === 'filled'"
                    class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 text-[10px] font-semibold ring-1 ring-emerald-200">
                ✓ Filled
              </span>
              <span v-else
                    class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-ink-100 text-ink-500 text-[10px] font-semibold">
                Cancelled
              </span>
            </td>
          </tr>
          <tr v-if="!store.declines.length">
            <td colspan="6" class="text-center text-ink-400 py-8 text-sm">No declines yet.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Add modal -->
    <div v-if="showAdd" class="fixed inset-0 z-50 flex items-center justify-center p-4 anim-fadein">
      <div class="absolute inset-0 bg-black/40" @click="showAdd = false" />
      <div class="relative bg-white w-full max-w-md rounded-2xl shadow-2xl overflow-hidden anim-pop">
        <div class="px-5 py-4 border-b border-ink-100">
          <h2 class="font-bold text-lg text-ink-900">Mark unavailable</h2>
        </div>
        <div class="p-5 space-y-3">
          <div>
            <label class="text-[10px] font-black uppercase tracking-widest text-ink-400 block mb-1.5">Member</label>
            <select v-model="form.member" class="w-full px-3 py-2 bg-ink-50 border border-ink-200 rounded-lg text-sm focus:bg-white focus:border-rose-500 outline-none">
              <option value="">Select member…</option>
              <option v-for="m in store.members" :key="m.name" :value="m.name">{{ m.full_name }}</option>
            </select>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="text-[10px] font-black uppercase tracking-widest text-ink-400 block mb-1.5">From</label>
              <input v-model="form.from_date" type="date" class="w-full px-3 py-2 bg-ink-50 border border-ink-200 rounded-lg text-sm focus:bg-white focus:border-rose-500 outline-none" />
            </div>
            <div>
              <label class="text-[10px] font-black uppercase tracking-widest text-ink-400 block mb-1.5">To</label>
              <input v-model="form.to_date" type="date" class="w-full px-3 py-2 bg-ink-50 border border-ink-200 rounded-lg text-sm focus:bg-white focus:border-rose-500 outline-none" />
            </div>
          </div>
          <div>
            <label class="text-[10px] font-black uppercase tracking-widest text-ink-400 block mb-1.5">Kind</label>
            <select v-model="form.kind" class="w-full px-3 py-2 bg-ink-50 border border-ink-200 rounded-lg text-sm focus:bg-white focus:border-rose-500 outline-none">
              <option value="vacation">Vacation</option>
              <option value="medical">Medical</option>
              <option value="suspended">Suspended</option>
              <option value="event">Personal event</option>
            </select>
          </div>
          <div>
            <label class="text-[10px] font-black uppercase tracking-widest text-ink-400 block mb-1.5">Reason</label>
            <textarea v-model="form.reason" rows="2" class="w-full px-3 py-2 bg-ink-50 border border-ink-200 rounded-lg text-sm focus:bg-white focus:border-rose-500 outline-none" />
          </div>
        </div>
        <div class="px-5 py-4 border-t border-ink-100 flex justify-end gap-2">
          <button @click="showAdd = false" class="px-3 py-2 text-xs font-medium text-ink-600 hover:bg-ink-50 rounded-lg">Cancel</button>
          <button @click="submit" class="px-4 py-2 text-xs font-bold bg-rose-600 text-white rounded-lg hover:bg-rose-700">Save</button>
        </div>
      </div>
    </div>
  </div>
</template>
