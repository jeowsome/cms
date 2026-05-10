import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { call } from "@/composables/useFrappeApi";

export const useSessionStore = defineStore("session", () => {
  const user = ref(null);
  const roles = ref([]);
  const tempPasswordPending = ref(false);
  const ready = ref(false);

  const isGuest = computed(() => !user.value || user.value === "Guest");
  const isLeader = computed(
    () => roles.value.includes("Music Team Leader") || roles.value.includes("System Manager")
  );
  const isMusicMember = computed(() => roles.value.includes("Music Team Member"));

  async function refresh() {
    try {
      const r = await call("church_management.api.music_team.whoami");
      user.value = r.user;
      roles.value = r.roles || [];
      tempPasswordPending.value = !!r.temp_password_pending;
    } catch (e) {
      user.value = "Guest";
      roles.value = [];
      tempPasswordPending.value = false;
    } finally {
      ready.value = true;
    }
    return { user: user.value, roles: roles.value };
  }

  async function login(email, password) {
    const r = await call("church_management.api.music_team.login", { email, password });
    user.value = r.user;
    roles.value = r.roles || [];
    tempPasswordPending.value = !!r.temp_password_pending;
    return r;
  }

  async function logout() {
    try {
      await call("church_management.api.music_team.logout");
    } catch {}
    user.value = "Guest";
    roles.value = [];
    tempPasswordPending.value = false;
  }

  function landingRoute() {
    if (tempPasswordPending.value) return "/music/change-password";
    if (isLeader.value) return "/music/registrations";
    if (isMusicMember.value) return "/music/profile";
    return "/disbursements";
  }

  return {
    user, roles, tempPasswordPending, ready,
    isGuest, isLeader, isMusicMember,
    refresh, login, logout, landingRoute,
  };
});
