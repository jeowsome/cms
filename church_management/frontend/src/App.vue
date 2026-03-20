<script setup>
import { RouterView } from "vue-router";
import AppSidebar from "@/components/AppSidebar.vue";
import BottomNav from "@/components/BottomNav.vue";
import { useWindowSize } from "@vueuse/core";
import { computed } from "vue";

const { width } = useWindowSize();
const isMobile = computed(() => width.value < 768);
</script>

<template>
  <div class="flex h-[100dvh] bg-gray-50 overflow-hidden">
    <!-- Desktop/Tablet: Sidebar -->
    <AppSidebar v-if="!isMobile" />

    <!-- Main content area -->
    <main class="flex-1 flex flex-col overflow-hidden">
      <div class="flex-1 overflow-y-auto" :class="isMobile ? 'pb-16' : ''">
        <RouterView />
      </div>
    </main>

    <!-- Mobile: Bottom navigation -->
    <BottomNav v-if="isMobile" />
  </div>
</template>
