<script setup>
import { onMounted, ref, computed, reactive } from "vue";
import { useMusicTeamStore } from "@/stores/musicTeam";
import { useRealtime } from "@/composables/useRealtime";
import MusicHeader from "@/components/MusicHeader.vue";
import MusicAvatar from "@/components/MusicAvatar.vue";

const store = useMusicTeamStore();

const TYPES = [
  { id: "songs",    label: "Song list",       icon: "🎵" },
  { id: "practice", label: "Practice notice", icon: "📅" },
  { id: "swap",     label: "Swap request",    icon: "🔄" },
  { id: "general",  label: "General memo",    icon: "📣" },
];

const form = reactive({
  notification_type: "songs",
  sunday_date: "",
  service_time: "Morning",
  title: "",
  body: "",
  send_sms: true,
});

const sending = ref(false);

onMounted(async () => {
  await Promise.all([store.loadCatalog(), store.loadLineup(), store.loadNotifications()]);
  if (!form.sunday_date && store.computedSundays.length) {
    form.sunday_date = store.computedSundays[0].iso;
  }
});

useRealtime("music_team_notification", () => store.loadNotifications());

const recipients = computed(() => {
  const svc = form.service_time === "Morning" ? "am" : "pm";
  const map = store.lineup?.[form.sunday_date]?.[svc] || {};
  return Object.entries(map)
    .filter(([_, slot]) => slot.member)
    .map(([role, slot]) => ({
      member: slot.member,
      member_name: slot.member_name,
      music_role: role,
    }));
});

function fmtRelative(dt) {
  if (!dt) return "";
  const diffH = (new Date() - new Date(dt)) / 36e5;
  if (diffH < 1) return Math.max(0, Math.round(diffH * 60)) + "m ago";
  if (diffH < 24) return Math.round(diffH) + "h ago";
  return Math.round(diffH / 24) + "d ago";
}

async function send() {
  if (!form.title || !form.body) return;
  sending.value = true;
  try {
    await store.sendNotification({ ...form, recipients: recipients.value });
    form.title = ""; form.body = "";
  } finally {
    sending.value = false;
  }
}
</script>

