<script setup>
import { onMounted, reactive, computed } from "vue";
import { useMusicTeamStore } from "@/stores/musicTeam";
import { useRealtime } from "@/composables/useRealtime";
import MusicHeader from "@/components/MusicHeader.vue";
import MusicAvatar from "@/components/MusicAvatar.vue";

const store = useMusicTeamStore();
const drafts = reactive({}); // memberName -> { roles: Set<string>, preferred: string }

onMounted(() => store.loadCatalog().then(seed));
useRealtime("music_team_event", (msg) => {
  if (msg.action === "roles_updated") store.loadCatalog().then(seed);
});

function seed() {
  for (const m of store.members) {
    drafts[m.name] = {
      roles: new Set(m.roles || []),
      preferred: m.preferred_role || "",
    };
  }
}

function isAllowed(member, role) {
  return drafts[member]?.roles?.has(role);
}
function isPreferred(member, role) {
  return drafts[member]?.preferred === role;
}

async function toggle(memberId, roleName) {
  const d = drafts[memberId];
  if (!d) return;
  const allowed = d.roles.has(roleName);
  const isPref = d.preferred === roleName;
  if (!allowed) d.roles.add(roleName);
  else if (allowed && !isPref) d.preferred = roleName;
  else { d.roles.delete(roleName); if (isPref) d.preferred = ""; }

  await store.setMemberRoles(memberId, Array.from(d.roles), d.preferred);
}
</script>

<template>
  <div class="bg-white w-full min-h-full">
    <MusicHeader title="Roles &amp; Preferences"
                 subtitle="What each music team member is approved to play, and what they prefer.">
      <div class="flex items-center gap-3 text-[11px] text-ink-500 mr-2">
        <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded bg-rose-100 ring-1 ring-rose-300 flex items-center justify-center"><span class="w-1.5 h-1.5 rounded-full bg-rose-500" /></span>Allowed</span>
        <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded bg-amber-100 ring-1 ring-amber-400 flex items-center justify-center text-[8px]">★</span>Preferred</span>
      </div>
    </MusicHeader>

    <div class="p-6 overflow-auto">
      <div class="inline-block min-w-full">
        <div class="grid bg-ink-50/50 rounded-t-xl border border-ink-200 sticky top-0"
             :style="{ gridTemplateColumns: `220px repeat(${store.roles.length}, 1fr)` }">
          <div class="px-4 py-3 text-[10px] font-black text-ink-400 uppercase tracking-widest border-r border-ink-200">
            Member · {{ store.members.length }}
          </div>
          <div v-for="r in store.roles" :key="r.name"
               class="px-2 py-3 text-center border-r border-ink-200 last:border-r-0">
            <div class="w-7 h-7 rounded-lg mx-auto mb-1 bg-brand-50 text-brand-700 flex items-center justify-center text-[10px] font-black">
              {{ r.tag_label.slice(0, 2) }}
            </div>
            <div class="text-[9px] text-ink-400 truncate">{{ r.tag_label }}</div>
          </div>
        </div>

        <div class="border-x border-b border-ink-200 rounded-b-xl divide-y divide-ink-100">
          <div v-for="m in store.members" :key="m.name"
               class="grid hover:bg-ink-50/30"
               :style="{ gridTemplateColumns: `220px repeat(${store.roles.length}, 1fr)` }">
            <div class="px-4 py-3 flex items-center gap-2.5 border-r border-ink-100 min-w-0">
              <MusicAvatar :id="m.name" :name="m.full_name" :size="32" />
              <div class="min-w-0">
                <div class="text-xs font-semibold text-ink-900 truncate">{{ m.full_name }}</div>
                <div class="text-[10px] text-ink-400">
                  {{ drafts[m.name]?.preferred ? `★ ${drafts[m.name].preferred}` : '—' }}
                </div>
              </div>
            </div>
            <button v-for="r in store.roles" :key="r.name"
                    @click="toggle(m.name, r.name)"
                    class="flex items-center justify-center border-r border-ink-100 last:border-r-0 transition-colors"
                    :class="isPreferred(m.name, r.name) ? 'bg-amber-50 hover:bg-amber-100'
                          : isAllowed(m.name, r.name) ? 'bg-rose-50/50 hover:bg-rose-100/60'
                          : 'bg-white hover:bg-ink-50'">
              <span v-if="isPreferred(m.name, r.name)" class="text-amber-600 font-black text-lg">★</span>
              <span v-else-if="isAllowed(m.name, r.name)" class="w-3 h-3 rounded-full bg-rose-500" />
              <span v-else class="w-2 h-2 rounded-full bg-ink-200" />
            </button>
          </div>
          <div v-if="!store.members.length" class="p-8 text-center text-sm text-ink-400">
            No music team members yet. Add Church Members with at least one Music Role Preference.
          </div>
        </div>

        <p class="text-[11px] italic text-ink-400 mt-3">
          Click an empty cell to mark as <strong>allowed</strong>. Click an allowed cell to promote to <strong>preferred</strong>. Click a preferred cell to clear.
        </p>
      </div>
    </div>
  </div>
</template>
