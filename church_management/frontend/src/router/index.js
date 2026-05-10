import { createRouter, createWebHashHistory } from "vue-router";
import { useSessionStore } from "@/stores/session";

const routes = [
  { path: "/", redirect: () => "/login" },

  // Public
  { path: "/login", name: "Login", component: () => import("@/pages/Login.vue"), meta: { public: true, chrome: false } },
  { path: "/forgot-password", name: "ForgotPassword", component: () => import("@/pages/ForgotPassword.vue"), meta: { public: true, chrome: false } },
  { path: "/register", name: "MusicRegister", component: () => import("@/pages/MusicRegister.vue"), meta: { public: true, chrome: false } },

  // Disbursements (auth required)
  { path: "/disbursements", name: "DisbursementList", component: () => import("@/pages/DisbursementList.vue"), meta: { requiresAuth: true } },
  { path: "/disbursements/:name", name: "DisbursementForm", component: () => import("@/pages/DisbursementForm.vue"), props: true, meta: { requiresAuth: true } },

  // Music team
  { path: "/music", redirect: "/music/lineup" },
  { path: "/music/lineup", name: "MusicLineup", component: () => import("@/pages/MusicLineup.vue"), meta: { requiresAuth: true } },
  { path: "/music/roles", name: "MusicRoles", component: () => import("@/pages/MusicRoles.vue"), meta: { requiresAuth: true } },
  { path: "/music/unavail", name: "MusicUnavail", component: () => import("@/pages/MusicUnavail.vue"), meta: { requiresAuth: true } },
  { path: "/music/me", name: "MusicMember", component: () => import("@/pages/MusicMember.vue"), meta: { requiresAuth: true } },
  { path: "/music/notify", name: "MusicNotify", component: () => import("@/pages/MusicNotify.vue"), meta: { requiresAuth: true } },
  { path: "/music/registrations", name: "MusicRegistrations", component: () => import("@/pages/MusicRegistrations.vue"), meta: { requiresAuth: true, requiresLeader: true } },
  { path: "/music/profile", name: "MusicProfile", component: () => import("@/pages/MusicProfile.vue"), meta: { requiresAuth: true } },
  { path: "/music/change-password", name: "ChangePassword", component: () => import("@/pages/ChangePassword.vue"), meta: { requiresAuth: true, chrome: false } },
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
  if (to.meta.requiresLeader && !session.isLeader) {
    return session.landingRoute();
  }
  return true;
});

export default router;
