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

  // Donations (department users; Pasig Admin / Administrator see all)
  { path: "/donations", name: "DonationList", component: () => import("@/pages/DonationList.vue"), meta: { requiresAuth: true, requiresDonation: true } },
  { path: "/donations/:name", name: "DonationForm", component: () => import("@/pages/DonationForm.vue"), props: true, meta: { requiresAuth: true, requiresDonation: true } },

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

  // Admin / access management — Music Team Leader, Donation Admin (Pasig Admin) or Admin.
  { path: "/admin/roles", name: "AdminRoles", component: () => import("@/pages/AdminRoles.vue"), meta: { requiresAuth: true, requiresRoleAdmin: true } },
];

const router = createRouter({
  history: createWebHashHistory(),
  routes,
});

// Recover from lazy chunks deleted by a newer deploy: jump to the intended
// route and force a full reload so the fresh bundle is fetched. The
// sessionStorage flag prevents a reload loop if the failure is permanent.
router.onError((error, to) => {
  const chunkFailed = /error loading dynamically imported module|Failed to fetch dynamically imported module|Importing a module script failed/i.test(
    String(error?.message || error)
  );
  if (!chunkFailed) return;
  const key = "cm-chunk-reload";
  if (sessionStorage.getItem(key) === to.fullPath) return;
  sessionStorage.setItem(key, to.fullPath);
  window.location.hash = "#" + to.fullPath;
  window.location.reload();
});

// Once the route loads fine, clear the reload marker so a future deploy can
// trigger recovery again.
router.afterEach((to) => {
  if (sessionStorage.getItem("cm-chunk-reload") === to.fullPath) {
    sessionStorage.removeItem("cm-chunk-reload");
  }
  sessionStorage.removeItem("cm-preload-reload");
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
    // If logged-in user lands on a public page, send them to their landing.
    // A landing of "/login" (account with no SPA roles) must fall through,
    // or this guard would redirect /login → /login forever.
    if (!session.isGuest && (to.name === "Login" || to.name === "ForgotPassword")) {
      const landing = session.landingRoute();
      if (landing !== "/login") return landing;
    }
    return true;
  }

  if (to.meta.requiresAuth && session.isGuest) {
    return { name: "Login", query: { redirect: to.fullPath } };
  }
  if (to.meta.requiresFinance && !session.hasFinanceAccess) {
    return session.landingRoute();
  }
  if (to.meta.requiresDonation && !session.hasDonationAccess) {
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
  if (to.meta.requiresRoleAdmin && !session.isLeader && !session.isDonationAdmin) {
    return session.landingRoute();
  }
  return true;
});

export default router;