<template>
  <div class="bg-[#f0eee9] w-full min-h-full">
    <MusicHeader title="Send to team"
                 subtitle="Compose songs, practice info, or swap requests. Goes to assigned members for the selected service.">
    </MusicHeader>

    <div class="grid grid-cols-12 gap-6 p-6">
      <!-- Composer -->
      <div class="col-span-12 lg:col-span-7 bg-white rounded-xl border border-ink-100 overflow-hidden">
        <div class="px-5 py-4 border-b border-ink-100">
          <div class="text-[10px] font-black uppercase tracking-widest text-ink-400 mb-2">Notification type</div>
          <div class="flex gap-2 flex-wrap">
            <button v-for="t in TYPES" :key="t.id"
                    @click="form.notification_type = t.id"
                    class="flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold transition-colors"
                    :class="form.notification_type === t.id
                            ? 'bg-rose-50 text-rose-700 ring-1 ring-rose-300'
                            : 'bg-ink-50 text-ink-600 hover:bg-ink-100'">
              <span class="text-base">{{ t.icon }}</span>{{ t.label }}
            </button>
          </div>
        </div>

        <div class="p-5 space-y-4">
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="text-[10px] font-black uppercase tracking-widest text-ink-400 block mb-1.5">Sunday</label>
              <select v-model="form.sunday_date"
                      class="w-full px-3 py-2 bg-ink-50 border border-ink-200 rounded-lg text-sm font-semibold focus:bg-white focus:border-rose-500 outline-none">
                <option v-for="s in store.computedSundays" :key="s.iso" :value="s.iso">
                  {{ new Date(s.iso).toLocaleDateString("en-US", { month: "short", day: "numeric" }) }}{{ s.theme ? ' — ' + s.theme : '' }}
                </option>
              </select>
            </div>
            <div>
              <label class="text-[10px] font-black uppercase tracking-widest text-ink-400 block mb-1.5">Service</label>
              <div class="flex gap-1 bg-ink-50 border border-ink-200 rounded-lg p-1">
                <button v-for="s in ['Morning','Evening']" :key="s"
                        @click="form.service_time = s"
                        class="flex-1 px-3 py-1 rounded text-xs font-bold transition-colors"
                        :class="form.service_time === s ? 'bg-white text-ink-900 shadow-sm' : 'text-ink-500 hover:text-ink-700'">
                  {{ s }}
                </button>
              </div>
            </div>
          </div>

          <div>
            <label class="text-[10px] font-black uppercase tracking-widest text-ink-400 block mb-1.5">Title</label>
            <input v-model="form.title"
                   class="w-full px-3 py-2.5 bg-ink-50 border border-ink-200 rounded-lg text-sm font-semibold focus:bg-white focus:border-rose-500 outline-none" />
          </div>

          <div>
            <label class="text-[10px] font-black uppercase tracking-widest text-ink-400 block mb-1.5">Message</label>
            <textarea v-model="form.body" rows="6"
                      class="w-full px-3 py-2.5 bg-ink-50 border border-ink-200 rounded-lg text-sm focus:bg-white focus:border-rose-500 outline-none font-mono leading-relaxed" />
            <div class="text-[10px] text-ink-400 mt-1.5">{{ form.body.length }} chars</div>
          </div>

          <div class="flex items-center justify-between pt-3 border-t border-ink-100">
            <label class="flex items-center gap-2 text-xs text-ink-600">
              <input v-model="form.send_sms" type="checkbox" class="rounded text-rose-600 focus:ring-rose-500" />
              Also send via SMS
            </label>
            <button @click="send" :disabled="sending || !form.title || !form.body"
                    class="px-4 py-2 text-xs font-bold bg-rose-600 text-white rounded-lg hover:bg-rose-700 shadow-sm disabled:opacity-50 disabled:cursor-not-allowed">
              Send to {{ recipients.length }} →
            </button>
          </div>
        </div>
      </div>

      <!-- Right column: recipients + log -->
      <div class="col-span-12 lg:col-span-5 space-y-6">
        <div class="bg-white rounded-xl border border-ink-100 overflow-hidden">
          <div class="px-5 py-4 border-b border-ink-100">
            <div class="text-[10px] font-black uppercase tracking-widest text-ink-400">Will receive</div>
            <div class="text-sm font-bold text-ink-900 mt-0.5">
              {{ recipients.length }} members ·
              {{ form.sunday_date ? new Date(form.sunday_date).toLocaleDateString("en-US", { month: "short", day: "numeric" }) : '—' }}
              {{ form.service_time }}
            </div>
          </div>
          <div class="divide-y divide-ink-100">
            <div v-for="r in recipients" :key="r.member + r.music_role"
                 class="px-5 py-2.5 flex items-center gap-3 hover:bg-ink-50/50">
              <MusicAvatar :id="r.member" :name="r.member_name" :size="28" />
              <div class="flex-1 min-w-0">
                <div class="text-xs font-semibold text-ink-900 truncate">{{ r.member_name }}</div>
                <div class="text-[10px] text-ink-400">{{ r.music_role }}</div>
              </div>
            </div>
            <div v-if="!recipients.length" class="px-5 py-6 text-center text-sm text-ink-400">
              No assignments yet for this service.
            </div>
          </div>
        </div>

        <!-- Sent log -->
        <div class="bg-white rounded-xl border border-ink-100 overflow-hidden">
          <div class="px-5 py-4 border-b border-ink-100">
            <div class="text-[10px] font-black uppercase tracking-widest text-ink-400">Recently sent</div>
          </div>
          <div class="divide-y divide-ink-100">
            <div v-for="n in store.notifications" :key="n.name"
                 class="px-5 py-3 flex items-start gap-3 hover:bg-ink-50/50">
              <span class="text-lg shrink-0">
                {{ n.notification_type === 'songs' ? '🎵' : n.notification_type === 'practice' ? '📅' : n.notification_type === 'swap' ? '🔄' : '📣' }}
              </span>
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                  <span class="text-xs font-bold text-ink-900 truncate">{{ n.title }}</span>
                  <span class="text-[9px] text-ink-400 tabular shrink-0">{{ fmtRelative(n.sent_at) }}</span>
                </div>
                <div class="text-[10px] text-ink-500 mt-0.5 line-clamp-2 whitespace-pre-line">
                  {{ n.body.split('\n').slice(0, 2).join(' · ') }}
                </div>
                <div class="text-[9px] text-ink-400 mt-1">→ {{ n.recipient_count }} recipient{{ n.recipient_count === 1 ? '' : 's' }}</div>
              </div>
            </div>
            <div v-if="!store.notifications.length" class="px-5 py-6 text-center text-sm text-ink-400">
              No notifications sent yet.
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
