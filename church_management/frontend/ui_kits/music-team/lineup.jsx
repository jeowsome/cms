// Lineup — main worship leader assignment page
// 5 Sundays × (AM + PM) × 9 roles. Click slot to open picker; picker filters to members
// whose `can` includes the role and who aren't already on this service (devotion exempt)
// and aren't in an unavailability window. Conflicts highlighted.

function Lineup() {
  const [lineup, setLineup] = React.useState(DEFAULT_LINEUP);
  const [picker, setPicker] = React.useState(null); // { iso, service, roleId }
  const [focusSunday, setFocusSunday] = React.useState("2026-05-10");

  const setSlot = (iso, service, roleId, memberId) => {
    setLineup(prev => {
      const next = { ...prev, [iso]: { ...prev[iso], [service]: { ...prev[iso][service], [roleId]: memberId } } };
      return next;
    });
  };

  // For a given iso/service, who is already assigned (excluding devotion role overlap)?
  const usedInService = (iso, service, exceptRole) => {
    const map = lineup[iso]?.[service] || {};
    const used = new Set();
    for (const r of ROLES) {
      if (r.id === "devotion") continue;
      if (r.id === exceptRole) continue;
      if (map[r.id]) used.add(map[r.id]);
    }
    return used;
  };

  return (
    <div className="bg-white w-full" style={{minHeight: "100%"}}>
      <Header title="Music Team — Lineup" subtitle="May 2026 · 5 Sundays · Morning + Evening" right={
        <>
          <button className="px-3 py-1.5 text-xs font-medium text-ink-600 hover:bg-ink-50 rounded-lg">← April</button>
          <button className="px-3 py-1.5 text-xs font-medium text-ink-600 hover:bg-ink-50 rounded-lg">June →</button>
          <div className="w-px h-5 bg-ink-200" />
          <button className="px-3 py-1.5 text-xs font-medium text-ink-600 hover:bg-ink-50 rounded-lg">Save draft</button>
          <button className="px-3.5 py-1.5 text-xs font-semibold bg-rose-600 text-white rounded-lg hover:bg-rose-700 shadow-sm flex items-center gap-1.5">
            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5"/></svg>
            Publish &amp; notify
          </button>
        </>
      } />

      {/* Sunday selector */}
      <div className="border-b border-ink-100 px-6 py-3 flex items-center gap-2 bg-ink-50/40 overflow-x-auto">
        {SUNDAYS.map(s => {
          const active = focusSunday === s.iso;
          const declines = DECLINES.filter(d => d.iso === s.iso && d.status === "open").length;
          return (
            <button key={s.iso} onClick={() => setFocusSunday(s.iso)}
              className={`px-3.5 py-2 rounded-xl text-xs font-semibold transition-colors flex items-center gap-2 shrink-0
                ${active ? "bg-rose-600 text-white shadow-sm" : "bg-white border border-ink-200 text-ink-700 hover:border-rose-300"}`}>
              <span>{s.label}</span>
              <span className={`text-[10px] font-medium ${active ? "text-rose-100" : "text-ink-400"}`}>{s.theme}</span>
              {declines > 0 && (
                <span className={`text-[9px] font-bold rounded-full px-1.5 py-0.5 ${active ? "bg-white/20 text-white" : "bg-amber-100 text-amber-700"}`}>
                  {declines}!
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Side-by-side AM / PM */}
      <div className="grid grid-cols-2 gap-px bg-ink-100">
        {SERVICES.map(svc => (
          <ServicePanel key={svc.id} svc={svc} iso={focusSunday} lineup={lineup} setPicker={setPicker} setSlot={setSlot} />
        ))}
      </div>

      {/* Open declines for this Sunday */}
      <OpenDeclines iso={focusSunday} />

      {picker && (
        <PickerModal
          iso={picker.iso} service={picker.service} roleId={picker.roleId}
          excluded={usedInService(picker.iso, picker.service, picker.roleId)}
          current={lineup[picker.iso]?.[picker.service]?.[picker.roleId]}
          onPick={(mid) => { setSlot(picker.iso, picker.service, picker.roleId, mid); setPicker(null); }}
          onClear={() => { setSlot(picker.iso, picker.service, picker.roleId, ""); setPicker(null); }}
          onClose={() => setPicker(null)}
        />
      )}
    </div>
  );
}

function Header({ title, subtitle, right }) {
  return (
    <div className="border-b border-ink-100 px-6 py-4 flex items-center justify-between sticky top-0 bg-white/95 backdrop-blur-sm z-10">
      <div className="flex items-center gap-3 min-w-0">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-rose-500 to-rose-700 flex items-center justify-center text-white font-bold shrink-0">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5"><path strokeLinecap="round" strokeLinejoin="round" d="M9 9l10.5-3m0 6.553v3.75a2.25 2.25 0 01-1.632 2.163l-1.32.377a1.803 1.803 0 11-.99-3.467l2.31-.66a2.25 2.25 0 001.632-2.163zm0 0V2.25L9 5.25v10.303m0 0v3.75a2.25 2.25 0 01-1.632 2.163l-1.32.377a1.803 1.803 0 01-.99-3.467l2.31-.66A2.25 2.25 0 009 15.553z"/></svg>
        </div>
        <div className="min-w-0">
          <div className="text-[10px] font-black text-ink-400 uppercase tracking-widest">JBC CMS · Worship Leader</div>
          <h1 className="font-bold text-lg text-ink-900 truncate">{title}</h1>
          {subtitle && <p className="text-[11px] text-ink-500 truncate">{subtitle}</p>}
        </div>
      </div>
      <div className="flex items-center gap-2">{right}</div>
    </div>
  );
}

function ServicePanel({ svc, iso, lineup, setPicker, setSlot }) {
  const map = lineup[iso]?.[svc.id] || {};
  return (
    <div className="bg-white p-5">
      <div className="flex items-baseline justify-between mb-3">
        <div>
          <div className="text-[10px] font-black text-ink-400 uppercase tracking-widest">{svc.label} Service</div>
          <div className="font-display font-bold text-2xl text-ink-900">{svc.time}</div>
        </div>
        <div className="text-[10px] font-black text-rose-700 uppercase tracking-widest bg-rose-50 px-2 py-1 rounded-md">{svc.short}</div>
      </div>

      <div className="space-y-1.5">
        {ROLES.map(r => {
          const memberId = map[r.id];
          const member = memberId ? memberById[memberId] : null;
          const unavail = member && isUnavailable(memberId, iso);
          const hasOpenDecline = DECLINES.find(d => d.iso === iso && d.service === svc.id && d.roleId === r.id && d.memberId === memberId && d.status === "open");
          return (
            <div key={r.id}
              onClick={() => setPicker({ iso, service: svc.id, roleId: r.id })}
              className={`group flex items-center gap-3 p-2 rounded-lg cursor-pointer transition-all
                ${member
                  ? (hasOpenDecline ? "bg-amber-50 ring-1 ring-amber-300" :
                     unavail ? "bg-rose-50 ring-1 ring-rose-300" :
                     "bg-ink-50/70 hover:bg-ink-100")
                  : "border border-dashed border-ink-200 hover:border-rose-400 hover:bg-rose-50/40"}`}>
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0
                ${r.group === "lead" ? "bg-amber-50 text-amber-700" :
                  r.group === "vocals" ? "bg-rose-50 text-rose-700" :
                  r.group === "instr" ? "bg-brand-50 text-brand-700" :
                  "bg-violet-50 text-violet-700"}`}>
                <RoleIcon r={r} className="w-4 h-4" />
              </div>
              <div className="w-32 shrink-0">
                <div className="text-[11px] font-bold text-ink-900">{r.label}</div>
                <div className="text-[9px] font-mono text-ink-400 uppercase tracking-wider">{r.short}</div>
              </div>
              {member ? (
                <div className="flex items-center gap-2 flex-1 min-w-0">
                  <Avatar id={memberId} size={28} />
                  <div className="min-w-0">
                    <div className="text-xs font-semibold text-ink-900 truncate">{member.name}</div>
                    {hasOpenDecline ? (
                      <div className="text-[10px] font-medium text-amber-700 truncate">⚠ Declined: {hasOpenDecline.reason}</div>
                    ) : unavail ? (
                      <div className="text-[10px] font-medium text-rose-700 truncate">On leave: {unavail.reason}</div>
                    ) : (
                      <div className="text-[10px] text-ink-400">{r.id === memberById[memberId].preferred ? "Preferred role" : "Available"}</div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="flex-1 text-[11px] italic text-ink-400">Click to assign…</div>
              )}
              <button className="opacity-0 group-hover:opacity-100 px-2 py-1 text-[10px] font-bold text-rose-700 bg-rose-50 rounded transition-opacity">
                {member ? "Change" : "Assign"}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function OpenDeclines({ iso }) {
  const open = DECLINES.filter(d => d.iso === iso && d.status === "open");
  if (open.length === 0) return null;
  return (
    <div className="border-t border-amber-200 bg-amber-50/60 px-6 py-3">
      <div className="flex items-center gap-2 mb-2">
        <div className="w-2 h-2 rounded-full bg-amber-500 pulse-ring" />
        <div className="text-[10px] font-black text-amber-800 uppercase tracking-widest">{open.length} open decline{open.length>1?"s":""} · needs reassignment</div>
      </div>
      {open.map(d => {
        const r = roleById[d.roleId];
        return (
          <div key={d.id} className="flex items-center gap-3 p-2 bg-white rounded-lg border border-amber-200 mb-1.5 last:mb-0">
            <Avatar id={d.memberId} size={28} />
            <div className="flex-1 min-w-0">
              <div className="text-xs"><span className="font-bold text-ink-900">{memberById[d.memberId].name}</span> can't make <span className="font-bold">{r.label}</span> · {d.service.toUpperCase()}</div>
              <div className="text-[10px] text-ink-500">"{d.reason}" · declined {fmtRelative(d.declinedAt)}</div>
            </div>
            <button className="px-2.5 py-1 text-[10px] font-bold text-rose-700 bg-rose-100 hover:bg-rose-200 rounded">Reassign</button>
          </div>
        );
      })}
    </div>
  );
}

function PickerModal({ iso, service, roleId, excluded, current, onPick, onClear, onClose }) {
  const [q, setQ] = React.useState("");
  const role = roleById[roleId];
  const sunday = SUNDAYS.find(s => s.iso === iso);
  const svc = SERVICES.find(s => s.id === service);

  const list = MEMBERS
    .map(m => ({
      ...m,
      canRole: m.can.includes(roleId),
      isPreferred: m.preferred === roleId,
      excluded: roleId !== "devotion" && excluded.has(m.id),
      unavail: isUnavailable(m.id, iso),
    }))
    .filter(m => m.name.toLowerCase().includes(q.toLowerCase()))
    .sort((a,b) => (b.isPreferred - a.isPreferred) || (b.canRole - a.canRole) || (a.unavail ? 1 : 0) - (b.unavail ? 1 : 0));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 anim-fadein">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-white w-full max-w-lg rounded-2xl shadow-2xl overflow-hidden anim-pop">
        <div className="px-5 py-4 border-b border-ink-100 flex items-center justify-between">
          <div>
            <div className="text-[10px] font-black text-rose-700 uppercase tracking-widest">{sunday?.label} · {svc?.label}</div>
            <h2 className="font-bold text-lg text-ink-900 mt-0.5">Assign {role.label}</h2>
          </div>
          {current && <button onClick={onClear} className="text-xs font-bold text-rose-700 hover:underline">Clear slot</button>}
        </div>
        <div className="px-5 py-3 border-b border-ink-100">
          <input autoFocus value={q} onChange={e => setQ(e.target.value)} placeholder="Search members…"
            className="w-full px-3.5 py-2 text-sm bg-ink-50 border border-ink-200 rounded-xl focus:bg-white focus:border-rose-500 focus:ring-2 focus:ring-rose-100 outline-none" />
        </div>
        <div className="max-h-96 overflow-auto">
          {list.map(m => {
            const blocked = m.excluded || m.unavail || !m.canRole;
            return (
              <button key={m.id} disabled={m.excluded || m.unavail} onClick={() => onPick(m.id)}
                className={`w-full flex items-center gap-3 px-5 py-2.5 border-b border-ink-50 text-left transition-colors
                  ${m.id === current ? "bg-rose-50/50" : ""}
                  ${blocked ? "opacity-60" : "hover:bg-rose-50/40"}
                  ${m.excluded || m.unavail ? "cursor-not-allowed" : ""}`}>
                <Avatar id={m.id} size={32} />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-ink-900 truncate">{m.name}</span>
                    {m.isPreferred && <span className="text-[9px] font-bold text-amber-700 bg-amber-100 px-1.5 py-0.5 rounded">★ Preferred</span>}
                    {m.id === current && <span className="text-[9px] font-bold text-rose-700 bg-rose-100 px-1.5 py-0.5 rounded">Current</span>}
                  </div>
                  <div className="text-[11px] text-ink-500 mt-0.5 flex items-center gap-1.5 flex-wrap">
                    {!m.canRole && <span className="font-semibold text-ink-400">Not approved for {role.label}</span>}
                    {m.canRole && !m.excluded && !m.unavail && <span>Plays: {m.can.map(c=>roleById[c]?.short).filter(Boolean).join(" · ")}</span>}
                    {m.excluded && <span className="font-semibold text-ink-500">Already on this service</span>}
                    {m.unavail && <span className="font-semibold text-rose-700">On leave: {m.unavail.reason}</span>}
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { Lineup, Header });
