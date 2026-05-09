// Roles & Preferences — admin page to record what each member can play and what they prefer.
// Matrix view: members down, roles across. Filled dot = allowed, star = preferred.
// Click a cell to toggle allowed; click again on an allowed cell to set as preferred.

function RolesPrefs() {
  const [data, setData] = React.useState(() => MEMBERS.map(m => ({ ...m })));

  const toggle = (memberId, roleId) => {
    setData(prev => prev.map(m => {
      if (m.id !== memberId) return m;
      const allowed = m.can.includes(roleId);
      const isPref = m.preferred === roleId;
      if (!allowed) return { ...m, can: [...m.can, roleId] };
      if (allowed && !isPref) return { ...m, preferred: roleId }; // promote to preferred
      // already preferred → remove (clear allowed AND preferred)
      return { ...m, can: m.can.filter(r => r !== roleId), preferred: m.preferred === roleId ? "" : m.preferred };
    }));
  };

  return (
    <div className="bg-white w-full" style={{minHeight:"100%"}}>
      <Header title="Roles & Preferences" subtitle="What each music team member is approved to play, and what they prefer." right={
        <>
          <div className="flex items-center gap-3 text-[11px] text-ink-500 mr-2">
            <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-rose-100 ring-1 ring-rose-300 flex items-center justify-center"><span className="w-1.5 h-1.5 rounded-full bg-rose-500" /></span>Allowed</span>
            <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-amber-100 ring-1 ring-amber-400 flex items-center justify-center text-[8px]">★</span>Preferred</span>
          </div>
          <button className="px-3 py-1.5 text-xs font-medium text-ink-600 hover:bg-ink-50 rounded-lg">Export CSV</button>
          <button className="px-3.5 py-1.5 text-xs font-semibold bg-rose-600 text-white rounded-lg hover:bg-rose-700 shadow-sm">+ New member</button>
        </>
      } />

      <div className="p-6 overflow-auto">
        <div className="inline-block min-w-full">
          <div className="grid bg-ink-50/50 rounded-t-xl border border-ink-200 sticky top-0"
               style={{gridTemplateColumns: `220px repeat(${ROLES.length}, 1fr)`}}>
            <div className="px-4 py-3 text-[10px] font-black text-ink-400 uppercase tracking-widest border-r border-ink-200">Member · {data.length}</div>
            {ROLES.map(r => (
              <div key={r.id} className="px-2 py-3 text-center border-r border-ink-200 last:border-r-0">
                <div className={`w-7 h-7 rounded-lg mx-auto mb-1 flex items-center justify-center
                  ${r.group === "lead" ? "bg-amber-50 text-amber-700" :
                    r.group === "vocals" ? "bg-rose-50 text-rose-700" :
                    r.group === "instr" ? "bg-brand-50 text-brand-700" :
                    "bg-violet-50 text-violet-700"}`}>
                  <RoleIcon r={r} className="w-4 h-4" />
                </div>
                <div className="text-[9px] font-black text-ink-700 uppercase tracking-wider">{r.short}</div>
                <div className="text-[9px] text-ink-400 truncate">{r.label}</div>
              </div>
            ))}
          </div>

          <div className="border-x border-b border-ink-200 rounded-b-xl divide-y divide-ink-100">
            {data.map(m => (
              <div key={m.id} className="grid hover:bg-ink-50/30" style={{gridTemplateColumns: `220px repeat(${ROLES.length}, 1fr)`}}>
                <div className="px-4 py-3 flex items-center gap-2.5 border-r border-ink-100 min-w-0">
                  <Avatar id={m.id} size={32} />
                  <div className="min-w-0">
                    <div className="text-xs font-semibold text-ink-900 truncate">{m.name}</div>
                    <div className="text-[10px] text-ink-400">
                      {m.preferred ? <>★ {roleById[m.preferred]?.label}</> : "—"}
                    </div>
                  </div>
                </div>
                {ROLES.map(r => {
                  const allowed = m.can.includes(r.id);
                  const isPref = m.preferred === r.id;
                  return (
                    <button key={r.id} onClick={() => toggle(m.id, r.id)}
                      className={`flex items-center justify-center border-r border-ink-100 last:border-r-0 transition-colors
                        ${isPref ? "bg-amber-50 hover:bg-amber-100" :
                          allowed ? "bg-rose-50/50 hover:bg-rose-100/60" :
                          "bg-white hover:bg-ink-50"}`}>
                      {isPref ? (
                        <span className="text-amber-600 font-black text-lg">★</span>
                      ) : allowed ? (
                        <span className="w-3 h-3 rounded-full bg-rose-500" />
                      ) : (
                        <span className="w-2 h-2 rounded-full bg-ink-200" />
                      )}
                    </button>
                  );
                })}
              </div>
            ))}
          </div>

          <p className="text-[11px] italic text-ink-400 mt-3">
            * Click an empty cell to mark as <strong>allowed</strong>. Click an allowed cell to promote to <strong>preferred</strong>. Click a preferred cell to clear.
            Each member has exactly one preferred role; the picker uses this to suggest assignments.
          </p>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { RolesPrefs });
