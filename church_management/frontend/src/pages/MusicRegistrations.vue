<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import { call } from "@/composables/useFrappeApi";
import { useRealtime } from "@/composables/useRealtime";
import { useSessionStore } from "@/stores/session";
import { useRouter } from "vue-router";

const router = useRouter();
const session = useSessionStore();
const rows = ref([]);
const loading = ref(false);
const filter = ref("Pending");
const selected = ref(null);
const editing = ref(false);
const draft = ref(null);
const skillsCatalog = ref([]);
const actionMsg = ref("");
const acting = ref(false);
const showRejectInput = ref(false);
const rejectReason = ref("");

const filtered = computed(() => {
  if (filter.value === "All") return rows.value;
  return rows.value.filter(r => r.status === filter.value);
});

async function load() {
  loading.value = true;
  try {
    rows.value = await call("church_management.api.music_team.list_registrations");
    if (selected.value) {
      const refreshed = rows.value.find(r => r.name === selected.value.name);
      if (refreshed) selected.value = refreshed;
    }
  } finally {
    loading.value = false;
  }
}

async function loadSkills() {
  try {
    const tags = await call("church_management.api.music_team.get_roles");
    skillsCatalog.value = tags.map(t => ({ id: t.name, label: t.tag_label || t.name }));
  } catch {}
}

function pick(r) {
  selected.value = r;
  editing.value = false;
  showRejectInput.value = false;
  actionMsg.value = "";
}

function startEdit() {
  draft.value = JSON.parse(JSON.stringify(selected.value));
  editing.value = true;
}

async function saveEdit() {
  acting.value = true;
  try {
    const patch = {
      first_name: draft.value.first_name,
      last_name: draft.value.last_name,
      email: draft.value.email,
      contact_number: draft.value.contact_number,
      birthday: draft.value.birthday,
      member_since: draft.value.member_since,
      envelope_number: draft.value.envelope_number,
      matched_church_member: draft.value.matched_church_member,
      skills: draft.value.skills,
    };
    await call("church_management.api.music_team.update_registration", { name: selected.value.name, patch });
    editing.value = false;
    await load();
  } catch (e) {
    actionMsg.value = e.message;
  } finally {
    acting.value = false;
  }
}

const lastAcceptedEmail = ref("");

async function accept() {
  if (!confirm(`Accept ${selected.value.first_name} ${selected.value.last_name}? This creates a user account and emails a temporary password.`)) return;
  acting.value = true;
  actionMsg.value = "";
  try {
    await call("church_management.api.music_team.accept_registration", { name: selected.value.name });
    lastAcceptedEmail.value = selected.value.email;
    actionMsg.value = "Accepted. Acceptance email sent.";
    await load();
  } catch (e) {
    actionMsg.value = e.message;
  } finally {
    acting.value = false;
  }
}

async function reject() {
  acting.value = true;
  actionMsg.value = "";
  try {
    await call("church_management.api.music_team.reject_registration", {
      name: selected.value.name, reason: rejectReason.value,
    });
    showRejectInput.value = false;
    rejectReason.value = "";
    await load();
  } catch (e) {
    actionMsg.value = e.message;
  } finally {
    acting.value = false;
  }
}

function toggleSkillDraft(id) {
  if (!draft.value.skills) draft.value.skills = [];
  const i = draft.value.skills.indexOf(id);
  if (i >= 0) draft.value.skills.splice(i, 1);
  else draft.value.skills.push(id);
}

function norm(v) { return (v == null ? "" : String(v)).trim().toLowerCase(); }
function fieldsMatch(a, b) {
  const na = norm(a), nb = norm(b);
  if (!na || !nb) return null;
  return na === nb;
}
function matchRows(sel) {
  const cm = sel?.matched_church_member_data || {};
  return [
    { label: "Envelope #", field: null,             submitted: sel.envelope_number, record: cm.envelope_number, mono: true },
    { label: "First name", field: "first_name",     submitted: sel.first_name,      record: cm.firstname },
    { label: "Last name",  field: "last_name",      submitted: sel.last_name,       record: cm.lastname },
    { label: "Email",      field: "email",          submitted: sel.email,           record: cm.email_address },
    { label: "Contact",    field: "contact_number", submitted: sel.contact_number,  record: cm.contact_number },
    { label: "Birthday",   field: "birthday",       submitted: sel.birthday,        record: cm.birthday },
  ];
}

