<script setup>
defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: "" },
});
</script>

<template>
  <div class="border-b border-ink-100 px-6 py-4 flex items-center justify-between sticky top-0 bg-white/95 backdrop-blur-sm z-10">
    <div class="flex items-center gap-3 min-w-0">
      <div class="w-9 h-9 rounded-xl bg-gradient-to-br from-rose-500 to-rose-700 flex items-center justify-center text-white font-bold shrink-0">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="w-5 h-5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 9l10.5-3m0 6.553v3.75a2.25 2.25 0 01-1.632 2.163l-1.32.377a1.803 1.803 0 11-.99-3.467l2.31-.66a2.25 2.25 0 001.632-2.163zm0 0V2.25L9 5.25v10.303"/>
        </svg>
      </div>
      <div class="min-w-0">
        <div class="text-[10px] font-black text-ink-400 uppercase tracking-widest">JBC CMS · Music Team</div>
        <h1 class="font-bold text-lg text-ink-900 truncate">{{ title }}</h1>
        <p v-if="subtitle" class="text-[11px] text-ink-500 truncate">{{ subtitle }}</p>
      </div>
    </div>
    <div class="flex items-center gap-2"><slot /></div>
  </div>
</template>
