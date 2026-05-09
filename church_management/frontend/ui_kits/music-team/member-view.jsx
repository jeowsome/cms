// Member view — phone-sized "my schedule" for a single member.
// Shows next assignment hero card, upcoming list, decline button, unavailability toggle.

function MemberView() {
  const me = memberById["u2"]; // Maria Dela Cruz — picked because she has multiple upcoming assignments
  const [declined, setDeclined] = React.useState({});

  const my = [];
  SUNDAYS.forEach(s => {
    SERVICES.forEach(svc => {
      const lineup = DEFAULT_LINEUP[s.iso]?.[svc.id] || {};
      Object.entries(lineup).forEach(([roleId, mid]) => {
        if (mid === me.id && !declined[`${s.iso}-${svc.id}-${roleId}`]) {
          my.push({ iso: s.iso, sunday: s, service: svc, roleId });
        }
      });
    });
  });

  const next = my[0];
  const rest = my.slice(1);

  return (
    <div className="bg-[#f0eee9] w-full" style={{minHeight:"100%"}}>
      {/* Phone frame */}
      <div className="max-w-[400px] mx-auto bg-white min-h-[800px] shadow-2xl relative" style={{borderRadius: 32, overflow:"hidden"}}>
        {/* Status bar */}
        <div className="px-6 pt-3 pb-1 flex items-center justify-between text-[11px] font-semibold text-ink-900">
          <span>9:41</span>
          <span className="flex items-center gap-1">
            <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20"><path d="M2 10a8 8 0 1116 0 8 8 0 01-16 0z"/></svg>
            <svg className="w-4 h-3" fill="currentColor" viewBox="0 0 24 18"><rect x="0" y="6" width="3" height="12"/><rect x="6" y="3" width="3" height="15"/><rect x="12" y="0" width="3" height="18"/></svg>
            <span>96</span>
          </span>
        </div>

        {/* Hero header */}
        <div className="px-6 pt-4 pb-6 bg-gradient-to-br from-rose-600 to-rose-800 text-white relative overflow-hidden" style={{borderBottomLeftRadius: 28, borderBottomRightRadius: 28}}>
          <div className="absolute -top-10 -right-10 w-40 h-40 rounded-full bg-white/10" />
          <div className="absolute top-20 -left-8 w-24 h-24 rounded-full bg-white/5" />
          <div className="relative">
            <div className="flex items-center justify-between mb-6">
              <div>
                <p className="text-[10px] font-black uppercase tracking-[0.2em] text-rose-200">Music Team</p>
                <p className="font-display text-2xl font-bold mt-0.5">My Schedule</p>
              </div>
              <Avatar id={me.id} size={44} ring="ring-2 ring-white/30" />
            </div>

            <div>
              <p className="text-[10px] font-black uppercase tracking-[0.2em] text-rose-200 mb-1">Next up · in 1 day</p>
              <p className="font-display text-3xl font-bold leading-tight">{fmtDateLong(next.iso)}</p>
              <p className="text-rose-100 text-sm mt-1">{next.sunday.theme} · {next.service.label} {next.service.time}</p>
              <div className="mt-4 inline-flex items-center gap-2 bg-white/20 backdrop-blur px-3 py-2 rounded-xl ring-1 ring-white/30">
                <RoleIcon r={roleById[next.roleId]} className="w-5 h-5" />
                <span className="font-bold text-sm uppercase tracking-wider">{roleById[next.roleId].label}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Quick actions */}
        <div className="px-6 -mt-3 relative z-10">
          <div className="bg-white rounded-2xl shadow-lg ring-1 ring-ink-100 p-3 grid grid-cols-3 gap-2">
            <QuickAction icon="🎵" label="Songs" sub="View list" />
            <QuickAction icon="📅" label="Practice" sub="Sat 5pm" />
            <QuickAction icon="🚫" label="Can't make it" sub="Decline" danger onClick={() => {
              setDeclined({...declined, [`${next.iso}-${next.service.id}-${next.roleId}`]: true });
            }} />
          </div>
        </div>

        {/* Upcoming list */}
        <div className="px-6 py-6">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-[10px] font-black uppercase tracking-widest text-ink-400">Upcoming · {rest.length}</h3>
            <button className="text-[11px] font-semibold text-rose-700">All schedule →</button>
          </div>
          <div className="space-y-2">
            {rest.map((a, i) => (
              <div key={i} className="flex items-center gap-3 bg-ink-50/50 rounded-xl p-3 border border-ink-100">
                <div className="text-center shrink-0 w-12">
                  <div className="text-[9px] font-black uppercase tracking-wider text-ink-400">{new Date(a.iso).toLocaleDateString("en-US",{month:"short"}).toUpperCase()}</div>
                  <div className="font-display text-2xl font-bold text-ink-900 leading-none">{new Date(a.iso).getDate()}</div>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs font-semibold text-ink-900">{a.service.label}</span>
                    <span className="text-[10px] text-ink-400 tabular">{a.service.time}</span>
                  </div>
                  <div className="text-[11px] text-ink-500 truncate">{a.sunday.theme}</div>
                </div>
                <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-rose-50 text-rose-700 ring-1 ring-rose-200">
                  <RoleIcon r={roleById[a.roleId]} className="w-3.5 h-3.5" />
                  <span className="text-[10px] font-bold uppercase tracking-wider">{roleById[a.roleId].short}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Unavailability section */}
        <div className="px-6 pb-8 mt-2">
          <h3 className="text-[10px] font-black uppercase tracking-widest text-ink-400 mb-3">Unavailable dates</h3>
          <div className="bg-amber-50/50 border border-amber-200 rounded-xl p-4">
            <p className="text-xs text-amber-900 font-medium">Set dates you can't serve and we'll skip you when assigning.</p>
            <button className="mt-3 inline-flex items-center gap-1.5 text-xs font-bold text-amber-700 bg-white px-3 py-1.5 rounded-lg ring-1 ring-amber-300 hover:bg-amber-50">
              + Add unavailable dates
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function QuickAction({ icon, label, sub, danger, onClick }) {
  return (
    <button onClick={onClick}
      className={`flex flex-col items-center gap-0.5 p-2.5 rounded-xl transition-colors
        ${danger ? "hover:bg-rose-50" : "hover:bg-ink-50"}`}>
      <span className="text-xl">{icon}</span>
      <span className={`text-[11px] font-bold ${danger ? "text-rose-700" : "text-ink-900"}`}>{label}</span>
      <span className="text-[9px] text-ink-400">{sub}</span>
    </button>
  );
}

Object.assign(window, { MemberView });
