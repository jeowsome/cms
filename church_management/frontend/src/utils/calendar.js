/** Church calendar helpers shared by the calendar, the GPOA planner and the
 * public calendar page. Class names are written out in full so Tailwind
 * keeps them. */

export const SEPARATE = "Separate from worship service";
export const PART_OF_SERVICE = "Part of worship service";
export const REPLACES = "Replaces worship service";
export const RELATIONS = [
  { value: SEPARATE, label: "Separate (must not overlap a service)" },
  { value: PART_OF_SERVICE, label: "Part of the worship service" },
  { value: REPLACES, label: "Replaces the worship service (pastor approves)" },
];

export const STATUSES = ["Proposed", "Confirmed", "Done", "Cancelled"];
export const WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
export const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
export const FREQUENCIES = ["Weekly", "Twice a Month", "Monthly", "Every 2 Months", "Quarterly", "Thrice a Year", "Yearly"];

const PALETTE = {
  sky: { dot: "bg-sky-500", chip: "bg-sky-50 text-sky-900 ring-sky-200", bar: "border-l-sky-500" },
  amber: { dot: "bg-amber-500", chip: "bg-amber-50 text-amber-900 ring-amber-200", bar: "border-l-amber-500" },
  rose: { dot: "bg-rose-500", chip: "bg-rose-50 text-rose-900 ring-rose-200", bar: "border-l-rose-500" },
  violet: { dot: "bg-violet-500", chip: "bg-violet-50 text-violet-900 ring-violet-200", bar: "border-l-violet-500" },
  lime: { dot: "bg-lime-500", chip: "bg-lime-50 text-lime-900 ring-lime-200", bar: "border-l-lime-500" },
  pink: { dot: "bg-pink-500", chip: "bg-pink-50 text-pink-900 ring-pink-200", bar: "border-l-pink-500" },
  indigo: { dot: "bg-indigo-500", chip: "bg-indigo-50 text-indigo-900 ring-indigo-200", bar: "border-l-indigo-500" },
  fuchsia: { dot: "bg-fuchsia-500", chip: "bg-fuchsia-50 text-fuchsia-900 ring-fuchsia-200", bar: "border-l-fuchsia-500" },
  cyan: { dot: "bg-cyan-500", chip: "bg-cyan-50 text-cyan-900 ring-cyan-200", bar: "border-l-cyan-500" },
  orange: { dot: "bg-orange-500", chip: "bg-orange-50 text-orange-900 ring-orange-200", bar: "border-l-orange-500" },
  emerald: { dot: "bg-emerald-500", chip: "bg-emerald-50 text-emerald-900 ring-emerald-200", bar: "border-l-emerald-500" },
  teal: { dot: "bg-teal-500", chip: "bg-teal-50 text-teal-900 ring-teal-200", bar: "border-l-teal-500" },
  yellow: { dot: "bg-yellow-400", chip: "bg-yellow-50 text-yellow-900 ring-yellow-200", bar: "border-l-yellow-400" },
  stone: { dot: "bg-stone-500", chip: "bg-stone-100 text-stone-800 ring-stone-200", bar: "border-l-stone-500" },
};

const FIXED = {
  "Pasig General": "sky",
  "Pasig Sunday School": "amber",
  "Pasig Young People": "rose",
  "Pasig ColSPro": "violet",
  "Pasig Juniors": "lime",
  "Pasig Ladies": "pink",
  "Pasig Men": "indigo",
  "Pasig Music Team": "fuchsia",
  "Pasig SocMed": "cyan",
  "Pasig Couples": "orange",
  "Cainta General": "emerald",
  Mission: "yellow",
};
const ROTATION = ["teal", "stone", "emerald", "cyan", "orange", "violet", "lime", "amber"];

export function deptColor(dept) {
  let key = FIXED[dept];
  if (!key && dept?.startsWith("Cainta")) key = "teal";
  if (!key && dept?.includes("Discipleship")) key = "stone";
  if (!key) {
    let h = 0;
    for (const ch of dept || "") h = (h * 31 + ch.charCodeAt(0)) >>> 0;
    key = ROTATION[h % ROTATION.length];
  }
  return PALETTE[key];
}

const SHORT = {
  "Pasig General": "Church",
  "Pasig Sunday School": "SS",
  "Pasig Young People": "YP",
  "Pasig ColSPro": "ColSPro",
  "Pasig Juniors": "Juniors",
  "Pasig Ladies": "Ladies",
  "Pasig Men": "Men",
  "Pasig Music Team": "Music",
  "Pasig SocMed": "SocMed",
  "Pasig Couples": "Couples",
  "Cainta General": "Cainta",
};
export function deptShort(dept) {
  return SHORT[dept] || (dept || "").replace(/^Pasig /, "");
}

