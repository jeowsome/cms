<script setup>
import { RouterView, useRoute, useRouter } from "vue-router";
import AppSidebar from "@/components/AppSidebar.vue";
import BottomNav from "@/components/BottomNav.vue";
import { useWindowSize } from "@vueuse/core";
import { computed, onMounted, ref } from "vue";
import { useSessionStore } from "@/stores/session";
import { useRealtime } from "@/composables/useRealtime";

const { width } = useWindowSize();
const isMobile = computed(() => width.value < 768);
const route = useRoute();
const router = useRouter();
const session = useSessionStore();

// Mission-donation approval alerts. The server targets these events at
// donation admins only; the flag check is a second line of defense.
const toasts = ref([]);
let toastSeq = 0;

function dismissToast(id) {
  toasts.value = toasts.value.filter((t) => t.id !== id);
}

function openToast(t) {
  dismissToast(t.id);
  router.push(`/donations/${encodeURIComponent(t.donation)}`);
}

function peso(v) {
  return new Intl.NumberFormat("en-PH", { style: "currency", currency: "PHP" }).format(v || 0);
}

useRealtime("donation_event", (msg) => {
  if (!session.isDonationAdmin) return;
  if (msg?.action !== "mission_pending") return;
  const p = msg.payload || {};
  const id = ++toastSeq;
  toasts.value.push({ id, ...p });
  setTimeout(() => dismissToast(id), 12000);
});

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

  <!-- Mission approval notifications (donation admins) -->
  <Teleport to="body">
    <div v-if="toasts.length" class="fixed top-4 right-4 z-[70] space-y-2 w-[calc(100vw-2rem)] max-w-sm">
      <div
        v-for="t in toasts"
        :key="t.id"
        class="bg-white rounded-2xl shadow-2xl ring-1 ring-amber-200 p-4 anim-pop cursor-pointer hover:ring-amber-300 transition"
        @click="openToast(t)"
      >
        <div class="flex items-start gap-3">
          <div class="w-9 h-9 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center shrink-0">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
            </svg>
          </div>
          <div class="min-w-0 flex-1">
            <p class="text-sm font-bold text-gray-900">Mission donation needs approval</p>
            <p class="text-xs text-gray-500 mt-0.5 truncate">
              {{ t.department }} · {{ t.year }} — {{ t.count }} {{ t.count === 1 ? "entry" : "entries" }},
              <span class="font-semibold text-gray-700">{{ peso(t.total) }}</span>
            </p>
            <p class="text-[11px] text-gray-400 mt-0.5 truncate">by {{ t.by }} · tap to review</p>
          </div>
          <button
            class="w-6 h-6 rounded-md flex items-center justify-center text-gray-300 hover:text-gray-500 shrink-0"
            aria-label="Dismiss"
            @click.stop="dismissToast(t.id)"
          >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
