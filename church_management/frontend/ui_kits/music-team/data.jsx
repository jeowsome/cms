// Music Team — shared data + helpers
// 9 roles per service. Everyone unique within a service except Devotion (overlaps allowed).

const ROLES = [
  { id: "leader",  label: "Worship Leader", short: "WL",  group: "lead",   icon: "M12 18v-5.25m0 0a6.01 6.01 0 001.5-.189m-1.5.189a6.01 6.01 0 01-1.5-.189m3.75 7.478a12.06 12.06 0 01-4.5 0m3.75 2.383a14.406 14.406 0 01-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 10-7.517 0c.85.493 1.509 1.333 1.509 2.316V18" },
  { id: "vocals1", label: "Backup Vocals 1", short: "V1", group: "vocals", icon: "M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" },
  { id: "vocals2", label: "Backup Vocals 2", short: "V2", group: "vocals", icon: "M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" },
  { id: "keys",    label: "Keyboard",       short: "Kb",  group: "instr",  icon: "M3 8.25v8.25a1.5 1.5 0 001.5 1.5h15a1.5 1.5 0 001.5-1.5V8.25m-18 0V6.75a1.5 1.5 0 011.5-1.5h15a1.5 1.5 0 011.5 1.5V8.25m-18 0h18M7.5 8.25V14m3-5.75V14m3-5.75V14m3-5.75V14" },
  { id: "guitar",  label: "Guitar",         short: "Gt",  group: "instr",  icon: "M14.121 7.629A3 3 0 009.017 9.43c-.023.212-.002.425.028.636l.506 3.541a4.5 4.5 0 01-.43 2.65L9 16.5l1.539-.5a4.5 4.5 0 012.65-.43l3.541.506c.21.03.424.051.636.028a3 3 0 001.802-5.104m-2.658-2.658L17 6l3 3m-1.379 1.379L21 12.5" },
  { id: "bass",    label: "Bass",           short: "Bs",  group: "instr",  icon: "M9 9.75V21m0-11.25a2.25 2.25 0 012.25-2.25h.5a2.25 2.25 0 012.25 2.25V21M9 9.75h5M3 21h18" },
  { id: "drums",   label: "Beatbox / Drums",short: "Dr",  group: "instr",  icon: "M3.75 9.75A.75.75 0 014.5 9h15a.75.75 0 010 1.5h-15a.75.75 0 01-.75-.75zM12 3v6m-3-3l3 3 3-3M5 14h14l-1.5 6h-11L5 14z" },
  { id: "laptop",  label: "Laptop / Slides",short: "Lt",  group: "tech",   icon: "M9 17.25v1.007a3 3 0 01-.879 2.122L7.5 21h9l-.621-.621A3 3 0 0115 18.257V17.25m6-12V15a2.25 2.25 0 01-2.25 2.25H5.25A2.25 2.25 0 013 15V5.25m18 0A2.25 2.25 0 0018.75 3H5.25A2.25 2.25 0 003 5.25m18 0V12a2.25 2.25 0 01-2.25 2.25H5.25A2.25 2.25 0 013 12V5.25" },
  { id: "devotion",label: "Devotion",       short: "Dv",  group: "lead",   icon: "M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" },
];

// 14 music team members with their allowed roles + preferred role
const MEMBERS = [
  { id: "u1",  name: "Jeomar Bayoguina",  preferred: "keys",    can: ["keys","leader","laptop","devotion"] },
  { id: "u2",  name: "Maria Dela Cruz",   preferred: "vocals1", can: ["vocals1","vocals2","leader","devotion"] },
  { id: "u3",  name: "Ramon Santos",      preferred: "drums",   can: ["drums","bass","devotion"] },
  { id: "u4",  name: "Ana Reyes",         preferred: "vocals1", can: ["vocals1","vocals2","leader","devotion"] },
  { id: "u5",  name: "Faith Mangahas",    preferred: "leader",  can: ["leader","vocals1","vocals2","devotion"] },
  { id: "u6",  name: "Daniel Lim",        preferred: "guitar",  can: ["guitar","bass","laptop","devotion"] },
  { id: "u7",  name: "Isaac Domingo",     preferred: "bass",    can: ["bass","guitar","laptop","devotion"] },
  { id: "u8",  name: "Samuel Bautista",   preferred: "leader",  can: ["leader","keys","vocals1","devotion"] },
  { id: "u9",  name: "Noel Hernandez",    preferred: "guitar",  can: ["guitar","leader","vocals1","devotion"] },
  { id: "u10", name: "Eliza Pascual",     preferred: "vocals1", can: ["vocals1","vocals2","keys","devotion"] },
  { id: "u11", name: "Joy Tamayo",        preferred: "laptop",  can: ["laptop","vocals2","devotion"] },
  { id: "u12", name: "Grace Villanueva",  preferred: "vocals2", can: ["vocals1","vocals2","devotion"] },
  { id: "u13", name: "Caleb Mariano",     preferred: "drums",   can: ["drums","bass","laptop","devotion"] },
  { id: "u14", name: "Hannah Rivera",     preferred: "keys",    can: ["keys","vocals1","devotion"] },
];

