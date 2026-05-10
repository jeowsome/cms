<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { useRouter } from "vue-router";
import { call } from "@/composables/useFrappeApi";
import DateInput from "@/components/DateInput.vue";

const router = useRouter();
const skillsCatalog = ref([]);
const submitted = ref(false);
const submitting = ref(false);
const errorMsg = ref("");

const form = ref({
  email: "", first_name: "", last_name: "", gender: "", birthday: "",
  contact_number: "", member_since: "", envelope_number: "",
  skills: [],
});

const valid = computed(() =>
  form.value.email && form.value.first_name && form.value.last_name &&
  form.value.gender && form.value.birthday && form.value.contact_number &&
  form.value.skills.length > 0
);

const visibleSkills = computed(() =>
  form.value.gender === "Female"
    ? skillsCatalog.value.filter(s => s.id.toLowerCase() !== "worship lead")
    : skillsCatalog.value
);

const SKILL_META = {
  "worship lead":     { label: "Worship Leader",  group: "lead",   desc: "Lead vocals + cue the band",     icon: "M19.114 5.636a9 9 0 010 12.728M16.463 8.288a5.25 5.25 0 010 7.424M6.75 8.25l4.72-4.72a.75.75 0 011.28.53v15.88a.75.75 0 01-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.01 9.01 0 012.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75z" },
  "back up singer":   { label: "Backup Singer",   group: "vocals", desc: "Harmonies and supporting vocals", icon: "M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" },
  "keyboard":         { label: "Keyboard",        group: "instr",  desc: "Piano, synth, organ",             icon: "M3 9.75h18M3 9.75v8.25A1.5 1.5 0 004.5 19.5h15a1.5 1.5 0 001.5-1.5V9.75M7.5 9.75v6m4.5-6v6m4.5-6v6" },
  "acoustic guitar":  { label: "Acoustic Guitar", group: "instr",  desc: "Strummed or fingerstyle",         icon: "M9 18V4l9-1.5v13M9 18a3 3 0 11-6 0 3 3 0 016 0zm9-1.5a3 3 0 11-6 0 3 3 0 016 0z" },
  "bass guitar":      { label: "Bass Guitar",     group: "instr",  desc: "Rhythm + low end",                icon: "M9 9l10.5-3m0 6.553v3.75a2.25 2.25 0 01-1.632 2.163l-1.32.377a1.803 1.803 0 11-.99-3.467l2.31-.66a2.25 2.25 0 001.632-2.163zm0 0V2.25L9 5.25v10.303m0 0v3.75a2.25 2.25 0 01-1.632 2.163l-1.32.377a1.803 1.803 0 01-.99-3.467l2.31-.66A2.25 2.25 0 009 15.553z" },
  "beatbox":          { label: "Beatbox",         group: "instr",  desc: "Cajón, kit, or vocal percussion", icon: "M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" },
  "laptop":           { label: "Laptop Operator", group: "instr",  desc: "Lyrics, tracks, sound cues",      icon: "M9 17.25v1.007a3 3 0 01-.879 2.122L7.5 21h9l-.621-.621A3 3 0 0115 18.257V17.25m6-12V15a2.25 2.25 0 01-2.25 2.25H5.25A2.25 2.25 0 013 15V5.25m18 0A2.25 2.25 0 0018.75 3H5.25A2.25 2.25 0 003 5.25m18 0V12a2.25 2.25 0 01-2.25 2.25H5.25A2.25 2.25 0 013 12V5.25" },
  "devotion":         { label: "Devotion",        group: "lead",   desc: "Open in scripture & prayer",      icon: "M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" },
};

const HIDDEN_TAGS = new Set(["backup vocals 1", "backup vocals 2"]);
const devotionId = ref("");

