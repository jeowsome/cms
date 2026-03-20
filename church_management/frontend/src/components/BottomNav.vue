<script setup>
import { RouterLink, useRoute } from "vue-router";
import { useScroll } from "@vueuse/core";
import { onMounted, ref, watch } from "vue";

const route = useRoute();
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

const navItems = [
  { label: "Disbursements", to: "/disbursements", icon: "wallet" },
];

function isActive(path) {
  return route.path.startsWith(path);
}
</script>

<template>
  <nav 
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
            v-if="item.icon === 'wallet'"
            stroke-linecap="round" stroke-linejoin="round"
            d="M21 12a2.25 2.25 0 0 0-2.25-2.25H15a3 3 0 1 1-6 0H5.25A2.25 2.25 0 0 0 3 12m18 0v6a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 18v-6m18 0V9M3 12V9m18 0a2.25 2.25 0 0 0-2.25-2.25H5.25A2.25 2.25 0 0 0 3 9m18 0V6a2.25 2.25 0 0 0-2.25-2.25H5.25A2.25 2.25 0 0 0 3 6v3"
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
