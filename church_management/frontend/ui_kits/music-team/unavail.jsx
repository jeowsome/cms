// Unavailability & Declines — log of suspensions/leaves AND a record of declined assignments.
// Two stacked panels: Unavailability windows (top) + Declines history (bottom).

function Unavail() {
  const [tab, setTab] = React.useState("windows");
  return (
    <div className="bg-white w-full" style={{minHeight:"100%"}}>
      <Header title="Unavailability & Declines" subtitle="Members on leave, suspended, or who declined a specific assignment." right={
        <button className="px-3.5 py-1.5 text-xs font-semibold bg-rose-600 text-white rounded-lg hover:bg-rose-700 shadow-sm">+ Mark unavailable</button>
      } />

      <div className="border-b border-ink-100 px-6 flex items-center gap-1 bg-white sticky top-[73px] z-[5]">
        {[
          { id: "windows", label: "Unavailability windows", count: UNAVAIL_WINDOWS.length },
          { id: "declines", label: "Decline log",            count: DECLINES.length },
        ].map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`px-4 py-3 text-xs font-semibold border-b-2 transition-colors flex items-center gap-2
              ${tab === t.id ? "text-rose-700 border-rose-500" : "text-ink-500 border-transparent hover:text-ink-700"}`}>
            <span>{t.label}</span>
            <span className={`text-[10px] font-bold rounded-full px-1.5 py-0.5 ${tab===t.id?"bg-rose-50 text-rose-700":"bg-ink-100 text-ink-500"}`}>{t.count}</span>
          </button>
        ))}
      </div>

      {tab === "windows" ? <WindowsPanel /> : <DeclinesPanel />}
    </div>
  );
}

const KIND_STYLES = {
  vacation:  { bg:"bg-brand-50",   text:"text-brand-700",   ring:"ring-brand-200",   label:"Vacation" },
  medical:   { bg:"bg-amber-50",   text:"text-amber-700",   ring:"ring-amber-200",   label:"Medical" },
  suspended: { bg:"bg-rose-50",    text:"text-rose-700",    ring:"ring-rose-200",    label:"Suspended" },
  event:     { bg:"bg-violet-50",  text:"text-violet-700",  ring:"ring-violet-200",  label:"Personal event" },
};

