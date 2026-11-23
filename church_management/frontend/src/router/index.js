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
  { path: "/overdue", name: "OverdueReview", component: () => import("@/pages/OverdueReview.vue"), meta: { requiresAuth: true, requiresFinance: true } },
  { path: "/creditors", name: "Creditors", component: () => import("@/pages/Creditors.vue"), meta: { requiresAuth: true, requiresFinance: true } },
  { path: "/fund-summary", name: "FundSummary", component: () => import("@/pages/FundSummary.vue"), meta: { requiresAuth: true, requiresFinance: true } },
  { path: "/audit-log", name: "AuditLog", component: () => import("@/pages/AuditLog.vue"), meta: { requiresAuth: true, requiresFinance: true } },
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

// Returns where to send a user who may not open `to`, or null when allowed.
function accessRedirect(to, session) {
  if (to.meta.requiresAuth && session.isGuest) {
    return { name: "Login", query: { redirect: to.fullPath } };
  }
  const denied =
    (to.meta.requiresFinance && !session.hasFinanceAccess) ||
    (to.meta.requiresDonation && !session.hasDonationAccess) ||
    (to.meta.requiresMusic && !session.hasMusicAccess) ||
    (to.meta.requiresWorshipLeader && !session.isWorshipLeader) ||
    (to.meta.requiresLeader && !session.isLeader) ||
    (to.meta.requiresRoleAdmin && !session.isLeader && !session.isDonationAdmin);
  return denied ? session.landingRoute() : null;
}

// The last section a user opened (e.g. /collections, /music/worship), kept per
// user so the Member Portal link reopens it instead of the role default.
const LAST_KEY = (user) => `cm-last-section:${user}`;

function sectionOf(path) {
  const parts = path.split("?")[0].split("/").filter(Boolean);
  // Detail pages (/collections/<name>, /collections/new) reopen their list
  const depth = parts[0] === "music" || parts[0] === "admin" ? 2 : 1;
  return "/" + parts.slice(0, depth).join("/");
}

/** Where a signed-in user lands: their last section if still allowed, else the role default. */
export function homeRoute(session) {
  if (session.tempPasswordPending) return session.landingRoute();
  let last = null;
  try {
    last = localStorage.getItem(LAST_KEY(session.user));
  } catch {}
  if (last) {
    const target = router.resolve(last);
    if (target.matched.length && !target.meta.public && target.meta.chrome !== false && !accessRedirect(target, session)) {
      return target.fullPath;
    }
  }
  return session.landingRoute();
}

router.afterEach((to) => {
  const session = useSessionStore();
  if (session.isGuest || to.meta.public || to.meta.chrome === false || !to.matched.length) return;
  try {
    localStorage.setItem(LAST_KEY(session.user), sectionOf(to.fullPath));
  } catch {}
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
      const landing = homeRoute(session);
      if (landing !== "/login") return landing;
    }
    return true;
  }

  return accessRedirect(to, session) ?? true;
});

export default router;
