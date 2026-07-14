<script setup>
import { onMounted, ref, computed, reactive } from "vue";
import { call } from "@/composables/useFrappeApi";
import { useSessionStore } from "@/stores/session";
import InviteDonationModal from "@/components/InviteDonationModal.vue";

const session = useSessionStore();
const showInvite = ref(false);

const users = ref([]);
const grantable = ref([]);
const loading = ref(false);
const search = ref("");
const filterRole = ref("");
const saving = reactive({});
const message = reactive({});
// Per-user pending edits — Set of roles to apply on save.
const drafts = reactive({});

const ROLE_META = {
  "Finance Team": { color: "emerald", label: "Finance" },
  "Music Team Leader": { color: "rose", label: "Music Leader" },
  "Music Team Member": { color: "sky", label: "Music Member" },
  "Worship Leader": { color: "amber", label: "Worship Leader" },
  "Donation Editor": { color: "violet", label: "Donations" },
};

const COLOR_MAP = {
  emerald: { chip: "bg-emerald-100 text-emerald-700 ring-emerald-200", on: "bg-emerald-600 text-white", off: "bg-white text-ink-500 ring-ink-200 hover:bg-emerald-50" },
  rose:    { chip: "bg-rose-100 text-rose-700 ring-rose-200",          on: "bg-rose-600 text-white",    off: "bg-white text-ink-500 ring-ink-200 hover:bg-rose-50" },
  sky:     { chip: "bg-sky-100 text-sky-700 ring-sky-200",             on: "bg-sky-600 text-white",     off: "bg-white text-ink-500 ring-ink-200 hover:bg-sky-50" },
  amber:   { chip: "bg-amber-100 text-amber-700 ring-amber-200",       on: "bg-amber-600 text-white",   off: "bg-white text-ink-500 ring-ink-200 hover:bg-amber-50" },
  violet:  { chip: "bg-violet-100 text-violet-700 ring-violet-200",    on: "bg-violet-600 text-white",  off: "bg-white text-ink-500 ring-ink-200 hover:bg-violet-50" },
};

// What the operator's limited scope is called in the header badge.
const scopeLabel = computed(() => {
  if (session.isAdmin) return "";
  if (session.isLeader && session.isDonationAdmin) return "Music Leader + Donation scope";
  if (session.isLeader) return "Music Leader scope";
  return "Donation Admin scope";
});

onMounted(async () => {
  await Promise.all([loadGrantable(), load()]);
});

async function loadGrantable() {
  grantable.value = await call("church_management.api.admin.list_grantable_roles") || [];
}

async function load() {
  loading.value = true;
  try {
    users.value = await call("church_management.api.admin.list_assignable_users", {
      search: search.value || null,
    }) || [];
    // Seed drafts from current state
    for (const u of users.value) {
      drafts[u.name] = new Set(u.roles);
    }
  } finally {
    loading.value = false;
  }
}

// Admins implicitly satisfy every managed role; count and filter accordingly so
// the operator sees a consistent picture (a System Manager IS a Finance user).
function effectiveHas(u, role) {
  return u.is_admin || u.roles.includes(role);
}

const filteredUsers = computed(() => {
  if (!filterRole.value) return users.value;
  return users.value.filter(u => effectiveHas(u, filterRole.value));
});

function dirty(u) {
  const d = drafts[u.name];
  if (!d) return false;
  if (d.size !== u.roles.length) return true;
  for (const r of u.roles) if (!d.has(r)) return true;
  return false;
}

function toggle(u, role) {
  if (!grantable.value.includes(role)) return;
  const d = drafts[u.name];
  if (d.has(role)) d.delete(role);
  else d.add(role);
  // Re-trigger reactivity
  drafts[u.name] = new Set(d);
}

function flash(user, text, ok = true) {
  message[user] = { text, ok };
  setTimeout(() => { message[user] = null; }, 1800);
}

