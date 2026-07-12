<script setup>
import { RouterView, useRoute } from "vue-router";
import AppSidebar from "@/components/AppSidebar.vue";
import BottomNav from "@/components/BottomNav.vue";
import { useWindowSize } from "@vueuse/core";
import { computed, onMounted } from "vue";
import { useSessionStore } from "@/stores/session";

const { width } = useWindowSize();
const isMobile = computed(() => width.value < 768);
const route = useRoute();
const session = useSessionStore();

const showChrome = computed(() => {
  if (route.meta?.chrome === false) return false;
  if (session.isGuest) return false;
  return true;
});

onMounted(() => { if (!session.ready) session.refresh(); });

// Self-healing staleness check: a tab restored from browser session-restore
// (or any cached shell) keeps running an old bundle forever. Compare the
// build version embedded in the page HTML against the deployed asset's
// Last-Modified and reload once when they diverge.
async function checkBuild() {
  const embedded = String(window.cmBuildVer || "");
  if (!embedded) return;
  try {
    const res = await fetch("/assets/church_management/dist/assets/index.js", {
      method: "HEAD",
      cache: "no-store",
    });
    const lm = res.headers.get("Last-Modified");
    if (!lm) return;
    const deployed = String(Math.floor(Date.parse(lm) / 1000));
    if (deployed !== embedded && !sessionStorage.getItem("cm_reload_" + deployed)) {
      sessionStorage.setItem("cm_reload_" + deployed, "1"); // guard against reload loops
      window.location.reload();
    }
  } catch {
    /* offline or blocked — try again next trigger */
  }
}

onMounted(() => {
  checkBuild();
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") checkBuild();
  });
  setInterval(checkBuild, 15 * 60 * 1000);
});
</script>

<template>
  <div v-if="!showChrome" class="h-[100dvh] overflow-y-auto bg-[#f0eee9]">
    <RouterView />
  </div>

  <div v-else class="flex h-[100dvh] bg-gray-50 overflow-hidden">
    <AppSidebar v-if="!isMobile" />
    <main class="flex-1 flex flex-col overflow-hidden">
      <div id="main-scroll-area" class="flex-1 overflow-y-auto" :class="isMobile ? 'pb-16' : ''">
        <RouterView />
      </div>
    </main>
    <BottomNav v-if="isMobile" />
  </div>
</template>
