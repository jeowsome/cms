<script setup>
import { ref, watch } from "vue";
import { useQuery, useQueryCache } from "@pinia/colada";
import { call } from "@/composables/useFrappeApi";
import AppButton from "@/components/AppButton.vue";

/**
 * Management of the Donation Purpose dropdown — open to every donation user;
 * the dedup check is the guardrail, not the role. New names are checked
 * server-side: exact duplicates (case/space-insensitive) are rejected
 * outright; near-matches (plurals, misspellings) come back as a
 * "did you mean" list that must be explicitly overridden.
 */
const props = defineProps({
  isOpen: { type: Boolean, default: false },
});
const emit = defineEmits(["close"]);

const queryCache = useQueryCache();
const newName = ref("");
const similar = ref([]); // near-matches flagged by the server for the pending name
const pendingName = ref("");
const adding = ref(false);
const errorMsg = ref("");
const inputEl = ref(null);

const { data: purposes, refetch } = useQuery({
  key: ["donation-purposes"],
  query: () => call("church_management.api.donation.get_purposes"),
});

watch(
  () => props.isOpen,
  (open) => {
    if (!open) return;
    newName.value = "";
    errorMsg.value = "";
    similar.value = [];
    pendingName.value = "";
    refetch();
    requestAnimationFrame(() => inputEl.value?.focus());
  }
);

async function add(force = false) {
  const name = (force ? pendingName.value : newName.value).trim();
  if (!name) return;
  errorMsg.value = "";
  adding.value = true;
  try {
    const r = await call("church_management.api.donation.create_purpose", {
      purpose_name: name,
      force: force ? 1 : 0,
    });
    if (r.created) {
      newName.value = "";
      similar.value = [];
      pendingName.value = "";
      refetch();
      queryCache.invalidateQueries({ key: ["donation-purposes"] });
      inputEl.value?.focus();
    } else {
      // Server flagged near-duplicates — ask before creating.
      similar.value = r.similar || [];
      pendingName.value = name;
    }
  } catch (e) {
    similar.value = [];
    pendingName.value = "";
    errorMsg.value = e.message || "Failed to add purpose.";
  } finally {
    adding.value = false;
  }
}

function cancelPending() {
  similar.value = [];
  pendingName.value = "";
  inputEl.value?.focus();
}
</script>

<template>
  <Teleport to="body">
    <div v-if="isOpen" class="fixed inset-0 z-[60] flex items-end sm:items-center justify-center p-4">
      <div class="absolute inset-0 bg-gray-900/40 backdrop-blur-sm" @click="!adding && emit('close')" />
      <div class="relative bg-white rounded-2xl shadow-2xl w-full max-w-md p-5 anim-pop max-h-[90dvh] overflow-y-auto">
        <div class="flex items-start justify-between gap-3">
          <div>
            <h3 class="text-base font-bold text-gray-900">Donation purposes</h3>
            <p class="text-xs text-gray-500 mt-0.5">
              What departments can pick when recording an entry
            </p>
          </div>
          <button
            type="button"
            class="w-8 h-8 rounded-lg flex items-center justify-center text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors shrink-0"
            aria-label="Close"
            @click="!adding && emit('close')"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div v-if="errorMsg" class="mt-3 p-2.5 rounded-xl bg-red-50 text-red-700 text-xs font-semibold">
          {{ errorMsg }}
        </div>

        <!-- Add form -->
        <form class="mt-4 flex gap-2" @submit.prevent="add(false)">
          <input
            ref="inputEl"
            v-model="newName"
            type="text"
            placeholder="e.g. Contribution"
            class="cm-field flex-1"
            :disabled="adding"
          />
          <AppButton type="submit" size="sm" :loading="adding" :disabled="!newName.trim()">Add</AppButton>
        </form>

        <!-- Did-you-mean flag -->
        <div v-if="similar.length" class="mt-3 p-3 rounded-xl bg-amber-50 border border-amber-200 text-xs">
          <p class="font-semibold text-amber-800">
            “{{ pendingName }}” looks like an existing purpose:
          </p>
          <ul class="mt-1.5 space-y-0.5">
            <li v-for="s in similar" :key="s" class="font-bold text-amber-900">• {{ s }}</li>
          </ul>
          <p class="mt-2 text-amber-700">Use the existing one, or create it anyway if it really is different.</p>
          <div class="mt-2.5 flex gap-2">
            <AppButton type="button" variant="secondary" size="sm" :disabled="adding" @click="cancelPending">
              Never mind
            </AppButton>
            <AppButton type="button" size="sm" :loading="adding" @click="add(true)">
              Create anyway
            </AppButton>
          </div>
        </div>

        <!-- Existing purposes -->
        <div class="mt-4">
          <p class="text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1.5">
            Existing ({{ (purposes || []).length }})
          </p>
          <p v-if="!(purposes || []).length" class="text-sm text-gray-400 py-3 text-center">
            No purposes yet — add the first one above.
          </p>
          <div v-else class="flex flex-wrap gap-1.5">
            <span
              v-for="p in purposes"
              :key="p.name"
              class="px-2.5 py-1 rounded-lg text-xs font-semibold inline-flex items-center gap-1.5"
              :class="p.is_mission ? 'bg-amber-50 text-amber-800 ring-1 ring-amber-200' : 'bg-gray-100 text-gray-700'"
              :title="p.is_mission ? 'Mission fund — entries need admin approval and post to the mission ledger' : ''"
            >
              {{ p.name }}
              <span v-if="p.is_mission" class="text-[9px] font-black uppercase tracking-wider text-amber-600">Mission</span>
            </span>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