async function save(u) {
  if (!dirty(u)) return;
  // Send the union of (a) currently-set roles outside grantable scope (untouched)
  // and (b) the user's pending grantable picks. The server only mutates within
  // grantable scope, so passing only the grantable picks is fine.
  const target = Array.from(drafts[u.name]).filter(r => grantable.value.includes(r));
  saving[u.name] = true;
  try {
    const res = await call("church_management.api.admin.set_user_roles", {
      user: u.name, roles: JSON.stringify(target),
    });
    // Merge server-confirmed roles back in.
    u.roles = res.roles || [];
    drafts[u.name] = new Set(u.roles);
    flash(u.name, "Saved");
  } catch (e) {
    flash(u.name, e.message || "Save failed", false);
  } finally {
    saving[u.name] = false;
  }
}

function reset(u) {
  drafts[u.name] = new Set(u.roles);
}

function initials(u) {
  const s = (u.full_name || u.email || "?").trim();
  return s.split(/\s+/).slice(0, 2).map(w => w[0]).join("").toUpperCase();
}
</script>

<template>
  <div class="bg-[#f0eee9] min-h-full">
    <div class="max-w-4xl mx-auto bg-white min-h-screen shadow">

      <!-- Header -->
      <div class="border-b border-ink-100 px-6 py-4 sticky top-0 bg-white/95 backdrop-blur z-10">
        <div class="flex items-center justify-between gap-3">
          <div>
            <div class="text-[10px] font-black uppercase tracking-widest text-ink-400">Admin · Access</div>
            <h1 class="font-bold text-lg text-ink-900">Role Assignments</h1>
            <p class="text-[11px] text-ink-500 mt-0.5">
              Grant or revoke church-management roles. System Manager and other Frappe roles are managed in Frappe Desk.
            </p>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <div v-if="scopeLabel" class="text-[10px] font-bold uppercase tracking-wider text-amber-700 bg-amber-50 ring-1 ring-amber-200 px-2 py-1 rounded">
              {{ scopeLabel }}
            </div>
            <button
              v-if="session.isDonationAdmin"
              @click="showInvite = true"
              class="px-3 py-2 text-xs font-bold bg-violet-600 text-white rounded-lg hover:bg-violet-700 inline-flex items-center gap-1.5"
            >
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75" />
              </svg>
              Invite to Donations
            </button>
          </div>
        </div>

        <!-- Search + filter -->
        <div class="mt-3 flex flex-wrap gap-2">
          <input v-model="search" @keydown.enter="load" placeholder="Search by name…"
                 class="flex-1 min-w-[180px] px-3 py-2 bg-ink-50 border border-ink-200 rounded-lg text-sm focus:bg-white focus:border-rose-500 outline-none" />
          <button @click="load"
                  class="px-3 py-2 text-xs font-bold bg-ink-900 text-white rounded-lg hover:bg-ink-800">Search</button>
        </div>
        <div class="mt-2 flex flex-wrap gap-1.5">
          <button @click="filterRole = ''"
                  class="px-2 py-1 text-[10px] font-bold uppercase tracking-wider rounded-full ring-1 transition"
                  :class="filterRole === '' ? 'bg-ink-900 text-white ring-ink-900' : 'bg-white text-ink-500 ring-ink-200 hover:bg-ink-50'">
            All ({{ users.length }})
          </button>
          <button v-for="r in Object.keys(ROLE_META)" :key="r" @click="filterRole = r"
                  class="px-2 py-1 text-[10px] font-bold uppercase tracking-wider rounded-full ring-1 transition"
                  :class="filterRole === r ? COLOR_MAP[ROLE_META[r].color].on + ' ring-transparent' : COLOR_MAP[ROLE_META[r].color].chip">
            {{ ROLE_META[r].label }} ({{ users.filter(u => effectiveHas(u, r)).length }})
          </button>
        </div>
      </div>

      <div v-if="loading" class="px-6 py-10 text-center text-ink-400 text-sm">Loading users…</div>

      <div v-else-if="!filteredUsers.length" class="px-6 py-10 text-center text-ink-400 text-sm">
        No users match the current filters.
      </div>

      <div v-else class="px-4 sm:px-6 py-4 space-y-2">
        <div v-for="u in filteredUsers" :key="u.name"
             class="bg-white rounded-xl border border-ink-100 hover:border-ink-200 transition p-3 sm:p-4">
          <div class="flex items-start gap-3">
            <!-- Avatar -->
            <div class="w-10 h-10 rounded-full bg-rose-100 text-rose-700 ring-1 ring-rose-200 flex items-center justify-center font-bold text-sm shrink-0 overflow-hidden">
              <img v-if="u.user_image" :src="u.user_image" class="w-full h-full object-cover" />
              <span v-else>{{ initials(u) }}</span>
            </div>

            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="font-semibold text-ink-900 text-sm truncate">{{ u.full_name }}</span>
                <span v-if="u.church_member" class="text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-sky-100 text-sky-700 ring-1 ring-sky-200">
                  Church Member
                </span>
                <span v-if="u.user_type === 'System User'" class="text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-ink-100 text-ink-500">
                  Staff
                </span>
                <span v-if="u.is_admin" class="text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-rose-600 text-white ring-1 ring-rose-700"
                      title="System Manager / Administrator — implicitly satisfies every role below">
                  Admin
                </span>
              </div>
              <div class="text-[11px] text-ink-500 truncate">{{ u.email }}</div>

              <!-- Department donation assignments -->
              <div v-if="u.donation_departments?.length" class="mt-1.5 flex flex-wrap gap-1">
                <span
                  v-for="d in u.donation_departments"
                  :key="d"
                  class="text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-violet-50 text-violet-600 ring-1 ring-violet-200"
                  title="Assigned donation record — controls which department they see on /donations"
                >
                  {{ d }}
                </span>
              </div>

              <!-- Role toggles -->
              <div class="mt-2 flex flex-wrap gap-1.5">
                <button v-for="role in Object.keys(ROLE_META)" :key="role"
                        @click="toggle(u, role)"
                        :disabled="u.is_admin || !grantable.includes(role)"
                        :title="u.is_admin
                                  ? 'Implicitly granted via System Manager'
                                  : (!grantable.includes(role) ? 'You don\'t have permission to grant this role' : '')"
                        class="px-2.5 py-1 text-[11px] font-bold rounded-full ring-1 transition disabled:cursor-not-allowed"
                        :class="[
                          (u.is_admin || drafts[u.name]?.has(role))
                            ? COLOR_MAP[ROLE_META[role].color].on + ' ring-transparent'
                            : COLOR_MAP[ROLE_META[role].color].off,
                          u.is_admin ? 'opacity-80' : 'disabled:opacity-40',
                        ]">
                  {{ ROLE_META[role].label }}
                </button>
              </div>
            </div>

            <!-- Save / status -->
            <div class="flex flex-col items-end gap-1 shrink-0 min-w-[80px]">
              <button v-if="dirty(u)" @click="save(u)" :disabled="saving[u.name]"
                      class="px-3 py-1.5 text-[11px] font-bold bg-rose-600 text-white rounded-lg hover:bg-rose-700 disabled:bg-ink-300">
                {{ saving[u.name] ? "Saving…" : "Save" }}
              </button>
              <button v-if="dirty(u)" @click="reset(u)"
                      class="text-[10px] text-ink-400 hover:text-ink-700">Reset</button>
              <span v-if="message[u.name]"
                    class="text-[10px] font-bold"
                    :class="message[u.name].ok ? 'text-emerald-700' : 'text-rose-700'">
                {{ message[u.name].text }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <InviteDonationModal
        :is-open="showInvite"
        @close="showInvite = false"
        @invited="load"
      />
    </div>
  </div>
</template>
