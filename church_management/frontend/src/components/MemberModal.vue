<script setup>
import { reactive, ref, watch } from "vue";
import { call } from "@/composables/useFrappeApi";
import AppButton from "@/components/AppButton.vue";

/**
 * Create or edit a Church Member. In create mode the envelope number can be
 * prefilled (e.g. from an unknown envelope typed during collection entry).
 */
const props = defineProps({
  isOpen: { type: Boolean, default: false },
  member: { type: Object, default: null }, // null → create mode
  prefillEnvelope: { type: String, default: "" },
});
const emit = defineEmits(["close", "saved"]);

const blank = () => ({
  name: null,
  envelope_number: "",
  firstname: "",
  lastname: "",
  contact_number: "",
  email_address: "",
  birthday: "",
  address: "",
  member_since: "",
});

const form = reactive(blank());
const saving = ref(false);
const errorMsg = ref("");
const firstField = ref(null);

watch(
  () => props.isOpen,
  (open) => {
    if (!open) return;
    errorMsg.value = "";
    Object.assign(form, blank(), props.member || {});
    if (!props.member && props.prefillEnvelope) {
      form.envelope_number = props.prefillEnvelope;
    }
    requestAnimationFrame(() => firstField.value?.focus());
  }
);

async function save() {
  errorMsg.value = "";
  if (!form.envelope_number.trim()) {
    errorMsg.value = "Envelope number is required.";
    return;
  }
  if (!form.firstname.trim()) {
    errorMsg.value = "First name is required.";
    return;
  }
  saving.value = true;
  try {
    const saved = await call("church_management.api.member.save_member", { doc: { ...form } });
    emit("saved", saved);
    emit("close");
  } catch (e) {
    errorMsg.value = e.message || "Failed to save member.";
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <Teleport to="body">
    <div v-if="isOpen" class="fixed inset-0 z-[60] flex items-end sm:items-center justify-center p-4">
      <div class="absolute inset-0 bg-gray-900/40 backdrop-blur-sm" @click="!saving && emit('close')" />
      <div class="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg p-5 anim-pop max-h-[90dvh] overflow-y-auto">
        <div class="flex items-start justify-between gap-3">
          <div>
            <h3 class="text-base font-bold text-gray-900">
              {{ member ? "Edit member" : "New church member" }}
            </h3>
            <p class="text-xs text-gray-500 mt-0.5">
              {{ member ? member.firstname + " " + (member.lastname || "") : "Register a member so their envelope number resolves during entry" }}
            </p>
          </div>
          <button
            type="button"
            class="w-8 h-8 rounded-lg flex items-center justify-center text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors shrink-0"
            aria-label="Close"
            @click="!saving && emit('close')"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div v-if="errorMsg" class="mt-3 p-2.5 rounded-xl bg-red-50 text-red-700 text-xs font-semibold">
          {{ errorMsg }}
        </div>

        <form class="mt-4 space-y-3" @submit.prevent="save">
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1">
                Envelope no. <span class="text-red-500">*</span>
              </label>
              <input ref="firstField" v-model="form.envelope_number" type="text" inputmode="numeric" class="cm-field text-center tabular font-semibold" placeholder="e.g. 158" />
            </div>
            <div>
              <label class="block text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1">Member since</label>
              <input v-model="form.member_since" type="text" class="cm-field" placeholder="e.g. 2020" />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1">
                First name <span class="text-red-500">*</span>
              </label>
              <input v-model="form.firstname" type="text" class="cm-field" placeholder="First name" />
            </div>
            <div>
              <label class="block text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1">Last name</label>
              <input v-model="form.lastname" type="text" class="cm-field" placeholder="Last name" />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1">Contact number</label>
              <input v-model="form.contact_number" type="tel" class="cm-field tabular" placeholder="09xx xxx xxxx" />
            </div>
            <div>
              <label class="block text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1">Birthday</label>
              <input v-model="form.birthday" type="date" class="cm-field tabular" />
            </div>
          </div>

          <div>
            <label class="block text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1">Email</label>
            <input v-model="form.email_address" type="email" class="cm-field" placeholder="name@email.com" />
          </div>

          <div>
            <label class="block text-[11px] font-semibold text-gray-500 uppercase tracking-wider mb-1">Address</label>
            <input v-model="form.address" type="text" class="cm-field" placeholder="Street, barangay, city" />
          </div>

          <div class="flex justify-end gap-2 pt-2">
            <AppButton type="button" variant="secondary" size="sm" :disabled="saving" @click="emit('close')">Cancel</AppButton>
            <AppButton type="submit" size="sm" :loading="saving">
              {{ member ? "Save changes" : "Create member" }}
            </AppButton>
          </div>
        </form>
      </div>
    </div>
  </Teleport>
</template>