async function applyField(field, source) {
  if (!field || !selected.value?.matched_church_member) return;
  acting.value = true;
  actionMsg.value = "";
  try {
    await call("church_management.api.music_team.apply_match_field", {
      name: selected.value.name, field, source,
    });
    await load();
    actionMsg.value = source === "submitted"
      ? "Submitted value applied to Church Member record."
      : "Church Member value applied to registration.";
  } catch (e) {
    actionMsg.value = e.message;
  } finally {
    acting.value = false;
  }
}

const stop = useRealtime("music_team_event", (data) => {
  if (data?.action?.startsWith("registration_")) load();
});

onMounted(async () => { await loadSkills(); await load(); });
onBeforeUnmount(() => stop && stop());

async function logout() { await session.logout(); router.replace("/login"); }
</script>

<template>
  <div class="bg-[#f0eee9] min-h-full">
    <div class="bg-gradient-to-br from-rose-600 to-rose-800 text-white px-6 sm:px-12 pt-10 pb-16 relative overflow-hidden">
      <div class="absolute -top-20 -right-20 w-64 h-64 rounded-full bg-white/10" />
      <div class="relative max-w-6xl mx-auto flex items-start justify-between gap-4">
        <div>
          <div class="text-[10px] font-black uppercase tracking-[0.25em] text-rose-200 mb-2">Music Team · Leader</div>
          <h1 class="font-display font-bold text-3xl sm:text-4xl tracking-tight">Registrations.</h1>
          <p class="text-rose-100 text-sm mt-1.5">Review submissions, verify envelope matches, accept or reject.</p>
        </div>
        <button @click="logout" class="text-[11px] font-semibold text-rose-100 hover:text-white">Sign out</button>
      </div>
    </div>

    <div class="px-4 sm:px-12 -mt-8 pb-10 relative z-10">
      <div class="max-w-6xl mx-auto grid gap-4 transition-[grid-template-columns] duration-300 ease-out"
           :class="selected ? 'grid-cols-1 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1.4fr)]' : 'grid-cols-1'">
        <!-- List -->
        <div class="bg-white rounded-2xl shadow-xl ring-1 ring-ink-100 overflow-hidden"
             :class="selected ? '' : 'lg:max-w-3xl lg:mx-auto lg:w-full'">
          <div class="px-5 py-4 border-b border-ink-100 flex items-center justify-between gap-2">
            <div class="flex gap-1.5">
              <button v-for="s in ['Pending','Accepted','Rejected','All']" :key="s" @click="filter = s"
                class="px-3 py-1.5 rounded-full text-[11px] font-bold transition-colors"
                :class="filter === s ? 'bg-rose-600 text-white' : 'bg-ink-50 text-ink-600 hover:bg-ink-100'">
                {{ s }}
              </button>
            </div>
            <button @click="load" class="text-[11px] font-semibold text-ink-500 hover:text-rose-700">Refresh</button>
          </div>
          <div v-if="loading" class="px-5 py-10 text-center text-sm text-ink-400">Loading…</div>
          <div v-else-if="!filtered.length" class="px-5 py-10 text-center text-sm text-ink-400">No registrations.</div>
          <ul v-else class="divide-y divide-ink-100 max-h-[600px] overflow-y-auto">
            <li v-for="r in filtered" :key="r.name">
              <button @click="pick(r)"
                class="w-full text-left px-5 py-3 hover:bg-rose-50/40 transition-colors flex items-center gap-3"
                :class="selected?.name === r.name ? 'bg-rose-50/60' : ''">
                <div class="flex-1 min-w-0">
                  <div class="text-sm font-bold text-ink-900 truncate">{{ r.first_name }} {{ r.last_name }}</div>
                  <div class="text-[11px] text-ink-500 truncate">{{ r.email }}</div>
                  <div class="text-[10px] text-ink-400 mt-0.5">
                    Env <span class="font-semibold text-ink-600">{{ r.envelope_number || '—' }}</span>
                    · {{ r.submitted_on?.slice(0,10) }}
                  </div>
                </div>
                <span class="text-[10px] font-black uppercase tracking-wider px-2 py-0.5 rounded-full"
                  :class="{
                    'bg-amber-100 text-amber-700': r.status === 'Pending',
                    'bg-emerald-100 text-emerald-700': r.status === 'Accepted',
                    'bg-rose-100 text-rose-700': r.status === 'Rejected',
                  }">{{ r.status }}</span>
              </button>
            </li>
          </ul>
        </div>

        <!-- Detail -->
        <Transition name="slide-detail">
        <div v-if="selected" class="bg-white rounded-2xl shadow-xl ring-1 ring-ink-100 overflow-hidden">
          <div class="px-6 py-5 border-b border-ink-100 flex items-center justify-between">
            <div>
              <div class="text-[10px] font-black uppercase tracking-widest text-rose-700">{{ selected.name }}</div>
              <div class="font-display font-bold text-xl text-ink-900 mt-0.5">{{ selected.first_name }} {{ selected.last_name }}</div>
            </div>
            <button v-if="selected.status === 'Pending' && !editing" @click="startEdit"
              class="text-[11px] font-semibold text-rose-700 hover:underline">Edit</button>
          </div>

          <div class="px-6 py-5 space-y-5">
            <!-- View mode -->
            <div v-if="!editing" class="grid grid-cols-2 gap-4 text-sm">
              <div>
                <div class="text-[10px] font-black uppercase tracking-widest text-ink-400 mb-1">Email</div>
                <div class="text-ink-900">{{ selected.email }}</div>
              </div>
              <div>
                <div class="text-[10px] font-black uppercase tracking-widest text-ink-400 mb-1">Phone</div>
                <div class="text-ink-900">{{ selected.contact_number }}</div>
              </div>
              <div>
                <div class="text-[10px] font-black uppercase tracking-widest text-ink-400 mb-1">Birthday</div>
                <div class="text-ink-900">{{ selected.birthday }}</div>
              </div>
              <div>
                <div class="text-[10px] font-black uppercase tracking-widest text-ink-400 mb-1">Member since</div>
                <div class="text-ink-900">{{ selected.member_since || '—' }}</div>
              </div>
              <div>
                <div class="text-[10px] font-black uppercase tracking-widest text-ink-400 mb-1">Envelope</div>
                <div class="text-ink-900 font-mono">{{ selected.envelope_number || '—' }}</div>
              </div>
              <div>
                <div class="text-[10px] font-black uppercase tracking-widest text-ink-400 mb-1">Submitted</div>
                <div class="text-ink-900">{{ selected.submitted_on?.replace('T',' ').slice(0,16) }}</div>
              </div>
              <div class="col-span-2">
                <div class="text-[10px] font-black uppercase tracking-widest text-ink-400 mb-1">Skills</div>
                <div class="flex flex-wrap gap-1.5">
                  <span v-for="s in selected.skills" :key="s"
                    class="px-2.5 py-0.5 rounded-full bg-rose-50 text-rose-700 text-[11px] font-bold">{{ s }}</span>
                  <span v-if="!selected.skills?.length" class="text-ink-400">—</span>
                </div>
              </div>
            </div>

            <!-- Match preview / verification -->
            <div v-if="!editing" class="rounded-xl border-2 overflow-hidden"
              :class="selected.matched_church_member ? 'border-emerald-200' : 'border-amber-200'">
              <div class="px-4 py-2.5 flex items-center justify-between"
                :class="selected.matched_church_member ? 'bg-emerald-50/70' : 'bg-amber-50/60'">
                <div class="text-[10px] font-black uppercase tracking-widest"
                  :class="selected.matched_church_member ? 'text-emerald-700' : 'text-amber-700'">
                  {{ selected.matched_church_member ? 'Verify against Church Member record' : 'No match found' }}
                </div>
                <div v-if="selected.matched_church_member" class="font-mono text-[11px] text-emerald-800">
                  {{ selected.matched_church_member }}
                </div>
              </div>

              <!-- Side-by-side comparison (always rendered so the leader can scan & verify) -->
              <div class="bg-white">
                <div class="grid grid-cols-[1fr_1fr_auto] text-[10px] font-black uppercase tracking-widest text-ink-400 px-4 py-2 border-b border-ink-100 bg-ink-50/60">
                  <div>Submitted</div>
                  <div>Church Member record</div>
                  <div></div>
                </div>
                <div v-for="row in matchRows(selected)" :key="row.label"
                  class="grid grid-cols-[1fr_1fr_auto] gap-3 items-center px-4 py-2 text-sm border-b border-ink-100 last:border-0">
                  <!-- Submitted -->
                  <div class="min-w-0 flex items-center gap-2">
                    <div class="min-w-0 flex-1">
                      <div class="text-[10px] font-black uppercase tracking-widest text-ink-400 mb-0.5">{{ row.label }}</div>
                      <div class="truncate" :class="[row.mono ? 'font-mono' : '', row.submitted ? 'text-ink-900' : 'text-ink-300 italic']">
                        {{ row.submitted || '—' }}
                      </div>
                    </div>
                    <div v-if="row.field && selected.matched_church_member && fieldsMatch(row.submitted, row.record) === false"
                         class="flex items-center gap-1 shrink-0">
                      <button @click="applyField(row.field, 'submitted')" :disabled="acting"
                        :title="`Apply submitted ${row.label.toLowerCase()} to Church Member record`"
                        class="w-6 h-6 rounded-full flex items-center justify-center bg-emerald-100 text-emerald-700 hover:bg-emerald-600 hover:text-white transition-colors disabled:opacity-40">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="3" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
                      </button>
                      <button @click="applyField(row.field, 'record')" :disabled="acting"
                        :title="`Discard submitted ${row.label.toLowerCase()} (use Church Member value)`"
                        class="w-6 h-6 rounded-full flex items-center justify-center bg-rose-100 text-rose-700 hover:bg-rose-600 hover:text-white transition-colors disabled:opacity-40">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="3" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
                      </button>
                    </div>
                  </div>

                  <!-- Church Member record -->
                  <div class="min-w-0 flex items-center gap-2">
                    <div class="min-w-0 flex-1">
                      <div class="truncate" :class="[row.mono ? 'font-mono' : '', row.record ? 'text-ink-900' : 'text-ink-300 italic']">
                        {{ row.record || (selected.matched_church_member ? '—' : 'Not matched') }}
                      </div>
                    </div>
                    <div v-if="row.field && selected.matched_church_member && fieldsMatch(row.submitted, row.record) === false"
                         class="flex items-center gap-1 shrink-0">
                      <button @click="applyField(row.field, 'record')" :disabled="acting"
                        :title="`Apply Church Member ${row.label.toLowerCase()} to registration`"
                        class="w-6 h-6 rounded-full flex items-center justify-center bg-emerald-100 text-emerald-700 hover:bg-emerald-600 hover:text-white transition-colors disabled:opacity-40">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="3" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
                      </button>
                      <button @click="applyField(row.field, 'submitted')" :disabled="acting"
                        :title="`Discard Church Member value (overwrite with submitted)`"
                        class="w-6 h-6 rounded-full flex items-center justify-center bg-rose-100 text-rose-700 hover:bg-rose-600 hover:text-white transition-colors disabled:opacity-40">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="3" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
                      </button>
                    </div>
                  </div>

                  <!-- Status pill -->
                  <div>
                    <span v-if="fieldsMatch(row.submitted, row.record) === true"
                      class="inline-flex items-center gap-1 text-[10px] font-black uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700">
                      <svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="3" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
                      Match
                    </span>
                    <span v-else-if="fieldsMatch(row.submitted, row.record) === false"
                      class="inline-flex items-center gap-1 text-[10px] font-black uppercase tracking-wider px-2 py-0.5 rounded-full bg-rose-100 text-rose-700">
                      <svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="3" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
                      Differ
                    </span>
                    <span v-else class="text-[10px] font-black uppercase tracking-wider text-ink-300">—</span>
                  </div>
                </div>
                <div v-if="!selected.matched_church_member" class="px-4 py-3 text-[12px] text-ink-600 bg-amber-50/40 border-t border-amber-200">
                  No Church Member matched yet. Use <strong>Edit</strong> above to set the matched record by envelope number.
                </div>
              </div>
            </div>

            <!-- Edit mode -->
            <div v-if="editing" class="space-y-3 text-sm">
              <div class="grid grid-cols-2 gap-3">
                <div><label class="block text-[10px] font-black uppercase tracking-widest text-ink-700 mb-1">First name</label>
                  <input v-model="draft.first_name" class="w-full px-3 py-2 bg-ink-50 border border-ink-200 rounded-lg text-sm" /></div>
                <div><label class="block text-[10px] font-black uppercase tracking-widest text-ink-700 mb-1">Last name</label>
                  <input v-model="draft.last_name" class="w-full px-3 py-2 bg-ink-50 border border-ink-200 rounded-lg text-sm" /></div>
                <div><label class="block text-[10px] font-black uppercase tracking-widest text-ink-700 mb-1">Email</label>
                  <input v-model="draft.email" class="w-full px-3 py-2 bg-ink-50 border border-ink-200 rounded-lg text-sm" /></div>
                <div><label class="block text-[10px] font-black uppercase tracking-widest text-ink-700 mb-1">Contact number</label>
                  <input v-model="draft.contact_number" class="w-full px-3 py-2 bg-ink-50 border border-ink-200 rounded-lg text-sm" /></div>
                <div><label class="block text-[10px] font-black uppercase tracking-widest text-ink-700 mb-1">Birthday</label>
                  <input v-model="draft.birthday" type="date" class="w-full px-3 py-2 bg-ink-50 border border-ink-200 rounded-lg text-sm" /></div>
                <div><label class="block text-[10px] font-black uppercase tracking-widest text-ink-700 mb-1">Envelope #</label>
                  <input v-model="draft.envelope_number" class="w-full px-3 py-2 bg-ink-50 border border-ink-200 rounded-lg text-sm font-mono" /></div>
                <div class="col-span-2"><label class="block text-[10px] font-black uppercase tracking-widest text-ink-700 mb-1">Matched Church Member</label>
                  <input v-model="draft.matched_church_member" placeholder="Envelope number / member ID"
                    class="w-full px-3 py-2 bg-ink-50 border border-ink-200 rounded-lg text-sm font-mono" /></div>
              </div>
              <div>
                <label class="block text-[10px] font-black uppercase tracking-widest text-ink-700 mb-1">Skills</label>
                <div class="flex flex-wrap gap-1.5">
                  <button v-for="s in skillsCatalog" :key="s.id" type="button" @click="toggleSkillDraft(s.id)"
                    class="px-2.5 py-1 rounded-full text-[11px] font-bold border-2 transition-colors"
                    :class="(draft.skills || []).includes(s.id) ? 'bg-rose-600 border-rose-600 text-white' : 'bg-white border-ink-200 text-ink-700 hover:border-rose-400'">
                    {{ s.label }}
                  </button>
                </div>
              </div>
              <div class="flex justify-end gap-2 pt-2">
                <button @click="editing = false" class="px-4 py-2 rounded-lg text-[12px] font-bold text-ink-600 hover:bg-ink-50">Cancel</button>
                <button @click="saveEdit" :disabled="acting"
                  class="px-4 py-2 rounded-lg text-[12px] font-bold bg-ink-900 text-white hover:bg-ink-800 disabled:opacity-50">Save changes</button>
              </div>
            </div>

            <div v-if="actionMsg" class="text-sm rounded-lg px-4 py-2"
              :class="actionMsg.toLowerCase().includes('accept') ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-rose-50 text-rose-700 border border-rose-200'">
              <div>{{ actionMsg }}</div>
              <RouterLink v-if="actionMsg.toLowerCase().includes('accept')" to="/admin/roles"
                class="inline-block mt-1 text-[11px] font-bold text-emerald-800 hover:underline">
                Open role assignments to add Worship Leader / extra roles →
              </RouterLink>
            </div>

            <!-- Actions -->
            <div v-if="!editing && selected.status === 'Pending'" class="flex flex-col sm:flex-row gap-2 pt-3 border-t border-ink-100">
              <button @click="accept" :disabled="acting"
                class="flex-1 px-5 py-3 rounded-xl text-sm font-bold bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50">
                Accept &amp; create account
              </button>
              <button v-if="!showRejectInput" @click="showRejectInput = true" :disabled="acting"
                class="px-5 py-3 rounded-xl text-sm font-bold bg-white border-2 border-rose-200 text-rose-700 hover:bg-rose-50">
                Reject
              </button>
            </div>

            <div v-if="showRejectInput && !editing" class="space-y-2">
              <label class="block text-[10px] font-black uppercase tracking-widest text-ink-700">Reason (internal)</label>
              <textarea v-model="rejectReason" rows="2"
                class="w-full px-3 py-2 bg-ink-50 border border-ink-200 rounded-lg text-sm" placeholder="Optional note for records." />
              <div class="flex gap-2 justify-end">
                <button @click="showRejectInput = false" class="px-4 py-2 rounded-lg text-[12px] font-bold text-ink-600 hover:bg-ink-50">Cancel</button>
                <button @click="reject" :disabled="acting"
                  class="px-4 py-2 rounded-lg text-[12px] font-bold bg-rose-600 text-white hover:bg-rose-700 disabled:opacity-50">Confirm reject</button>
              </div>
            </div>
          </div>
        </div>

        </Transition>
      </div>
    </div>
  </div>
</template>

<style scoped>
.slide-detail-enter-active,
.slide-detail-leave-active {
  transition: transform 320ms cubic-bezier(0.16, 1, 0.3, 1), opacity 220ms ease-out;
}
.slide-detail-enter-from {
  transform: translateX(24px);
  opacity: 0;
}
.slide-detail-leave-to {
  transform: translateX(24px);
  opacity: 0;
}
</style>