onMounted(async () => {
  try {
    const tags = await call("church_management.api.music_team.get_roles");
    skillsCatalog.value = tags
      .filter(t => !HIDDEN_TAGS.has((t.name || "").toLowerCase()))
      .map(t => {
        const meta = SKILL_META[(t.name || "").toLowerCase()] || { group: "instr", desc: "", icon: "" };
        return { id: t.name, label: meta.label || t.tag_label || t.name, group: meta.group, desc: meta.desc, icon: meta.icon };
      });
  } catch (e) {
    skillsCatalog.value = Object.entries(SKILL_META)
      .filter(([id]) => !HIDDEN_TAGS.has(id))
      .map(([id, m]) => ({ id, ...m }));
  }
  const dev = skillsCatalog.value.find(s => s.id.toLowerCase() === "devotion");
  if (dev) {
    devotionId.value = dev.id;
    if (!form.value.skills.includes(dev.id)) form.value.skills.push(dev.id);
  }
});

function openPicker(e) {
  if (e?.target?.showPicker) {
    try { e.target.showPicker(); } catch {}
  }
}

function isLocked(id) { return id === devotionId.value; }

function toggleSkill(id) {
  if (isLocked(id)) return;
  const i = form.value.skills.indexOf(id);
  if (i >= 0) form.value.skills.splice(i, 1);
  else form.value.skills.push(id);
}

watch(() => form.value.gender, (g) => {
  if (g === "Female") {
    form.value.skills = form.value.skills.filter(s => s.toLowerCase() !== "worship lead");
  }
});

async function submit() {
  if (!valid.value || submitting.value) return;
  submitting.value = true;
  errorMsg.value = "";
  try {
    await call("church_management.api.music_team.submit_registration", { payload: form.value });
    submitted.value = true;
  } catch (e) {
    errorMsg.value = e.message || "Submission failed.";
  } finally {
    submitting.value = false;
  }
}

function reset() {
  submitted.value = false;
  form.value = { email: "", first_name: "", last_name: "", gender: "", birthday: "", contact_number: "", member_since: "", envelope_number: "", skills: devotionId.value ? [devotionId.value] : [] };
}
</script>

