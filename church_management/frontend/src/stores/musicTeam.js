import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { call } from "@/composables/useFrappeApi";

const MONTHS = [
  "January","February","March","April","May","June",
  "July","August","September","October","November","December",
];

function pad(n) { return n < 10 ? "0" + n : "" + n; }

function sundaysInMonth(year, monthIndex0) {
  const out = [];
  const d = new Date(year, monthIndex0, 1);
  while (d.getMonth() === monthIndex0) {
    if (d.getDay() === 0) out.push(`${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`);
    d.setDate(d.getDate() + 1);
  }
  return out;
}

export const useMusicTeamStore = defineStore("musicTeam", () => {
  const today = new Date();
  const month = ref(MONTHS[today.getMonth()]);
  const year = ref(today.getFullYear());

  const roles = ref([]);
  const members = ref([]);
  const lineup = ref({});            // { iso: { am: { roleName: {member, member_name, row_name} } } }
  const sundays = ref([]);            // [{sunday_date, theme}]
  const wednesdays = ref([]);
  const openDeclines = ref([]);
  const unavailability = ref([]);
  const declines = ref([]);
  const notifications = ref([]);
  const scheduleStatus = ref(null);

  const monthIndex = computed(() => MONTHS.indexOf(month.value));
  const computedSundays = computed(() => {
    const themed = Object.fromEntries((sundays.value || []).map(s => [s.sunday_date, s]));
    return sundaysInMonth(year.value, monthIndex.value).map(iso => ({
      iso,
      sunday_date: iso,
      theme: themed[iso]?.theme || "",
      sermon_title: themed[iso]?.sermon_title || "",
    }));
  });

  const memberById = computed(() => Object.fromEntries(members.value.map(m => [m.name, m])));
  const roleByName = computed(() => Object.fromEntries(roles.value.map(r => [r.name, r])));

  async function loadCatalog() {
    const [r, m] = await Promise.all([
      call("church_management.api.music_team.get_roles"),
      call("church_management.api.music_team.get_members"),
    ]);
    roles.value = r || [];
    members.value = m || [];
  }

  async function loadLineup() {
    const data = await call("church_management.api.music_team.get_lineup", {
      month: month.value, year: year.value,
    });
    lineup.value = data.lineup || {};
    sundays.value = data.sundays || [];
    wednesdays.value = data.wednesdays || [];
    openDeclines.value = data.open_declines || [];
    scheduleStatus.value = data.schedule?.status || null;
  }

  async function setSlot(iso, service, roleName, memberId, memberName) {
    await call("church_management.api.music_team.set_assignment", {
      month: month.value, year: year.value,
      sunday_date: iso, service_time: service, music_role: roleName,
      member: memberId || "", member_name: memberName || "",
    });
    await loadLineup();
  }

  async function publishSchedule() {
    await call("church_management.api.music_team.publish_schedule", {
      month: month.value, year: year.value,
    });
    await loadLineup();
  }

  async function setMemberRoles(memberName, roleNames, preferred) {
    await call("church_management.api.music_team.set_member_roles", {
      member: memberName,
      roles: JSON.stringify(roleNames),
      preferred: preferred || "",
    });
    await loadCatalog();
  }

  async function loadUnavailability() {
    unavailability.value = await call(
      "church_management.api.music_team.list_unavailability"
    ) || [];
  }
  async function addUnavailability(p) {
    await call("church_management.api.music_team.create_unavailability", p);
    await loadUnavailability();
  }

  async function loadDeclines() {
    declines.value = await call(
      "church_management.api.music_team.list_declines"
    ) || [];
  }
  async function resolveDecline(name) {
    await call("church_management.api.music_team.resolve_decline", { name });
    await Promise.all([loadDeclines(), loadLineup()]);
  }

  async function loadNotifications() {
    notifications.value = await call(
      "church_management.api.music_team.list_notifications", { limit: 20 }
    ) || [];
  }
  async function sendNotification(payload) {
    await call("church_management.api.music_team.send_notification", {
      ...payload,
      recipients: JSON.stringify(payload.recipients || []),
      send_sms: payload.send_sms ? 1 : 0,
    });
    await loadNotifications();
  }

  function isUnavailable(memberId, iso) {
    return unavailability.value.find(
      w => w.member === memberId && w.from_date <= iso && iso <= w.to_date
    );
  }

  return {
    month, year, MONTHS,
    roles, members, lineup, sundays, wednesdays, openDeclines,
    unavailability, declines, notifications, scheduleStatus,
    computedSundays, memberById, roleByName,
    loadCatalog, loadLineup, setSlot, publishSchedule, setMemberRoles,
    loadUnavailability, addUnavailability,
    loadDeclines, resolveDecline,
    loadNotifications, sendNotification,
    isUnavailable,
  };
});