// Sundays in May 2026: 3, 10, 17, 24, 31
const SUNDAYS = [
  { iso: "2026-05-03", label: "May 3",  theme: "Communion" },
  { iso: "2026-05-10", label: "May 10", theme: "Mother's Day" },
  { iso: "2026-05-17", label: "May 17", theme: "Walking by Faith" },
  { iso: "2026-05-24", label: "May 24", theme: "Pentecost" },
  { iso: "2026-05-31", label: "May 31", theme: "Sent Out" },
];

const SERVICES = [
  { id: "am", label: "Morning",  time: "9:00 AM", short: "AM" },
  { id: "pm", label: "Evening",  time: "6:00 PM", short: "PM" },
];

// Assignments — { iso: { am: { roleId: memberId }, pm: { ... } } }
// Devotion can overlap; everything else unique per service.
const DEFAULT_LINEUP = {
  "2026-05-03": {
    am: { leader:"u5",  vocals1:"u2",  vocals2:"u12", keys:"u1",  guitar:"u9", bass:"u7",  drums:"u3",  laptop:"u11", devotion:"u8"  },
    pm: { leader:"u8",  vocals1:"u4",  vocals2:"u10", keys:"u14", guitar:"u6", bass:"u7",  drums:"u13", laptop:"u11", devotion:"u4"  },
  },
  "2026-05-10": {
    am: { leader:"u2",  vocals1:"u4",  vocals2:"u10", keys:"u14", guitar:"u6", bass:"u7",  drums:"u3",  laptop:"u11", devotion:"u14" },
    pm: { leader:"u8",  vocals1:"u5",  vocals2:"u12", keys:"u1",  guitar:"u9", bass:"u6",  drums:"u13", laptop:"u11", devotion:"u8"  },
  },
  "2026-05-17": {
    am: { leader:"u9",  vocals1:"u2",  vocals2:"u4",  keys:"u1",  guitar:"u6", bass:"u7",  drums:"u3",  laptop:"u11", devotion:"u9"  },
    pm: { leader:"u5",  vocals1:"u10", vocals2:"u12", keys:"u14", guitar:"u9", bass:"u7",  drums:"u13", laptop:"u11", devotion:"u3"  },
  },
  "2026-05-24": {
    am: { leader:"u8",  vocals1:"u4",  vocals2:"u10", keys:"u1",  guitar:"u6", bass:"u7",  drums:"u3",  laptop:"u11", devotion:"u8"  },
    pm: { leader:"u2",  vocals1:"u5",  vocals2:"u12", keys:"u14", guitar:"u9", bass:"u6",  drums:"u13", laptop:"u11", devotion:"u2"  },
  },
  "2026-05-31": {
    am: { leader:"u5",  vocals1:"u2",  vocals2:"u4",  keys:"u14", guitar:"u9", bass:"u7",  drums:"u3",  laptop:"u11", devotion:"u5"  },
    pm: { leader:"u9",  vocals1:"u10", vocals2:"u12", keys:"u1",  guitar:"u6", bass:"u7",  drums:"u13", laptop:"u11", devotion:"u1"  },
  },
};

// Date-range unavailability windows (suspensions, vacation, etc.)
const UNAVAIL_WINDOWS = [
  { id: "w1",  memberId: "u3",  from: "2026-05-15", to: "2026-05-31", reason: "Family vacation — Cebu",            kind: "vacation" },
  { id: "w2",  memberId: "u14", from: "2026-05-01", to: "2026-05-12", reason: "Wrist injury — recovering",         kind: "medical" },
  { id: "w3",  memberId: "u13", from: "2026-04-20", to: "2026-05-03", reason: "Suspended — discipleship counsel",  kind: "suspended" },
  { id: "w4",  memberId: "u6",  from: "2026-05-24", to: "2026-05-24", reason: "Out of town — sister's wedding",    kind: "event" },
];