function WindowsPanel() {
  // Timeline: April 15 – May 31
  const start = new Date("2026-04-15");
  const end = new Date("2026-05-31");
  const totalDays = Math.round((end - start) / 86400000) + 1;
  const dayPct = (iso) => Math.max(0, Math.min(100, ((new Date(iso) - start) / 86400000) / totalDays * 100));

  // Group windows by member for clean rows
  const byMember = {};
  UNAVAIL_WINDOWS.forEach(w => { (byMember[w.memberId] = byMember[w.memberId] || []).push(w); });

  return (
    <div className="p-6">
      <div className="bg-white border border-ink-100 rounded-xl overflow-hidden">
        {/* Date scale */}
        <div className="grid bg-ink-50/50 border-b border-ink-100 text-[10px] font-mono text-ink-400" style={{gridTemplateColumns: "200px 1fr"}}>
          <div className="px-4 py-2 border-r border-ink-100 text-[10px] font-black text-ink-400 uppercase tracking-widest">Member</div>
          <div className="relative h-8">
            {[...Array(7)].map((_, i) => {
              const d = new Date(start);
              d.setDate(d.getDate() + Math.round(i * totalDays / 6));
              return (
                <div key={i} className="absolute top-0 bottom-0 border-l border-ink-100 px-1.5 py-2" style={{left: `${i*100/6}%`}}>
                  {d.toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                </div>
              );
            })}
            <div className="absolute top-0 bottom-0 border-l-2 border-rose-500" style={{left: `${dayPct("2026-05-09")}%`}}>
              <div className="absolute -top-1 -left-2 w-3 h-3 bg-rose-500 rounded-full ring-2 ring-white" />
              <div className="absolute top-0.5 left-1.5 text-[9px] font-bold text-rose-600 whitespace-nowrap">Today</div>
            </div>
          </div>
        </div>

        {Object.entries(byMember).map(([mid, windows]) => (
          <div key={mid} className="grid hover:bg-ink-50/30 border-b border-ink-100 last:border-b-0" style={{gridTemplateColumns: "200px 1fr"}}>
            <div className="px-4 py-3 flex items-center gap-2.5 border-r border-ink-100">
              <Avatar id={mid} size={28} />
              <div className="min-w-0">
                <div className="text-xs font-semibold text-ink-900 truncate">{memberById[mid].name}</div>
                <div className="text-[10px] text-ink-400 truncate">{windows.length} window{windows.length>1?"s":""}</div>
              </div>
            </div>
            <div className="relative h-14">
              {windows.map(w => {
                const left = dayPct(w.from);
                const right = dayPct(w.to);
                const width = Math.max(2, right - left + (1/totalDays*100));
                const style = KIND_STYLES[w.kind];
                return (
                  <div key={w.id} className={`absolute top-2 bottom-2 ${style.bg} ${style.ring} ring-1 rounded-lg flex items-center px-2 overflow-hidden`}
                       style={{left: `${left}%`, width: `${width}%`}}>
                    <div className="min-w-0">
                      <div className={`text-[10px] font-bold ${style.text} truncate`}>{style.label}</div>
                      <div className="text-[9px] text-ink-500 truncate">{w.reason}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Add a couple legend chips */}
      <div className="mt-4 flex flex-wrap items-center gap-3 text-[11px]">
        {Object.entries(KIND_STYLES).map(([k,s]) => (
          <span key={k} className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full ${s.bg} ${s.ring} ring-1 ${s.text} font-medium`}>{s.label}</span>
        ))}
      </div>
    </div>
  );
}

function DeclinesPanel() {
  return (
    <div className="p-6">
      <table className="w-full bg-white border border-ink-100 rounded-xl overflow-hidden">
        <thead>
          <tr className="bg-ink-50/50 border-b border-ink-100 text-[10px] font-black text-ink-400 uppercase tracking-widest">
            <th className="px-4 py-3 text-left">Member</th>
            <th className="px-4 py-3 text-left">Service</th>
            <th className="px-4 py-3 text-left">Role</th>
            <th className="px-4 py-3 text-left">Reason</th>
            <th className="px-4 py-3 text-left">Declined</th>
            <th className="px-4 py-3 text-left">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-ink-100">
          {DECLINES.map(d => {
            const r = roleById[d.roleId];
            return (
              <tr key={d.id} className="hover:bg-ink-50/30">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <Avatar id={d.memberId} size={28} />
                    <span className="text-xs font-semibold text-ink-900">{memberById[d.memberId].name}</span>
                  </div>
                </td>
                <td className="px-4 py-3 text-xs text-ink-700">
                  <div className="font-semibold">{fmtDateLong(d.iso)}</div>
                  <div className="text-[10px] text-ink-400 uppercase tracking-wider">{d.service === "am" ? "Morning" : "Evening"}</div>
                </td>
                <td className="px-4 py-3"><span className="text-[10px] font-bold uppercase tracking-widest text-ink-700 bg-ink-100 px-2 py-1 rounded">{r.label}</span></td>
                <td className="px-4 py-3 text-xs text-ink-700 italic max-w-xs truncate">"{d.reason}"</td>
                <td className="px-4 py-3 text-[11px] text-ink-500 tabular">{fmtRelative(d.declinedAt)}</td>
                <td className="px-4 py-3">
                  {d.status === "open" ? (
                    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 text-[10px] font-semibold ring-1 ring-amber-200">
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-500 pulse-ring" />Needs reassignment
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 text-[10px] font-semibold ring-1 ring-emerald-200">
                      ✓ Filled
                    </span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

Object.assign(window, { Unavail });
