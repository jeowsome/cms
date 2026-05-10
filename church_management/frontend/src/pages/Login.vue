<script setup>
import { ref } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useSessionStore } from "@/stores/session";

const router = useRouter();
const route = useRoute();
const session = useSessionStore();

const email = ref("");
const password = ref("");
const showPw = ref(false);
const submitting = ref(false);
const errorMsg = ref("");

async function submit() {
  if (!email.value || !password.value || submitting.value) return;
  submitting.value = true;
  errorMsg.value = "";
  try {
    const id = email.value.trim();
    await session.login(id === "Administrator" ? id : id.toLowerCase(), password.value);
    const redirect = route.query.redirect;
    if (session.tempPasswordPending) {
      router.replace("/music/change-password");
    } else if (redirect && typeof redirect === "string") {
      router.replace(redirect);
    } else {
      router.replace(session.landingRoute());
    }
  } catch (e) {
    errorMsg.value = e.message || "Invalid email or password.";
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
              Jezreel Baptist Church
            </div>
            <h1 class="font-display font-bold text-3xl tracking-tight">Sign in.</h1>
            <p class="text-rose-100 text-sm mt-1.5">Church Management System</p>
          </div>
        </div>

        <form @submit.prevent="submit" class="px-8 py-7 space-y-5">
          <div>
            <label class="block text-[10px] font-black uppercase tracking-widest text-ink-700 mb-1.5">Email or username</label>
            <input v-model="email" type="text" autocomplete="username" required
              class="w-full px-4 py-2.5 bg-ink-50 border border-ink-200 rounded-xl text-sm focus:bg-white focus:border-rose-500 focus:ring-2 focus:ring-rose-100 outline-none" />
          </div>

          <div>
            <div class="flex items-baseline justify-between mb-1.5">
              <label class="text-[10px] font-black uppercase tracking-widest text-ink-700">Password</label>
              <button type="button" @click="showPw = !showPw" class="text-[10px] font-semibold text-rose-700 hover:underline">
                {{ showPw ? "Hide" : "Show" }}
              </button>
            </div>
            <input v-model="password" :type="showPw ? 'text' : 'password'" autocomplete="current-password" required
              class="w-full px-4 py-2.5 bg-ink-50 border border-ink-200 rounded-xl text-sm focus:bg-white focus:border-rose-500 focus:ring-2 focus:ring-rose-100 outline-none" />
          </div>

          <div v-if="errorMsg" class="text-sm text-rose-700 bg-rose-50 border border-rose-200 rounded-lg px-4 py-2">{{ errorMsg }}</div>

          <button type="submit" :disabled="submitting"
            class="w-full px-6 py-3 rounded-xl text-sm font-bold shadow-sm transition-all"
            :class="submitting ? 'bg-ink-200 text-ink-400 cursor-not-allowed' : 'bg-rose-600 text-white hover:bg-rose-700'">
            {{ submitting ? "Signing in…" : "Sign in" }}
          </button>

          <div class="flex items-center justify-between pt-2 border-t border-ink-100">
            <RouterLink to="/forgot-password" class="text-[11px] font-semibold text-ink-500 hover:text-rose-700">Forgot password?</RouterLink>
            <RouterLink to="/register" class="text-[11px] font-semibold text-rose-700 hover:underline">Music team registration →</RouterLink>
          </div>
        </form>
      </div>

      <p class="text-center mt-4 text-[10px] uppercase tracking-widest text-ink-400 font-bold">JBC CMS</p>
    </div>
  </div>
</template>
