import { createRouter, createWebHashHistory } from "vue-router";

const routes = [
  {
    path: "/",
    redirect: "/disbursements",
  },
  {
    path: "/disbursements",
    name: "DisbursementList",
    component: () => import("@/pages/DisbursementList.vue"),
  },
  {
    path: "/disbursements/:name",
    name: "DisbursementForm",
    component: () => import("@/pages/DisbursementForm.vue"),
    props: true,
  },
];

const router = createRouter({
  history: createWebHashHistory(),
  routes,
});

export default router;
