<script setup>
import { ref } from "vue";
import { call } from "@/composables/useFrappeApi";

const email = ref("");
const submitting = ref(false);
const sent = ref(false);
const errorMsg = ref("");

async function submit() {
  if (!email.value || submitting.value) return;
  submitting.value = true;
  errorMsg.value = "";
  try {
    await call("church_management.api.music_team.request_password_reset", { email: email.value.trim().toLowerCase() });
    sent.value = true;
  } catch (e) {
    errorMsg.value = e.message || "Could not send reset email.";
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
              Password reset
            </div>
            <h1 class="font-display font-bold text-3xl tracking-tight">Forgot password?</h1>
            <p class="text-rose-100 text-sm mt-1.5">We'll email you a reset link.</p>
          </div>
        </div>

        <div v-if="!sent">
          <form @submit.prevent="submit" class="px-8 py-7 space-y-5">
            <div>
              <label class="block text-[10px] font-black uppercase tracking-widest text-ink-700 mb-1.5">Email</label>
              <input v-model="email" type="email" required
                class="w-full px-4 py-2.5 bg-ink-50 border border-ink-200 rounded-xl text-sm focus:bg-white focus:border-rose-500 focus:ring-2 focus:ring-rose-100 outline-none" />
            </div>

            <div v-if="errorMsg" class="text-sm text-rose-700 bg-rose-50 border border-rose-200 rounded-lg px-4 py-2">{{ errorMsg }}</div>

            <button type="submit" :disabled="submitting"
              class="w-full px-6 py-3 rounded-xl text-sm font-bold shadow-sm transition-all"
              :class="submitting ? 'bg-ink-200 text-ink-400 cursor-not-allowed' : 'bg-rose-600 text-white hover:bg-rose-700'">
              {{ submitting ? "Sending…" : "Send reset link" }}
            </button>

            <div class="text-center pt-2 border-t border-ink-100">
              <RouterLink to="/login" class="text-[11px] font-semibold text-rose-700 hover:underline">← Back to sign in</RouterLink>
            </div>
          </form>
        </div>

        <div v-else class="px-8 py-10 text-center">
          <div class="w-12 h-12 mx-auto rounded-full bg-emerald-100 flex items-center justify-center text-emerald-700">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5"/></svg>
          </div>
          <h2 class="font-display font-bold text-xl text-ink-900 mt-4">Check your inbox.</h2>
          <p class="text-ink-600 text-sm mt-1.5">If <strong>{{ email }}</strong> is registered, a reset link is on its way.</p>
          <RouterLink to="/login" class="inline-block mt-6 text-[11px] font-semibold text-rose-700 hover:underline">← Back to sign in</RouterLink>
        </div>
      </div>
    </div>
  </div>
</template>