// Per-assignment declines (member said unavailable AFTER being assigned)
const DECLINES = [
  { id: "d1", iso: "2026-05-10", service: "pm", roleId: "drums",  memberId: "u13", reason: "Final exam Monday morning",   declinedAt: "2026-05-04T09:14:00", status: "open"     },
  { id: "d2", iso: "2026-05-17", service: "am", roleId: "guitar", memberId: "u6",  reason: "Sick — flu",                  declinedAt: "2026-05-13T19:42:00", status: "filled"   },
  { id: "d3", iso: "2026-05-24", service: "am", roleId: "keys",   memberId: "u1",  reason: "Travel — work conference",    declinedAt: "2026-05-15T11:20:00", status: "filled"   },
];

// Notifications log
const NOTIFICATIONS = [
  { id: "n3", at: "2026-05-07T20:14:00", from: "u5",  type: "songs",    sundayIso: "2026-05-10", service: "am", title: "May 10 AM songs",          body: "1. Goodness of God\n2. Build My Life\n3. King of Kings\n4. The Blessing", recipients: 14 },
  { id: "n2", at: "2026-05-06T18:02:00", from: "u5",  type: "practice", sundayIso: "2026-05-10", service: "am", title: "Practice — Sat May 9",     body: "5:00 PM at the sanctuary. Bring in-ears. Worship leaders please be 15 min early.", recipients: 14 },
  { id: "n1", at: "2026-05-01T22:30:00", from: "u8",  type: "songs",    sundayIso: "2026-05-03", service: "pm", title: "May 3 PM songs",          body: "1. Yet Not I\n2. Christ Our Hope\n3. Jesus Paid It All\n4. Doxology", recipients: 14 },
];

// Helpers
const initials = (name) => name.split(" ").map(p => p[0]).slice(0,2).join("").toUpperCase();
const memberById = Object.fromEntries(MEMBERS.map(m => [m.id, m]));
const roleById = Object.fromEntries(ROLES.map(r => [r.id, r]));

function isUnavailable(memberId, iso) {
  return UNAVAIL_WINDOWS.find(w => w.memberId === memberId && w.from <= iso && iso <= w.to);
}

function fmtDateLong(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}
function fmtRelative(isoDateTime) {
  const now = new Date("2026-05-09T10:00:00");
  const then = new Date(isoDateTime);
  const diffH = (now - then) / 36e5;
  if (diffH < 1)  return Math.round(diffH * 60) + "m ago";
  if (diffH < 24) return Math.round(diffH) + "h ago";
  return Math.round(diffH / 24) + "d ago";
}

// Avatar
const Avatar = ({ id, size = 28, ring }) => {
  const m = memberById[id];
  if (!m) return null;
  const colors = ["from-rose-400 to-rose-600","from-brand-400 to-brand-600","from-violet-400 to-violet-600","from-amber-400 to-amber-600","from-emerald-400 to-emerald-600","from-indigo-400 to-indigo-600","from-fuchsia-400 to-fuchsia-600","from-sky-400 to-sky-600"];
  const c = colors[parseInt(id.replace(/\D/g,""), 10) % colors.length];
  return (
    <div className={`rounded-full bg-gradient-to-br ${c} text-white flex items-center justify-center font-bold shrink-0 ${ring || ""}`}
         style={{width: size, height: size, fontSize: Math.max(9, Math.round(size * 0.36))}}>
      {initials(m.name)}
    </div>
  );
};

const RoleIcon = ({ r, className = "w-5 h-5" }) => (
  <svg className={className} fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24" strokeLinecap="round" strokeLinejoin="round">
    <path d={r.icon} />
  </svg>
);

Object.assign(window, { ROLES, MEMBERS, SUNDAYS, SERVICES, DEFAULT_LINEUP, UNAVAIL_WINDOWS, DECLINES, NOTIFICATIONS, initials, memberById, roleById, isUnavailable, fmtDateLong, fmtRelative, Avatar, RoleIcon });
