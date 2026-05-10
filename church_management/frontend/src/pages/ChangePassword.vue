<script setup>
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import { call } from "@/composables/useFrappeApi";
import { useSessionStore } from "@/stores/session";

const router = useRouter();
const session = useSessionStore();

const current = ref("");
const next1 = ref("");
const next2 = ref("");
const submitting = ref(false);
const errorMsg = ref("");
const done = ref(false);

const valid = computed(() =>
  current.value && next1.value && next1.value.length >= 8 && next1.value === next2.value
);

async function submit() {
  if (!valid.value || submitting.value) return;
  submitting.value = true;
  errorMsg.value = "";
  try {
    await call("church_management.api.music_team.change_password", {
      current_password: current.value, new_password: next1.value,
    });
    await session.refresh();
    done.value = true;
    setTimeout(() => router.replace(session.landingRoute()), 1200);
  } catch (e) {
    errorMsg.value = e.message || "Could not change password.";
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <div class="min-h-full flex items-center justify-center px-4 py-10">
    <div class="w-full max-w-md">
      <div class="bg-white rounded-2xl shadow-xl ring-1 ring-ink-100 overflow-hidden">
        <div class="bg-gradient-to-br from-rose-600 to-rose-800 text-white px-8 py-10 relative overflow-hidden">
          <div class="absolute -top-12 -right-12 w-40 h-40 rounded-full bg-white/10" />
          <div class="relative">
            <div class="inline-flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.25em] text-rose-200 mb-3">
              <span class="w-8 h-px bg-rose-300" />
              {{ session.tempPasswordPending ? "First sign-in" : "Account security" }}
            </div>
            <h1 class="font-display font-bold text-3xl tracking-tight">Update password.</h1>
            <p class="text-rose-100 text-sm mt-1.5" v-if="session.tempPasswordPending">
              Set a permanent password. Your temporary password will stop working after this.
            </p>
          </div>
        </div>

        <div v-if="!done">
          <form @submit.prevent="submit" class="px-8 py-7 space-y-5">
            <div>
              <label class="block text-[10px] font-black uppercase tracking-widest text-ink-700 mb-1.5">
                {{ session.tempPasswordPending ? "Temporary password" : "Current password" }}
              </label>
              <input v-model="current" type="password" autocomplete="current-password" required
                class="w-full px-4 py-2.5 bg-ink-50 border border-ink-200 rounded-xl text-sm focus:bg-white focus:border-rose-500 focus:ring-2 focus:ring-rose-100 outline-none" />
            </div>

            <div>
              <label class="block text-[10px] font-black uppercase tracking-widest text-ink-700 mb-1.5">New password</label>
              <input v-model="next1" type="password" autocomplete="new-password" minlength="8" required
                class="w-full px-4 py-2.5 bg-ink-50 border border-ink-200 rounded-xl text-sm focus:bg-white focus:border-rose-500 focus:ring-2 focus:ring-rose-100 outline-none" />
              <div class="text-[10px] text-ink-400 mt-1">At least 8 characters.</div>
            </div>

            <div>
              <label class="block text-[10px] font-black uppercase tracking-widest text-ink-700 mb-1.5">Confirm new password</label>
              <input v-model="next2" type="password" autocomplete="new-password" required
                class="w-full px-4 py-2.5 bg-ink-50 border border-ink-200 rounded-xl text-sm focus:bg-white focus:border-rose-500 focus:ring-2 focus:ring-rose-100 outline-none" />
              <div v-if="next2 && next1 !== next2" class="text-[10px] text-rose-600 mt-1">Passwords do not match.</div>
            </div>

            <div v-if="errorMsg" class="text-sm text-rose-700 bg-rose-50 border border-rose-200 rounded-lg px-4 py-2">{{ errorMsg }}</div>

            <button type="submit" :disabled="!valid || submitting"
              class="w-full px-6 py-3 rounded-xl text-sm font-bold shadow-sm transition-all"
              :class="valid && !submitting ? 'bg-rose-600 text-white hover:bg-rose-700' : 'bg-ink-200 text-ink-400 cursor-not-allowed'">
              {{ submitting ? "Saving…" : "Update password" }}
            </button>
          </form>
        </div>

        <div v-else class="px-8 py-10 text-center">
          <div class="w-12 h-12 mx-auto rounded-full bg-emerald-100 flex items-center justify-center text-emerald-700">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5"/></svg>
          </div>
          <h2 class="font-display font-bold text-xl text-ink-900 mt-4">Password updated.</h2>
          <p class="text-ink-600 text-sm mt-1.5">Redirecting…</p>
        </div>
      </div>
    </div>
  </div>
</template>
