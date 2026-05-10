<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { call } from "@/composables/useFrappeApi";
import { useSessionStore } from "@/stores/session";

const router = useRouter();
const session = useSessionStore();

const profile = ref(null);
const skillsCatalog = ref([]);
const draft = ref({ first_name: "", last_name: "", profile_image: "", skills: [], preferred: "" });
const saving = ref(false);
const msg = ref("");

const unavailRows = ref([]);
const newUnavail = ref({ kind: "vacation", from_date: "", to_date: "", reason: "" });
const schedules = ref([]);

async function load() {
  profile.value = await call("church_management.api.music_team.get_my_music_profile");
  draft.value = {
    first_name: profile.value.first_name || "",
    last_name: profile.value.last_name || "",
    profile_image: profile.value.profile_image || "",
    skills: [...(profile.value.skills || [])],
    preferred: (profile.value.preferences || []).find(p => p.preferred)?.music_team_tag || "",
  };

  if (profile.value.church_member) {
    schedules.value = await call("church_management.api.music_team.my_assignments", { member: profile.value.church_member });
    try {
      const all = await call("church_management.api.music_team.list_unavailability");
      unavailRows.value = (all || []).filter(u => u.member === profile.value.church_member);
    } catch {
      unavailRows.value = [];
    }
  }
}

async function loadSkills() {
  const tags = await call("church_management.api.music_team.get_roles");
  skillsCatalog.value = tags.map(t => ({ id: t.name, label: t.tag_label || t.name }));
}

function toggleSkill(id) {
  const i = draft.value.skills.indexOf(id);
  if (i >= 0) draft.value.skills.splice(i, 1);
  else draft.value.skills.push(id);
  if (!draft.value.skills.includes(draft.value.preferred)) draft.value.preferred = "";
}

async function uploadImage(e) {
  const file = e.target.files?.[0];
  if (!file) return;
  const fd = new FormData();
  fd.append("file", file);
  fd.append("is_private", "0");
  fd.append("folder", "Home/Attachments");
  const res = await fetch("/api/method/upload_file", {
    method: "POST",
    headers: { "X-Frappe-CSRF-Token": window.csrfToken || "" },
    body: fd,
  });
  if (!res.ok) { msg.value = "Image upload failed."; return; }
  const json = await res.json();
  draft.value.profile_image = json.message?.file_url || json.file_url || "";
}

async function save() {
  saving.value = true;
  msg.value = "";
  try {
    await call("church_management.api.music_team.update_my_music_profile", {
      patch: {
        first_name: draft.value.first_name,
        last_name: draft.value.last_name,
        profile_image: draft.value.profile_image,
        skills: draft.value.skills,
        preferred: draft.value.preferred,
      },
    });
    msg.value = "Saved.";
    await load();
  } catch (e) { msg.value = e.message; }
  finally { saving.value = false; }
}

async function reloadUnavail() {
  const all = await call("church_management.api.music_team.list_unavailability");
  unavailRows.value = (all || []).filter(u => u.member === profile.value.church_member);
}

async function addUnavail() {
  if (!newUnavail.value.from_date || !newUnavail.value.to_date) return;
  await call("church_management.api.music_team.create_unavailability", {
    member: profile.value.church_member, ...newUnavail.value,
  });
  newUnavail.value = { kind: "vacation", from_date: "", to_date: "", reason: "" };
  await reloadUnavail();
}

async function delUnavail(name) {
  await call("church_management.api.music_team.delete_unavailability", { name });
  await reloadUnavail();
}

async function logout() { await session.logout(); router.replace("/login"); }

onMounted(async () => { await loadSkills(); await load(); });
</script>