<template>
  <div v-if="!submitted" class="bg-[#f0eee9] w-full" style="min-height:100%">
    <div class="relative bg-gradient-to-br from-rose-600 to-rose-800 text-white px-6 sm:px-12 pt-14 pb-20 overflow-hidden">
      <div class="absolute -top-20 -right-20 w-64 h-64 rounded-full bg-white/10" />
      <div class="absolute top-32 -left-12 w-40 h-40 rounded-full bg-white/5" />
      <div class="relative max-w-2xl">
        <div class="inline-flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.25em] text-rose-200 mb-3">
          <span class="w-8 h-px bg-rose-300" />
          Jezreel Baptist Church · Music Team
        </div>
        <h1 class="font-display font-bold text-4xl sm:text-5xl leading-tight tracking-tight">Join the worship team.</h1>
        <p class="text-rose-100 text-base mt-4 max-w-lg">
          Tell us your details and what you play. We'll match this to your existing records and send a confirmation once you're verified.
        </p>
      </div>
    </div>

    <div class="px-4 sm:px-12 -mt-10 pb-10 relative z-10">
      <div class="bg-white rounded-2xl shadow-xl ring-1 ring-ink-100 max-w-3xl mx-auto overflow-hidden">
        <div class="px-6 sm:px-8 py-6 border-b border-ink-100">
          <div class="text-[10px] font-black uppercase tracking-widest text-rose-700">Step 1 of 1</div>
          <h2 class="font-display font-bold text-2xl text-ink-900 mt-0.5">Registration details</h2>
        </div>

        <div class="px-6 sm:px-8 py-6 space-y-6">
          <div>
            <label class="block text-[10px] font-black uppercase tracking-widest text-ink-700 mb-1.5">Email address <span class="text-rose-600">*</span></label>
            <input v-model="form.email" type="email" placeholder="you@example.com"
              class="w-full px-4 py-2.5 bg-ink-50 border border-ink-200 rounded-xl text-sm focus:bg-white focus:border-rose-500 focus:ring-2 focus:ring-rose-100 outline-none" />
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label class="block text-[10px] font-black uppercase tracking-widest text-ink-700 mb-1.5">First name <span class="text-rose-600">*</span></label>
              <input v-model="form.first_name" placeholder="Maria"
                class="w-full px-4 py-2.5 bg-ink-50 border border-ink-200 rounded-xl text-sm focus:bg-white focus:border-rose-500 focus:ring-2 focus:ring-rose-100 outline-none" />
            </div>
            <div>
              <label class="block text-[10px] font-black uppercase tracking-widest text-ink-700 mb-1.5">Last name <span class="text-rose-600">*</span></label>
              <input v-model="form.last_name" placeholder="Dela Cruz"
                class="w-full px-4 py-2.5 bg-ink-50 border border-ink-200 rounded-xl text-sm focus:bg-white focus:border-rose-500 focus:ring-2 focus:ring-rose-100 outline-none" />
            </div>
          </div>

          <div>
            <label class="block text-[10px] font-black uppercase tracking-widest text-ink-700 mb-1.5">Gender <span class="text-rose-600">*</span></label>
            <div class="grid grid-cols-2 gap-2.5">
              <button v-for="g in ['Male','Female']" :key="g" type="button" @click="form.gender = g"
                class="px-4 py-2.5 rounded-xl border-2 text-sm font-bold transition-all"
                :class="form.gender === g ? 'border-rose-500 bg-rose-50/60 text-rose-900 shadow-sm' : 'border-ink-200 bg-white text-ink-700 hover:border-rose-300'">
                {{ g }}
              </button>
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label class="block text-[10px] font-black uppercase tracking-widest text-ink-700 mb-1.5">Birthday <span class="text-rose-600">*</span></label>
              <DateInput v-model="form.birthday" />
            </div>
            <div>
              <label class="block text-[10px] font-black uppercase tracking-widest text-ink-700 mb-1.5">Contact number <span class="text-rose-600">*</span></label>
              <input v-model="form.contact_number" type="tel" placeholder="+63 917 555 0123"
                class="w-full px-4 py-2.5 bg-ink-50 border border-ink-200 rounded-xl text-sm focus:bg-white focus:border-rose-500 focus:ring-2 focus:ring-rose-100 outline-none" />
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label class="block text-[10px] font-black uppercase tracking-widest text-ink-700 mb-1.5">Envelope number</label>
              <input v-model="form.envelope_number" placeholder="e.g. 0247"
                class="w-full px-4 py-2.5 bg-ink-50 border border-ink-200 rounded-xl text-sm focus:bg-white focus:border-rose-500 focus:ring-2 focus:ring-rose-100 outline-none" />
              <div class="text-[10px] text-ink-400 mt-1">Helps the leader match you to your member record.</div>
            </div>
            <div>
              <div class="flex items-baseline justify-between mb-1.5">
                <label class="text-[10px] font-black uppercase tracking-widest text-ink-700">Member since</label>
                <span class="text-[10px] text-ink-400 font-medium normal-case tracking-normal">(optional)</span>
              </div>
              <DateInput v-model="form.member_since" />
              <div class="text-[10px] text-ink-400 mt-1 italic">Don't worry if you can't recall — leave blank, approximate, or just pick January 1 of the year.</div>
            </div>
          </div>

          <div>
            <div class="flex items-baseline justify-between mb-1.5">
              <label class="text-[10px] font-black uppercase tracking-widest text-ink-700">Skills <span class="text-rose-600">*</span></label>
              <span class="text-[10px] text-ink-400">{{ form.skills.length }} selected</span>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              <button v-for="s in visibleSkills" :key="s.id" type="button" @click="toggleSkill(s.id)"
                :disabled="isLocked(s.id)"
                class="flex items-start gap-3 p-3 rounded-xl border-2 text-left transition-all relative"
                :class="[
                  form.skills.includes(s.id) ? 'border-rose-500 bg-rose-50/60 shadow-sm' : 'border-ink-200 bg-white hover:border-rose-300',
                  isLocked(s.id) ? 'cursor-default' : ''
                ]">
                <div class="w-9 h-9 rounded-lg flex items-center justify-center shrink-0 transition-colors"
                  :class="form.skills.includes(s.id) ? 'bg-rose-600 text-white'
                    : s.group === 'lead' ? 'bg-amber-50 text-amber-700'
                    : s.group === 'vocals' ? 'bg-rose-50 text-rose-700'
                    : 'bg-brand-50 text-brand-700'">
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round">
                    <path :d="s.icon" />
                  </svg>
                </div>
                <div class="min-w-0 flex-1">
                  <div class="flex items-center gap-1.5">
                    <div class="text-sm font-bold" :class="form.skills.includes(s.id) ? 'text-rose-900' : 'text-ink-900'">{{ s.label }}</div>
                    <span v-if="isLocked(s.id)" class="text-[9px] font-black uppercase tracking-widest px-1.5 py-0.5 rounded-full bg-rose-600 text-white">Required</span>
                  </div>
                  <div class="text-[11px] text-ink-500 mt-0.5">{{ s.desc }}</div>
                </div>
                <div class="w-5 h-5 rounded-md border-2 flex items-center justify-center shrink-0"
                     :class="form.skills.includes(s.id) ? 'border-rose-600 bg-rose-600' : 'border-ink-300 bg-white'">
                  <svg v-if="form.skills.includes(s.id)" class="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" stroke-width="3" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
                </div>
              </button>
            </div>
          </div>

          <div v-if="errorMsg" class="text-sm text-rose-700 bg-rose-50 border border-rose-200 rounded-lg px-4 py-2">{{ errorMsg }}</div>

          <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pt-5 border-t border-ink-100">
            <p class="text-[11px] text-ink-500 italic max-w-sm">
              We'll review your registration and email you within a few days.
            </p>
            <button @click="submit" :disabled="!valid || submitting"
              class="px-6 py-3 rounded-xl text-sm font-bold shadow-sm transition-all"
              :class="valid && !submitting ? 'bg-rose-600 text-white hover:bg-rose-700' : 'bg-ink-200 text-ink-400 cursor-not-allowed'">
              {{ submitting ? "Submitting…" : "Submit registration" }}
            </button>
          </div>

          <div class="text-center pt-2">
            <RouterLink to="/login" class="text-[11px] font-semibold text-rose-700 hover:underline">← Already have an account? Sign in</RouterLink>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div v-else class="bg-[#f0eee9] w-full p-6 sm:p-12" style="min-height:100%">
    <div class="max-w-2xl mx-auto bg-white rounded-2xl shadow-xl ring-1 ring-ink-100 overflow-hidden">
      <div class="px-8 py-10 text-center bg-gradient-to-br from-emerald-50 to-emerald-100/50 border-b border-emerald-200">
        <div class="w-14 h-14 mx-auto rounded-full bg-emerald-600 flex items-center justify-center text-white shadow-lg">
          <svg class="w-7 h-7" fill="none" stroke="currentColor" stroke-width="3" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5"/></svg>
        </div>
        <h1 class="font-display font-bold text-3xl text-ink-900 mt-4">Registration received.</h1>
        <p class="text-ink-600 text-sm mt-1.5">A receipt has been sent to <strong class="font-semibold">{{ form.email }}</strong></p>
      </div>
      <div class="px-8 py-6">
        <div class="text-[10px] font-black uppercase tracking-widest text-ink-400 mb-2">What happens next</div>
        <ol class="space-y-2.5 text-sm text-ink-700">
          <li class="flex items-start gap-2.5"><span class="w-5 h-5 rounded-full bg-rose-100 text-rose-700 flex items-center justify-center text-[11px] font-black shrink-0 mt-0.5">1</span><span>The Music Team Leader reviews your details and matches them to existing church records.</span></li>
          <li class="flex items-start gap-2.5"><span class="w-5 h-5 rounded-full bg-rose-100 text-rose-700 flex items-center justify-center text-[11px] font-black shrink-0 mt-0.5">2</span><span>You'll receive an acceptance email with a temporary password — usually within a few days.</span></li>
          <li class="flex items-start gap-2.5"><span class="w-5 h-5 rounded-full bg-rose-100 text-rose-700 flex items-center justify-center text-[11px] font-black shrink-0 mt-0.5">3</span><span>Once you log in, set a permanent password and complete your profile.</span></li>
        </ol>
        <div class="flex items-center justify-end mt-6">
          <RouterLink to="/login" class="text-[11px] font-semibold text-ink-500 hover:text-ink-900">Sign in →</RouterLink>
        </div>
      </div>
    </div>
  </div>
</template>
