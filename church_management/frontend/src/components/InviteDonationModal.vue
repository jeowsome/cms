<script setup>
import { reactive, ref, watch } from "vue";
import { useQuery } from "@pinia/colada";
import { call } from "@/composables/useFrappeApi";
import AppButton from "@/components/AppButton.vue";

/**
 * Donation-admin only: invite anyone by email to record donations for one
 * department. New emails get an account + temporary password; existing
 * accounts just gain the Donation Editor role. Either way they're assigned
 * the department's Donation record for the year.
 *
 * Pass `department`/`year` to lock the invite to a specific record (used on
 * the record page); leave them empty for the free-pick variant on /admin/roles.
 */
const props = defineProps({
  isOpen: { type: Boolean, default: false },
  department: { type: String, default: "" },
  year: { type: Number, default: 0 },
});
const emit = defineEmits(["close", "invited"]);

const form = reactive({
  email: "",
  first_name: "",
  last_name: "",
  department: "",
  year: Math.max(new Date().getFullYear(), 2026),
});
const sending = ref(false);
const errorMsg = ref("");
const result = ref(null); // server response after a successful invite
const firstField = ref(null);

// The department picker is only needed in the free-pick variant.
const { data: options } = useQuery({
  key: ["donation-new-options"],
  query: () => call("church_management.api.donation.get_new_donation_options"),
  enabled: () => props.isOpen && !props.department,
  staleTime: 5 * 60 * 1000,
});

watch(
  () => props.isOpen,
  (open) => {
    if (!open) return;
    errorMsg.value = "";
    result.value = null;
    form.email = "";
    form.first_name = "";
    form.last_name = "";
    form.department = props.department || "";
    form.year = props.year || Math.max(new Date().getFullYear(), 2026);
    requestAnimationFrame(() => firstField.value?.focus());
  }
);

async function send() {
  errorMsg.value = "";
  if (!form.email.trim()) {
    errorMsg.value = "Email is required.";
    return;
  }
  if (!form.department) {
    errorMsg.value = "Pick the department they'll record donations for.";
    return;
  }
  sending.value = true;
  try {
    result.value = await call("church_management.api.donation.invite_user", { ...form });
    emit("invited", result.value);
  } catch (e) {
    errorMsg.value = e.message || "Failed to send invitation.";
  } finally {
    sending.value = false;
  }
}
</script>

<template>
  <Teleport to="body">
    <div v-if="isOpen" class="fixed inset-0 z-[60] flex items-end sm:items-center justify-center p-4">
      <div class="absolute inset-0 bg-gray-900/40 backdrop-blur-sm" @click="!sending && emit('close')" />
      <div class="relative bg-white rounded-2xl shadow-2xl w-full max-w-md p-5 anim-pop max-h-[90dvh] overflow-y-auto">
        <div class="flex items-start justify-between gap-3">
          <div>
            <h3 class="text-base font-bold text-gray-900">Invite to Donations</h3>
            <p class="text-xs text-gray-500 mt-0.5">
              <template v-if="department">
                They'll get access to <strong class="text-gray-700">{{ department }} · {{ form.year }}</strong> only
              </template>
              <template v-else>
                They get access to the donations pages only, scoped to their department
              </template>
            </p>
          </div>
          <button
            type="button"
            class="w-8 h-8 rounded-lg flex items-center justify-center text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors shrink-0"
            aria-label="Close"
            @click="!sending && emit('close')"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- Success summary -->
        <div v-if="result" class="mt-4">
          <div class="p-3.5 rounded-xl bg-green-50 border border-green-200 text-sm text-green-800">
            <p class="font-bold">
              {{ result.new_user ? "Invitation sent" : "Access granted" }} — {{ result.user }}
            </p>
            <p class="mt-1 text-xs leading-relaxed">
              Assigned to <strong>{{ result.department }} · {{ result.year }}</strong>.
              <template v-if="result.new_user">A temporary password was emailed; they'll set their own on first sign-in.</template>
              <template v-else>They already had an account, so it kept its password — we emailed them that donation access was added.</template>
            </p>
          </div>
          <div v-if="result.previous_assignee" class="mt-2 p-3 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-800">
            This record was previously assigned to <strong>{{ result.previous_assignee }}</strong> — they can no longer see it
            unless they're assigned another department.
          </div>
          <div v-if="!result.email_sent" class="mt-2 p-3 rounded-xl bg-red-50 border border-red-200 text-xs text-red-700">
            The email could not be sent (check Email Account settings in Frappe Desk). The account and assignment were still
            created — you can share credentials manually or re-invite later.
          </div>
          <div class="mt-3 flex justify-end gap-2">
            <AppButton size="sm" variant="secondary" @click="result = null">Invite another</AppButton>
            <AppButton size="sm" @click="emit('close')">Done</AppButton>
          </div>
        </div>

        <!-- Invite form -->
        <template v-else>
          <div v-if="errorMsg" class="mt-3 p-2.5 rounded-xl bg-red-50 text-red-700 text-xs font-semibold">
            {{ errorMsg }}
          </div>

          <form class="mt-4 space-y-3" @submit.prevent="send">
            <div>
              <label class="block text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1">
                Email <span class="text-red-500">*</span>
              </label>
              <input ref="firstField" v-model="form.email" type="email" class="cm-field" placeholder="name@email.com" />
            </div>

            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1">First name</label>
                <input v-model="form.first_name" type="text" class="cm-field" placeholder="First name" />
              </div>
              <div>
                <label class="block text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1">Last name</label>
                <input v-model="form.last_name" type="text" class="cm-field" placeholder="Last name" />
              </div>
            </div>

            <div v-if="!department" class="grid grid-cols-2 gap-3">
              <div>
                <label class="block text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1">
                  Department <span class="text-red-500">*</span>
                </label>
                <select v-model="form.department" class="cm-field cm-select">
                  <option value="" disabled>Select…</option>
                  <option v-for="d in options?.departments || []" :key="d" :value="d">{{ d }}</option>
                </select>
              </div>
              <div>
                <label class="block text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1">Year</label>
                <input v-model.number="form.year" type="number" :min="options?.min_year || 2026" class="cm-field tabular" />
              </div>
            </div>

            <p class="text-[11px] text-gray-400 leading-relaxed">
              If this department already has an assignee for that year, the record moves to the new person.
            </p>

            <div class="flex justify-end gap-2 pt-1">
              <AppButton type="button" variant="secondary" size="sm" :disabled="sending" @click="emit('close')">Cancel</AppButton>
              <AppButton type="submit" size="sm" :loading="sending">Send invitation</AppButton>
            </div>
          </form>
        </template>
      </div>
    </div>
  </Teleport>
</template>
