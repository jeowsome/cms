import { createRouter, createWebHashHistory } from "vue-router";
import { useSessionStore } from "@/stores/session";

const routes = [
  { path: "/", redirect: () => "/login" },

  // Public
  { path: "/login", name: "Login", component: () => import("@/pages/Login.vue"), meta: { public: true, chrome: false } },
  { path: "/forgot-password", name: "ForgotPassword", component: () => import("@/pages/ForgotPassword.vue"), meta: { public: true, chrome: false } },
  { path: "/register", name: "MusicRegister", component: () => import("@/pages/MusicRegister.vue"), meta: { public: true, chrome: false } },

  // Collections (Finance Team or Admin)
  { path: "/collections", name: "CollectionList", component: () => import("@/pages/CollectionList.vue"), meta: { requiresAuth: true, requiresFinance: true } },
  { path: "/collections/:name", name: "CollectionForm", component: () => import("@/pages/CollectionForm.vue"), props: true, meta: { requiresAuth: true, requiresFinance: true } },

  // Church Members (Finance Team or Admin)
  { path: "/members", name: "MemberList", component: () => import("@/pages/MemberList.vue"), meta: { requiresAuth: true, requiresFinance: true } },

  // Disbursements (Finance Team or Admin)
  { path: "/disbursements", name: "DisbursementList", component: () => import("@/pages/DisbursementList.vue"), meta: { requiresAuth: true, requiresFinance: true } },
  { path: "/disbursements/:name", name: "DisbursementForm", component: () => import("@/pages/DisbursementForm.vue"), props: true, meta: { requiresAuth: true, requiresFinance: true } },

  // Disbursement Templates (Finance Team or Admin)
  { path: "/templates", name: "TemplateList", component: () => import("@/pages/TemplateList.vue"), meta: { requiresAuth: true, requiresFinance: true } },
  { path: "/templates/:name", name: "TemplateForm", component: () => import("@/pages/TemplateForm.vue"), props: true, meta: { requiresAuth: true, requiresFinance: true } },

  // Music team (any music role required)
  { path: "/music", redirect: "/music/lineup" },
  { path: "/music/lineup", name: "MusicLineup", component: () => import("@/pages/MusicLineup.vue"), meta: { requiresAuth: true, requiresMusic: true, requiresWorshipLeader: true } },
  { path: "/music/roles", name: "MusicRoles", component: () => import("@/pages/MusicRoles.vue"), meta: { requiresAuth: true, requiresMusic: true, requiresLeader: true } },
  { path: "/music/unavail", name: "MusicUnavail", component: () => import("@/pages/MusicUnavail.vue"), meta: { requiresAuth: true, requiresMusic: true, requiresLeader: true } },
  { path: "/music/me", name: "MusicMember", component: () => import("@/pages/MusicMember.vue"), meta: { requiresAuth: true, requiresMusic: true } },
  { path: "/music/notify", name: "MusicNotify", component: () => import("@/pages/MusicNotify.vue"), meta: { requiresAuth: true, requiresMusic: true, requiresLeader: true } },
  { path: "/music/registrations", name: "MusicRegistrations", component: () => import("@/pages/MusicRegistrations.vue"), meta: { requiresAuth: true, requiresMusic: true, requiresLeader: true } },
  { path: "/music/worship", name: "MusicWorship", component: () => import("@/pages/MusicWorship.vue"), meta: { requiresAuth: true, requiresMusic: true, requiresWorshipLeader: true } },
  { path: "/music/profile", name: "MusicProfile", component: () => import("@/pages/MusicProfile.vue"), meta: { requiresAuth: true, requiresMusic: true } },
  { path: "/music/change-password", name: "ChangePassword", component: () => import("@/pages/ChangePassword.vue"), meta: { requiresAuth: true, chrome: false } },

  // Admin / access management — Music Team Leader or Admin only.
  { path: "/admin/roles", name: "AdminRoles", component: () => import("@/pages/AdminRoles.vue"), meta: { requiresAuth: true, requiresLeader: true } },
];

const router = createRouter({
  history: createWebHashHistory(),
  routes,
});

router.beforeEach(async (to) => {
  const session = useSessionStore();
  if (!session.ready) {
    await session.refresh();
  }

  // If logged in and forced to change temp password, lock to /music/change-password
  if (
    !session.isGuest &&
    session.tempPasswordPending &&
    to.name !== "ChangePassword" &&
    to.name !== "Login"
  ) {
    return { name: "ChangePassword" };
  }

  if (to.meta.public) {
    // If logged-in user lands on a public page, send them to their landing
    if (!session.isGuest && (to.name === "Login" || to.name === "ForgotPassword")) {
      return session.landingRoute();
    }
    return true;
  }

  if (to.meta.requiresAuth && session.isGuest) {
    return { name: "Login", query: { redirect: to.fullPath } };
  }
  if (to.meta.requiresFinance && !session.hasFinanceAccess) {
    return session.landingRoute();
  }
  if (to.meta.requiresMusic && !session.hasMusicAccess) {
    return session.landingRoute();
  }
  if (to.meta.requiresWorshipLeader && !session.isWorshipLeader) {
    return session.landingRoute();
  }
  if (to.meta.requiresLeader && !session.isLeader) {
    return session.landingRoute();
  }
  return true;
});

export default router;
