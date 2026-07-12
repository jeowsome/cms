import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { call } from "@/composables/useFrappeApi";

export const useSessionStore = defineStore("session", () => {
  const user = ref(null);
  const roles = ref([]);
  const churchMember = ref(null);
  const tempPasswordPending = ref(false);
  const ready = ref(false);

  // Role flags returned by whoami(). Keep these in sync with
  // church_management/api/permissions.py role_flags().
  const flags = ref({
    is_admin: false,
    is_finance: false,
    is_music_leader: false,
    is_worship_leader: false,
    is_music_member: false,
    has_music_access: false,
    has_finance_access: false,
  });

  const isGuest = computed(() => !user.value || user.value === "Guest");
  const isAdmin = computed(() => flags.value.is_admin);
  const isFinance = computed(() => flags.value.is_finance);
  const isLeader = computed(() => flags.value.is_music_leader);
  const isWorshipLeader = computed(() => flags.value.is_worship_leader);
  // Member flag: roles that grant "music team area" access. Worship Leader and
  // Music Team Leader implicitly satisfy this; admin too.
  const isMusicMember = computed(() => flags.value.is_music_member);
  const hasMusicAccess = computed(() => flags.value.has_music_access);
  const hasFinanceAccess = computed(() => flags.value.has_finance_access);
  // True only when a user has *only* slim-member privileges and no leader role.
  const isMemberOnly = computed(
    () =>
      flags.value.is_music_member &&
      !flags.value.is_music_leader &&
      !flags.value.is_worship_leader &&
      !flags.value.is_admin
  );

  function applyWhoami(r) {
    user.value = r.user;
    roles.value = r.roles || [];
    tempPasswordPending.value = !!r.temp_password_pending;
    churchMember.value = r.church_member || null;
    flags.value = {
      is_admin: !!r.is_admin,
      is_finance: !!r.is_finance,
      is_music_leader: !!r.is_music_leader,
      is_worship_leader: !!r.is_worship_leader,
      is_music_member: !!r.is_music_member,
      has_music_access: !!r.has_music_access,
      has_finance_access: !!r.has_finance_access,
    };
  }

  function reset() {
    user.value = "Guest";
    roles.value = [];
    churchMember.value = null;
    tempPasswordPending.value = false;
    flags.value = {
      is_admin: false,
      is_finance: false,
      is_music_leader: false,
      is_worship_leader: false,
      is_music_member: false,
      has_music_access: false,
      has_finance_access: false,
    };
  }

  async function refresh() {
    try {
      const r = await call("church_management.api.music_team.whoami");
      applyWhoami(r);
    } catch (e) {
      // Transient failures (server restarting, network blip) must not wipe an
      // authenticated session's nav; only an explicit auth rejection — or
      // never having been authenticated — resets to guest.
      if (e.status === 401 || e.status === 403 || !user.value || user.value === "Guest") {
        reset();
      }
    } finally {
      ready.value = true;
    }
    return { user: user.value, roles: roles.value };
  }

  async function login(email, password) {
    const r = await call("church_management.api.music_team.login", { email, password });
    // login returns roles + temp flag but not the full role-flag set; refresh
    // afterwards so we always have the canonical permission view.
    user.value = r.user;
    roles.value = r.roles || [];
    tempPasswordPending.value = !!r.temp_password_pending;
    await refresh();
    return r;
  }

  async function logout() {
    try {
      await call("church_management.api.music_team.logout");
    } catch {}
    reset();
  }

  function landingRoute() {
    if (tempPasswordPending.value) return "/music/change-password";
    // Priority: admin → music tools (lineup) ; worship leader → worship plan ;
    // music leader → registrations queue ; member-only → personal profile ;
    // finance-only → disbursements.
    if (flags.value.is_admin) return "/music/lineup";
    if (flags.value.is_worship_leader) return "/music/worship";
    if (flags.value.is_music_leader) return "/music/registrations";
    if (flags.value.is_music_member) return "/music/profile";
    if (flags.value.is_finance) return "/disbursements";
    return "/login";
  }

  return {
    user, roles, churchMember, tempPasswordPending, ready, flags,
    isGuest, isAdmin, isFinance, isLeader, isWorshipLeader, isMusicMember,
    isMemberOnly, hasMusicAccess, hasFinanceAccess,
    refresh, login, logout, landingRoute,
  };
});
