<script setup>
import { ref, computed } from "vue";
import { RouterLink, useRoute } from "vue-router";

const route = useRoute();
const collapsed = ref(false);

const navItems = [
  { label: "Disbursements", to: "/disbursements", icon: "wallet" },
  {
    label: "Music Team",
    icon: "music",
    basePath: "/music",
    children: [
      { label: "Lineup", to: "/music/lineup" },
      { label: "Roles", to: "/music/roles" },
      { label: "Unavailability", to: "/music/unavail" },
      { label: "My Schedule", to: "/music/me" },
      { label: "Notify", to: "/music/notify" },
    ],
  },
];

const expanded = ref({
  "Music Team": route.path.startsWith("/music"),
});

function isActive(path) {
  return route.path === path || route.path.startsWith(path + "/");
}
function isGroupActive(item) {
  return item.basePath && route.path.startsWith(item.basePath);
}
function toggle(label) {
  expanded.value[label] = !expanded.value[label];
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
    <nav class="flex-1 py-3 px-2 space-y-0.5 overflow-y-auto">
      <template v-for="item in navItems" :key="item.label">
        <!-- Leaf link -->
        <RouterLink
          v-if="!item.children"
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

        <!-- Group with children -->
        <div v-else>
          <button
            @click="collapsed ? null : toggle(item.label)"
            class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors"
            :class="
              isGroupActive(item)
                ? 'bg-brand-50 text-brand-700'
                : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
            "
          >
            <svg class="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path
                v-if="item.icon === 'music'"
                stroke-linecap="round" stroke-linejoin="round"
                d="M9 9l10.5-3m0 6.553v3.75a2.25 2.25 0 0 1-1.632 2.163l-1.32.377a1.803 1.803 0 1 1-.99-3.467l2.31-.66a2.25 2.25 0 0 0 1.632-2.163zm0 0V2.25L9 5.25v10.303m0 0v3.75a2.25 2.25 0 0 1-1.632 2.163l-1.32.377a1.803 1.803 0 0 1-.99-3.467l2.31-.66A2.25 2.25 0 0 0 9 15.553z"
              />
            </svg>
            <span v-if="!collapsed" class="truncate flex-1 text-left">{{ item.label }}</span>
            <svg
              v-if="!collapsed"
              class="w-3.5 h-3.5 shrink-0 transition-transform text-gray-400"
              :class="expanded[item.label] ? 'rotate-90' : ''"
              fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
            </svg>
          </button>

          <div
            v-if="!collapsed && expanded[item.label]"
            class="mt-0.5 ml-3 pl-3 border-l border-gray-200 space-y-0.5"
          >
            <RouterLink
              v-for="child in item.children"
              :key="child.to"
              :to="child.to"
              class="flex items-center gap-2 px-3 py-2 rounded-lg text-[13px] font-medium transition-colors"
              :class="
                isActive(child.to)
                  ? 'bg-brand-50 text-brand-700'
                  : 'text-gray-500 hover:bg-gray-50 hover:text-gray-900'
              "
            >
              <span class="w-1 h-1 rounded-full shrink-0"
                    :class="isActive(child.to) ? 'bg-brand-500' : 'bg-gray-300'" />
              <span class="truncate">{{ child.label }}</span>
            </RouterLink>
          </div>
        </div>
      </template>
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
