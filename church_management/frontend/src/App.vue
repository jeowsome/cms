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