// ---------- dates (all local, ISO yyyy-mm-dd strings)

export function iso(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}
export function parseIso(s) {
  const [y, m, d] = String(s).slice(0, 10).split("-").map(Number);
  return new Date(y, m - 1, d);
}
export function addDays(s, n) {
  const d = parseIso(s);
  d.setDate(d.getDate() + n);
  return iso(d);
}
export function todayIso() {
  return iso(new Date());
}

/** 6×7 grid of ISO dates starting on the Sunday on/before the 1st. */
export function monthGrid(year, month) {
  const first = new Date(year, month, 1);
  const start = new Date(year, month, 1 - first.getDay());
  const cells = [];
  for (let i = 0; i < 42; i++) {
    const d = new Date(start);
    d.setDate(start.getDate() + i);
    cells.push({ date: iso(d), day: d.getDate(), inMonth: d.getMonth() === month, weekday: d.getDay() });
  }
  // Drop a trailing week that is entirely next month.
  return cells.slice(35).every((c) => !c.inMonth) ? cells.slice(0, 35) : cells;
}

export function fmtTime(t) {
  if (!t) return "";
  const [h, m] = t.split(":").map(Number);
  return `${h % 12 || 12}:${String(m).padStart(2, "0")}${h < 12 ? "am" : "pm"}`;
}
export function fmtDate(s, opts = { month: "short", day: "numeric" }) {
  return parseIso(s).toLocaleDateString("en-PH", opts);
}
export function fmtRange(a) {
  const same = !a.end_date || a.end_date === a.start_date;
  const d = same ? fmtDate(a.start_date, { weekday: "short", month: "short", day: "numeric" })
    : `${fmtDate(a.start_date, { weekday: "short", month: "short", day: "numeric" })} – ${fmtDate(a.end_date, { weekday: "short", month: "short", day: "numeric" })}`;
  const t = a.all_day || !a.start_time ? "" : ` · ${fmtTime(a.start_time)}–${fmtTime(a.end_time)}`;
  return d + t;
}

/** Map ISO date → activities touching that date. */
export function byDay(activities) {
  const out = {};
  for (const a of activities) {
    let d = a.start_date;
    const end = a.end_date || a.start_date;
    let guard = 0;
    while (d <= end && guard++ < 60) {
      (out[d] ||= []).push(a);
      d = addDays(d, 1);
    }
  }
  return out;
}

/** Worship services on a given ISO date (weekly schedule), marking replaced ones. */
export function servicesOn(date, services, replaced) {
  const wd = WEEKDAYS[parseIso(date).getDay()];
  return (services || [])
    .filter((s) => s.weekday === wd)
    .map((s) => ({ ...s, replacedBy: (replaced || []).find((r) => r.date === date && r.service === s.name)?.by || null }));
}

export function peso(v, digits = 0) {
  return new Intl.NumberFormat("en-PH", { style: "currency", currency: "PHP", minimumFractionDigits: digits, maximumFractionDigits: digits }).format(v || 0);
}

const ORD = { 1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th" };
/** "2nd & 4th Sunday", "Every Sunday", "1st Sunday · every 2 months from Mar". */
export function describeRule(r) {
  const weeks = String(r.weeks_of_month || "")
    .toLowerCase()
    .match(/last|\d/g) || [];
  const wd = r.weekday || "Sunday";
  let base;
  if (r.frequency === "Weekly" && !weeks.length) base = `Every ${wd}`;
  else {
    const w = weeks.length ? weeks : r.frequency === "Twice a Month" ? ["1", "3"] : ["1"];
    base = `${w.map((x) => (x === "last" ? "last" : ORD[x] || x)).join(" & ")} ${wd}`;
  }
  const months = String(r.months || "").match(/\d+/g);
  if (months?.length) return `${base} · ${months.map((m) => MONTHS[Number(m) - 1]?.slice(0, 3)).filter(Boolean).join(", ")}`;
  const start = MONTHS[(Number(r.start_month) || 1) - 1].slice(0, 3);
  switch (r.frequency) {
    case "Every 2 Months": return `${base} · every 2 months from ${start}`;
    case "Quarterly": return `${base} · quarterly from ${start}`;
    case "Thrice a Year": return `${base} · 3× a year from ${start}`;
    case "Yearly": return `${base} of ${MONTHS[(Number(r.start_month) || 1) - 1]}`;
    case "Weekly": return base;
    default: return `${base} · monthly`;
  }
}