<template>
  <div v-if="profile" class="bg-[#f0eee9] min-h-full">
    <div class="bg-gradient-to-br from-rose-600 to-rose-800 text-white px-6 sm:px-12 pt-10 pb-20 relative overflow-hidden">
      <div class="absolute -top-20 -right-20 w-64 h-64 rounded-full bg-white/10" />
      <div class="relative max-w-5xl mx-auto flex items-start justify-between gap-4">
        <div class="flex items-center gap-4">
          <div class="w-16 h-16 rounded-full bg-white/20 ring-2 ring-white/40 overflow-hidden flex items-center justify-center">
            <img v-if="draft.profile_image" :src="draft.profile_image" class="w-full h-full object-cover" />
            <span v-else class="text-xl font-display font-bold">{{ (draft.first_name || '?').charAt(0) }}</span>
          </div>
          <div>
            <div class="text-[10px] font-black uppercase tracking-[0.25em] text-rose-200 mb-1">Music Team · Member</div>
            <h1 class="font-display font-bold text-2xl sm:text-3xl tracking-tight">{{ draft.first_name }} {{ draft.last_name }}</h1>
            <div class="text-rose-100 text-sm mt-0.5">{{ profile.user }}</div>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <RouterLink to="/music/change-password"
            class="text-[11px] font-semibold text-rose-100 hover:text-white">Change password</RouterLink>
          <button @click="logout" class="text-[11px] font-semibold text-rose-100 hover:text-white">Sign out</button>
        </div>
      </div>
    </div>

    <div class="px-4 sm:px-12 -mt-12 pb-10 relative z-10">
      <div class="max-w-5xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-4">
        <!-- Profile editor -->
        <div class="bg-white rounded-2xl shadow-xl ring-1 ring-ink-100 overflow-hidden">
          <div class="px-6 py-4 border-b border-ink-100">
            <div class="text-[10px] font-black uppercase tracking-widest text-rose-700">Profile</div>
            <h2 class="font-display font-bold text-lg text-ink-900 mt-0.5">Personal details</h2>
          </div>
          <div class="px-6 py-5 space-y-4">
            <div>
              <label class="block text-[10px] font-black uppercase tracking-widest text-ink-700 mb-1.5">Profile picture</label>
              <div class="flex items-center gap-3">
                <div class="w-14 h-14 rounded-full bg-ink-100 overflow-hidden flex items-center justify-center">
                  <img v-if="draft.profile_image" :src="draft.profile_image" class="w-full h-full object-cover" />
                  <svg v-else class="w-6 h-6 text-ink-400" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"/></svg>
                </div>
                <label class="px-3 py-2 rounded-lg bg-ink-50 hover:bg-ink-100 text-[12px] font-bold text-ink-700 cursor-pointer">
                  Upload
                  <input type="file" accept="image/*" class="hidden" @change="uploadImage" />
                </label>
                <button v-if="draft.profile_image" @click="draft.profile_image = ''"
                  class="text-[11px] font-semibold text-rose-700 hover:underline">Remove</button>
              </div>
            </div>

            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block text-[10px] font-black uppercase tracking-widest text-ink-700 mb-1.5">First name</label>
                <input v-model="draft.first_name"
                  class="w-full px-3 py-2 bg-ink-50 border border-ink-200 rounded-lg text-sm focus:bg-white focus:border-rose-500 outline-none" />
              </div>
              <div>
                <label class="block text-[10px] font-black uppercase tracking-widest text-ink-700 mb-1.5">Last name</label>
                <input v-model="draft.last_name"
                  class="w-full px-3 py-2 bg-ink-50 border border-ink-200 rounded-lg text-sm focus:bg-white focus:border-rose-500 outline-none" />
              </div>
            </div>

            <div>
              <label class="block text-[10px] font-black uppercase tracking-widest text-ink-700 mb-1.5">Skills</label>
              <div class="flex flex-wrap gap-1.5">
                <button v-for="s in skillsCatalog" :key="s.id" type="button" @click="toggleSkill(s.id)"
                  class="px-3 py-1 rounded-full text-[11px] font-bold border-2 transition-colors"
                  :class="draft.skills.includes(s.id) ? 'bg-rose-600 border-rose-600 text-white' : 'bg-white border-ink-200 text-ink-700 hover:border-rose-400'">
                  {{ s.label }}
                </button>
              </div>
            </div>

            <div v-if="draft.skills.length">
              <label class="block text-[10px] font-black uppercase tracking-widest text-ink-700 mb-1.5">Preferred role</label>
              <select v-model="draft.preferred"
                class="w-full px-3 py-2 bg-ink-50 border border-ink-200 rounded-lg text-sm">
                <option value="">— None —</option>
                <option v-for="s in draft.skills" :key="s" :value="s">{{ s }}</option>
              </select>
            </div>

            <div v-if="msg" class="text-sm rounded-lg px-3 py-2 bg-emerald-50 text-emerald-700 border border-emerald-200">{{ msg }}</div>

            <div class="flex justify-end pt-2">
              <button @click="save" :disabled="saving"
                class="px-5 py-2.5 rounded-xl text-sm font-bold bg-rose-600 text-white hover:bg-rose-700 disabled:opacity-50">
                {{ saving ? "Saving…" : "Save profile" }}
              </button>
            </div>
          </div>
        </div>

        <!-- Unavailability + Schedule -->
        <div class="space-y-4">
          <div class="bg-white rounded-2xl shadow-xl ring-1 ring-ink-100 overflow-hidden">
            <div class="px-6 py-4 border-b border-ink-100">
              <div class="text-[10px] font-black uppercase tracking-widest text-rose-700">Unavailability</div>
              <h2 class="font-display font-bold text-lg text-ink-900 mt-0.5">Block out dates</h2>
            </div>
            <div class="px-6 py-4 space-y-3">
              <div class="grid grid-cols-2 gap-2">
                <select v-model="newUnavail.kind" class="px-3 py-2 bg-ink-50 border border-ink-200 rounded-lg text-sm">
                  <option value="vacation">Vacation</option>
                  <option value="medical">Medical</option>
                  <option value="event">Event</option>
                  <option value="suspended">Suspended</option>
                </select>
                <input v-model="newUnavail.reason" placeholder="Reason (optional)"
                  class="px-3 py-2 bg-ink-50 border border-ink-200 rounded-lg text-sm" />
                <input v-model="newUnavail.from_date" type="date" class="px-3 py-2 bg-ink-50 border border-ink-200 rounded-lg text-sm" />
                <input v-model="newUnavail.to_date" type="date" class="px-3 py-2 bg-ink-50 border border-ink-200 rounded-lg text-sm" />
              </div>
              <button @click="addUnavail"
                class="w-full px-4 py-2 rounded-lg text-[12px] font-bold bg-ink-900 text-white hover:bg-ink-800">Add</button>

              <ul v-if="unavailRows.length" class="divide-y divide-ink-100">
                <li v-for="u in unavailRows" :key="u.name" class="py-2 flex items-center gap-2 text-sm">
                  <span class="text-[10px] font-black uppercase tracking-wider text-rose-700 w-20">{{ u.kind }}</span>
                  <span class="flex-1 text-ink-700">{{ u.from_date }} → {{ u.to_date }}</span>
                  <button @click="delUnavail(u.name)" class="text-[11px] text-ink-400 hover:text-rose-700">Remove</button>
                </li>
              </ul>
              <div v-else class="text-[12px] text-ink-400 italic">No upcoming blocks.</div>
            </div>
          </div>

          <div class="bg-white rounded-2xl shadow-xl ring-1 ring-ink-100 overflow-hidden">
            <div class="px-6 py-4 border-b border-ink-100">
              <div class="text-[10px] font-black uppercase tracking-widest text-rose-700">Schedule</div>
              <h2 class="font-display font-bold text-lg text-ink-900 mt-0.5">Upcoming assignments</h2>
            </div>
            <div class="px-6 py-4">
              <ul v-if="schedules.length" class="divide-y divide-ink-100">
                <li v-for="s in schedules" :key="s.row_name" class="py-2.5">
                  <div class="flex items-center justify-between text-sm">
                    <div>
                      <div class="font-bold text-ink-900">{{ s.sunday_date }} · {{ s.service_time }}</div>
                      <div class="text-[12px] text-ink-500">{{ s.music_role }}</div>
                    </div>
                    <span class="text-[10px] font-black uppercase tracking-wider px-2 py-0.5 rounded-full bg-rose-100 text-rose-700">{{ s.status }}</span>
                  </div>
                </li>
              </ul>
              <div v-else class="text-[12px] text-ink-400 italic">No upcoming services.</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
  <div v-else class="p-10 text-center text-sm text-ink-400">Loading…</div>
</template>
