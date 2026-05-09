import { createRouter, createWebHashHistory } from "vue-router";

const routes = [
  { path: "/", redirect: "/disbursements" },
  { path: "/disbursements", name: "DisbursementList", component: () => import("@/pages/DisbursementList.vue") },
  { path: "/disbursements/:name", name: "DisbursementForm", component: () => import("@/pages/DisbursementForm.vue"), props: true },

  { path: "/music", redirect: "/music/lineup" },
  { path: "/music/lineup", name: "MusicLineup", component: () => import("@/pages/MusicLineup.vue") },
  { path: "/music/roles", name: "MusicRoles", component: () => import("@/pages/MusicRoles.vue") },
  { path: "/music/unavail", name: "MusicUnavail", component: () => import("@/pages/MusicUnavail.vue") },
  { path: "/music/me", name: "MusicMember", component: () => import("@/pages/MusicMember.vue") },
  { path: "/music/notify", name: "MusicNotify", component: () => import("@/pages/MusicNotify.vue") },
];

const router = createRouter({
  history: createWebHashHistory(),
  routes,
});

export default router;
