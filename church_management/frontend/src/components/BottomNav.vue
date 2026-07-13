<script setup>
import { RouterLink, useRoute } from "vue-router";
import { useScroll } from "@vueuse/core";
import { onMounted, ref, watch, computed } from "vue";
import { useSessionStore } from "@/stores/session";

const route = useRoute();
const session = useSessionStore();
const scrollArea = ref(null);
const isVisible = ref(true); // start visible so they aren't confused

onMounted(() => {
  scrollArea.value = document.getElementById("main-scroll-area");
});

const { y, directions } = useScroll(scrollArea);

watch(() => directions.bottom, (val) => {
  // User swiping upward (scrolling down to bottom) -> show nav
  if (val) isVisible.value = true;
});

watch(() => directions.top, (val) => {
  // User swiping downward (scrolling up to top) -> hide nav
  if (val) isVisible.value = false;
});

watch(y, (val) => {
  // Always show if near the top so they aren't trapped
  if (val < 50) isVisible.value = true;
});

const navItems = computed(() => {
  const items = [];

  // Member-only mobile nav: schedule + profile.
  if (session.isMemberOnly) {
    items.push({ label: "Schedule", to: "/music/me", icon: "calendar" });
    items.push({ label: "Profile", to: "/music/profile", icon: "user" });
    return items;
  }

  if (session.hasFinanceAccess) {
    items.push({ label: "Collections", to: "/collections", icon: "inbox" });
    items.push({ label: "Disbursements", to: "/disbursements", icon: "wallet" });
    items.push({ label: "Templates", to: "/templates", icon: "layers" });
  }
  if (session.hasMusicAccess) {
    items.push({ label: "Music", to: "/music/lineup", icon: "music" });
    if (session.isWorshipLeader) {
      items.push({ label: "Worship", to: "/music/worship", icon: "songs" });
    }
  }
  return items;
});

function isActive(path) {
  return route.path.startsWith(path);
}
</script>

<template>
  <nav
    v-if="navItems.length"
    class="fixed bottom-0 inset-x-0 bg-white border-t border-gray-200 z-[40] safe-bottom transition-transform duration-300 ease-in-out"
    :class="isVisible ? 'translate-y-0' : 'translate-y-full'"
  >
    <div class="flex items-center justify-around h-16">
      <RouterLink
        v-for="item in navItems"
        :key="item.to"
        :to="item.to"
        class="flex flex-col items-center justify-center flex-1 h-full gap-0.5 transition-colors"
        :class="
          isActive(item.to)
            ? 'text-brand-600'
            : 'text-gray-400 active:text-gray-600'
        "
      >
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path
            v-if="item.icon === 'inbox'"
            stroke-linecap="round" stroke-linejoin="round"
            d="M2.25 13.5h3.86a2.25 2.25 0 0 1 2.012 1.244l.256.512a2.25 2.25 0 0 0 2.013 1.244h3.218a2.25 2.25 0 0 0 2.013-1.244l.256-.512a2.25 2.25 0 0 1 2.013-1.244h3.859m-19.5.338V18a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18v-4.162c0-.224-.034-.447-.1-.661l-2.074-6.742a2.25 2.25 0 0 0-2.15-1.588H6.574a2.25 2.25 0 0 0-2.15 1.588l-2.075 6.742a2.25 2.25 0 0 0-.1.661Z"
          />
          <path
            v-else-if="item.icon === 'wallet'"
            stroke-linecap="round" stroke-linejoin="round"
            d="M21 12a2.25 2.25 0 0 0-2.25-2.25H15a3 3 0 1 1-6 0H5.25A2.25 2.25 0 0 0 3 12m18 0v6a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 18v-6m18 0V9M3 12V9m18 0a2.25 2.25 0 0 0-2.25-2.25H5.25A2.25 2.25 0 0 0 3 9m18 0V6a2.25 2.25 0 0 0-2.25-2.25H5.25A2.25 2.25 0 0 0 3 6v3"
          />
          <path
            v-else-if="item.icon === 'layers'"
            stroke-linecap="round" stroke-linejoin="round"
            d="M6.429 9.75 2.25 12l4.179 2.25m0-4.5 5.571 3 5.571-3m-11.142 0L2.25 7.5 12 2.25l9.75 5.25-4.179 2.25m0 0L21.75 12l-4.179 2.25m0 0 4.179 2.25L12 21.75 2.25 16.5l4.179-2.25m11.142 0-5.571 3-5.571-3"
          />
          <path
            v-else-if="item.icon === 'music' || item.icon === 'songs'"
            stroke-linecap="round" stroke-linejoin="round"
            d="M9 9l10.5-3m0 6.553v3.75a2.25 2.25 0 0 1-1.632 2.163l-1.32.377a1.803 1.803 0 1 1-.99-3.467l2.31-.66a2.25 2.25 0 0 0 1.632-2.163zm0 0V2.25L9 5.25v10.303m0 0v3.75a2.25 2.25 0 0 1-1.632 2.163l-1.32.377a1.803 1.803 0 0 1-.99-3.467l2.31-.66A2.25 2.25 0 0 0 9 15.553z"
          />
          <path
            v-else-if="item.icon === 'calendar'"
            stroke-linecap="round" stroke-linejoin="round"
            d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5"
          />
          <path
            v-else-if="item.icon === 'user'"
            stroke-linecap="round" stroke-linejoin="round"
            d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.5 20.25a7.5 7.5 0 0 1 15 0v.75a.75.75 0 0 1-.75.75H5.25a.75.75 0 0 1-.75-.75v-.75Z"
          />
        </svg>
        <span class="text-[10px] font-medium leading-none">{{ item.label }}</span>
        <!-- Active indicator dot -->
        <div
          v-if="isActive(item.to)"
          class="absolute bottom-1 w-1 h-1 rounded-full bg-brand-600"
        />
      </RouterLink>
    </div>
  </nav>
</template>
