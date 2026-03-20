<script setup>
defineProps({
  columns: {
    type: Array,
    required: true,
    // { key, label, align?, class?, format?, hideOnMobile? }
  },
  rows: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  emptyText: { type: String, default: "No records found." },
  emptyIcon: { type: String, default: "folder" },
  rowClickable: { type: Boolean, default: false },
});

defineEmits(["row-click"]);
</script>

<template>
  <div>
    <!-- Desktop/Tablet: Table view (hidden on mobile) -->
    <div class="hidden sm:block bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-100">
          <thead class="bg-gray-50/80">
            <tr>
              <th
                v-for="col in columns"
                :key="col.key"
                class="px-5 py-3 text-[11px] font-semibold text-gray-500 uppercase tracking-wider"
                :class="[
                  col.align === 'right' ? 'text-right' : 'text-left',
                  col.hideOnMobile ? 'hidden lg:table-cell' : '',
                ]"
              >
                {{ col.label }}
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50">
            <template v-if="loading">
              <tr v-for="i in 5" :key="'sk-' + i">
                <td v-for="col in columns" :key="col.key" class="px-5 py-4">
                  <div class="h-4 bg-gray-100 rounded-lg animate-pulse" />
                </td>
              </tr>
            </template>
            <template v-else-if="rows.length">
              <tr
                v-for="(row, idx) in rows"
                :key="row.name || idx"
                class="hover:bg-gray-50/70 transition-colors"
                :class="rowClickable ? 'cursor-pointer active:bg-gray-100' : ''"
                @click="rowClickable && $emit('row-click', row)"
              >
                <td
                  v-for="col in columns"
                  :key="col.key"
                  class="px-5 py-3.5 whitespace-nowrap text-sm"
                  :class="[
                    col.align === 'right' ? 'text-right' : 'text-left',
                    col.class || 'text-gray-600',
                    col.hideOnMobile ? 'hidden lg:table-cell' : '',
                  ]"
                >
                  <slot :name="'cell-' + col.key" :row="row" :value="row[col.key]">
                    {{ col.format ? col.format(row[col.key], row) : row[col.key] }}
                  </slot>
                </td>
              </tr>
            </template>
            <tr v-else>
              <td :colspan="columns.length" class="px-5 py-16 text-center">
                <div class="flex flex-col items-center gap-2">
                  <svg class="w-10 h-10 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z" />
                  </svg>
                  <span class="text-sm text-gray-400">{{ emptyText }}</span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Mobile: Card view -->
    <div class="sm:hidden space-y-2.5">
      <!-- Loading cards -->
      <template v-if="loading">
        <div v-for="i in 4" :key="'msk-' + i" class="bg-white rounded-2xl border border-gray-100 p-4">
          <div class="space-y-3">
            <div class="h-4 w-2/3 bg-gray-100 rounded-lg animate-pulse" />
            <div class="h-3 w-1/2 bg-gray-100 rounded-lg animate-pulse" />
            <div class="h-5 w-1/3 bg-gray-100 rounded-lg animate-pulse" />
          </div>
        </div>
      </template>

      <!-- Data cards -->
      <template v-else-if="rows.length">
        <div
          v-for="(row, idx) in rows"
          :key="row.name || idx"
          class="bg-white rounded-2xl border border-gray-100 p-4 transition-all"
          :class="rowClickable ? 'active:bg-gray-50 active:scale-[0.99] cursor-pointer' : ''"
          @click="rowClickable && $emit('row-click', row)"
        >
          <slot name="mobile-card" :row="row">
            <!-- Default card layout: show all non-hidden columns -->
            <div class="space-y-2">
              <template v-for="col in columns" :key="col.key">
                <div class="flex items-center justify-between">
                  <span class="text-xs text-gray-400">{{ col.label }}</span>
                  <span class="text-sm text-gray-800 font-medium">
                    <slot :name="'cell-' + col.key" :row="row" :value="row[col.key]">
                      {{ col.format ? col.format(row[col.key], row) : row[col.key] }}
                    </slot>
                  </span>
                </div>
              </template>
            </div>
          </slot>
        </div>
      </template>

      <!-- Empty state -->
      <div v-else class="flex flex-col items-center gap-3 py-16">
        <svg class="w-12 h-12 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z" />
        </svg>
        <span class="text-sm text-gray-400">{{ emptyText }}</span>
      </div>
    </div>
  </div>
</template>
