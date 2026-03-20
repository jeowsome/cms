<script setup>
import { ref } from "vue";
import { RouterLink, useRoute } from "vue-router";

const route = useRoute();
const collapsed = ref(false);

const navItems = [
  { label: "Disbursements", to: "/disbursements", icon: "wallet" },
];

function isActive(path) {
  return route.path.startsWith(path);
}
</script>

<template>
  <aside
    class="bg-white border-r border-gray-200 flex flex-col transition-all duration-200 shrink-0"
    :class="collapsed ? 'w-16' : 'w-56'"
  >
    <!-- Logo -->
    <div class="h-14 flex items-center px-4 border-b border-gray-100 shrink-0">
      <div class="flex items-center gap-2.5 overflow-hidden">
        <div class="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center text-white font-bold text-sm shrink-0">
          J
        </div>
        <span v-if="!collapsed" class="font-semibold text-gray-800 truncate text-sm">JBC CMS</span>
      </div>
    </div>

    <!-- Nav -->
    <nav class="flex-1 py-3 px-2 space-y-0.5">
      <RouterLink
        v-for="item in navItems"
        :key="item.to"
        :to="item.to"
        class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors"
        :class="
          isActive(item.to)
            ? 'bg-brand-50 text-brand-700'
            : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
        "
      >
        <svg class="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path
            v-if="item.icon === 'wallet'"
            stroke-linecap="round" stroke-linejoin="round"
            d="M21 12a2.25 2.25 0 0 0-2.25-2.25H15a3 3 0 1 1-6 0H5.25A2.25 2.25 0 0 0 3 12m18 0v6a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 18v-6m18 0V9M3 12V9m18 0a2.25 2.25 0 0 0-2.25-2.25H5.25A2.25 2.25 0 0 0 3 9m18 0V6a2.25 2.25 0 0 0-2.25-2.25H5.25A2.25 2.25 0 0 0 3 6v3"
          />
        </svg>
        <span v-if="!collapsed" class="truncate">{{ item.label }}</span>
      </RouterLink>
    </nav>

    <!-- Collapse toggle -->
    <button
      @click="collapsed = !collapsed"
      class="h-10 flex items-center justify-center border-t border-gray-100 text-gray-400 hover:text-gray-600 transition-colors shrink-0"
    >
      <svg
        class="w-4 h-4 transition-transform"
        :class="collapsed ? 'rotate-180' : ''"
        fill="none" stroke="currentColor" viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
      </svg>
    </button>
  </aside>
</template>
