<script setup>
import { ref, computed } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import { useSessionStore } from "@/stores/session";

const route = useRoute();
const router = useRouter();
const session = useSessionStore();
const collapsed = ref(false);

const navItems = computed(() => {
  const items = [];

  // Finance area — Finance Team and Admin only.
  if (session.hasFinanceAccess) {
    items.push({ label: "Collections", to: "/collections", icon: "inbox" });
    items.push({ label: "Disbursements", to: "/disbursements", icon: "wallet" });
    items.push({ label: "Templates", to: "/templates", icon: "layers" });
    items.push({ label: "Members", to: "/members", icon: "users" });
  }

  // Role assignments — Music Team Leader and Admin only.
  if (session.isLeader) {
    items.push({ label: "Role Assignments", to: "/admin/roles", icon: "shield" });
  }

  // Music Team area — only for users with at least one music role (or admin).
  if (!session.hasMusicAccess) return items;

  // Slim member-only nav: profile + own schedule + swap requests.
  if (session.isMemberOnly) {
    items.push({
      label: "Music Team", icon: "music", basePath: "/music",
      children: [
        { label: "My Profile", to: "/music/profile" },
        { label: "My Schedule", to: "/music/me" },
      ],
    });
    return items;
  }

  // Leader / worship leader / admin: full music tooling. Each child link is
  // surfaced only to roles that can actually use it (mirrors router meta).
  const musicChildren = [];
  if (session.isLeader) musicChildren.push({ label: "Registrations", to: "/music/registrations" });
  if (session.isWorshipLeader) musicChildren.push({ label: "Worship Plan", to: "/music/worship" });
  if (session.isWorshipLeader) musicChildren.push({ label: "Lineup", to: "/music/lineup" });
  if (session.isLeader) musicChildren.push({ label: "Roles", to: "/music/roles" });
  if (session.isLeader) musicChildren.push({ label: "Unavailability", to: "/music/unavail" });
  musicChildren.push({ label: "My Schedule", to: "/music/me" });
  musicChildren.push({ label: "My Profile", to: "/music/profile" });
  if (session.isLeader) musicChildren.push({ label: "Notify", to: "/music/notify" });
  items.push({ label: "Music Team", icon: "music", basePath: "/music", children: musicChildren });

  return items;
});

async function logout() { await session.logout(); router.replace("/login"); }

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
              v-else-if="item.icon === 'users'"
              stroke-linecap="round" stroke-linejoin="round"
              d="M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 0 1 8.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0 1 11.964-3.07M12 6.375a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0Zm8.25 2.25a2.625 2.625 0 1 1-5.25 0 2.625 2.625 0 0 1 5.25 0Z"
            />
            <path
              v-else-if="item.icon === 'shield'"
              stroke-linecap="round" stroke-linejoin="round"
              d="M9 12.75 11.25 15 15 9.75M21 12c0 5.25-4.5 9-9 9s-9-3.75-9-9c0-1.286.27-2.508.756-3.61.5-1.13 1.95-1.39 3.034-.799C8.107 8.222 9.946 9 12 9c2.054 0 3.893-.778 5.21-2.41 1.084-.59 2.534-.33 3.034.8C20.73 9.49 21 10.713 21 12Z"
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

    <!-- Account footer -->
    <div v-if="!collapsed" class="px-3 py-2 border-t border-gray-100 text-[11px] text-gray-500 truncate">
      <div class="font-semibold text-gray-700 truncate">{{ session.user }}</div>
      <button @click="logout" class="mt-1 text-rose-700 hover:underline font-semibold">Sign out</button>
    </div>

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
