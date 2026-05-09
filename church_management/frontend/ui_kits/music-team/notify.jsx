// Notify — worship leader composes and broadcasts to the lineup.
// Two-pane: composer left, recipient list right. Below: notification log.

function Notify() {
  const [type, setType] = React.useState("songs");
  const [sunday, setSunday] = React.useState("2026-05-17");
  const [service, setService] = React.useState("am");
  const [title, setTitle] = React.useState("May 17 AM songs");
  const [body, setBody] = React.useState("1. Goodness of God\n2. Build My Life\n3. The Blessing\n4. King of Kings");

  const lineup = DEFAULT_LINEUP[sunday]?.[service] || {};
  const recipients = Object.values(lineup).filter((v, i, a) => a.indexOf(v) === i).map(id => memberById[id]);
  const sundayObj = SUNDAYS.find(s => s.iso === sunday);

  const TYPES = [
    { id: "songs",    label: "Song list",       icon: "🎵", color: "rose" },
    { id: "practice", label: "Practice notice", icon: "📅", color: "brand" },
    { id: "swap",     label: "Swap request",    icon: "🔄", color: "violet" },
    { id: "general",  label: "General memo",    icon: "📣", color: "amber" },
  ];

  return (
    <div className="bg-[#f0eee9] w-full" style={{minHeight:"100%"}}>
      <Header title="Send to team" subtitle="Compose songs, practice info, or swap requests. Goes to assigned members for the selected service." right={
        <div className="flex items-center gap-2">
          <Avatar id="u5" size={28} />
          <div>
            <div className="text-[11px] font-bold text-ink-900">Faith Mangahas</div>
            <div className="text-[9px] text-ink-400 uppercase tracking-widest">Worship leader · sending</div>
          </div>
        </div>
      } />

      <div className="grid grid-cols-12 gap-6 p-6">
        {/* Composer */}
        <div className="col-span-12 lg:col-span-7 bg-white rounded-xl border border-ink-100 overflow-hidden">
          <div className="px-5 py-4 border-b border-ink-100">
            <div className="text-[10px] font-black uppercase tracking-widest text-ink-400 mb-2">Notification type</div>
            <div className="flex gap-2 flex-wrap">
              {TYPES.map(t => (
                <button key={t.id} onClick={() => setType(t.id)}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold transition-colors
                    ${type === t.id ? `bg-${t.color}-50 text-${t.color}-700 ring-1 ring-${t.color}-300` : "bg-ink-50 text-ink-600 hover:bg-ink-100"}`}>
                  <span className="text-base">{t.icon}</span>{t.label}
                </button>
              ))}
            </div>
          </div>

          <div className="p-5 space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-[10px] font-black uppercase tracking-widest text-ink-400 block mb-1.5">Sunday</label>
                <select value={sunday} onChange={e => setSunday(e.target.value)}
                  className="w-full px-3 py-2 bg-ink-50 border border-ink-200 rounded-lg text-sm font-semibold focus:bg-white focus:border-rose-500 focus:ring-2 focus:ring-rose-100 outline-none">
                  {SUNDAYS.map(s => <option key={s.iso} value={s.iso}>{fmtDateLong(s.iso)} — {s.theme}</option>)}
                </select>
              </div>
              <div>
                <label className="text-[10px] font-black uppercase tracking-widest text-ink-400 block mb-1.5">Service</label>
                <div className="flex gap-1 bg-ink-50 border border-ink-200 rounded-lg p-1">
                  {SERVICES.map(s => (
                    <button key={s.id} onClick={() => setService(s.id)}
                      className={`flex-1 px-3 py-1 rounded text-xs font-bold transition-colors
                        ${service === s.id ? "bg-white text-ink-900 shadow-sm" : "text-ink-500 hover:text-ink-700"}`}>
                      {s.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div>
              <label className="text-[10px] font-black uppercase tracking-widest text-ink-400 block mb-1.5">Title</label>
              <input value={title} onChange={e => setTitle(e.target.value)}
                className="w-full px-3 py-2.5 bg-ink-50 border border-ink-200 rounded-lg text-sm font-semibold focus:bg-white focus:border-rose-500 focus:ring-2 focus:ring-rose-100 outline-none" />
            </div>

            <div>
              <label className="text-[10px] font-black uppercase tracking-widest text-ink-400 block mb-1.5">Message</label>
              <textarea value={body} onChange={e => setBody(e.target.value)} rows={6}
                className="w-full px-3 py-2.5 bg-ink-50 border border-ink-200 rounded-lg text-sm focus:bg-white focus:border-rose-500 focus:ring-2 focus:ring-rose-100 outline-none font-mono leading-relaxed" />
              <div className="text-[10px] text-ink-400 mt-1.5">Markdown supported · {body.length} chars</div>
            </div>

            <div className="flex items-center justify-between pt-3 border-t border-ink-100">
              <label className="flex items-center gap-2 text-xs text-ink-600">
                <input type="checkbox" defaultChecked className="rounded text-rose-600 focus:ring-rose-500" />
                Also send via SMS
              </label>
              <div className="flex gap-2">
                <button className="px-3 py-2 text-xs font-medium text-ink-600 hover:bg-ink-50 rounded-lg">Save draft</button>
                <button className="px-4 py-2 text-xs font-bold bg-rose-600 text-white rounded-lg hover:bg-rose-700 shadow-sm">
                  Send to {recipients.length} →
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Recipients */}
        <div className="col-span-12 lg:col-span-5 space-y-6">
          <div className="bg-white rounded-xl border border-ink-100 overflow-hidden">
            <div className="px-5 py-4 border-b border-ink-100 flex items-center justify-between">
              <div>
                <div className="text-[10px] font-black uppercase tracking-widest text-ink-400">Will receive</div>
                <div className="text-sm font-bold text-ink-900 mt-0.5">{recipients.length} members · {sundayObj?.label} {SERVICES.find(s=>s.id===service)?.label}</div>
              </div>
              <button className="text-[11px] font-semibold text-rose-700">Edit ↗</button>
            </div>
            <div className="divide-y divide-ink-100">
              {Object.entries(lineup).map(([roleId, mid]) => {
                const m = memberById[mid];
                const role = roleById[roleId];
                return (
                  <div key={roleId} className="px-5 py-2.5 flex items-center gap-3 hover:bg-ink-50/50">
                    <Avatar id={mid} size={28} />
                    <div className="flex-1 min-w-0">
                      <div className="text-xs font-semibold text-ink-900 truncate">{m.name}</div>
                      <div className="text-[10px] text-ink-400">{role.label}</div>
                    </div>
                    <span className="text-[9px] font-bold uppercase tracking-widest text-ink-500 bg-ink-100 px-1.5 py-0.5 rounded">{role.short}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Sent log */}
          <div className="bg-white rounded-xl border border-ink-100 overflow-hidden">
            <div className="px-5 py-4 border-b border-ink-100">
              <div className="text-[10px] font-black uppercase tracking-widest text-ink-400">Recently sent</div>
            </div>
            <div className="divide-y divide-ink-100">
              {NOTIFICATIONS.map(n => (
                <div key={n.id} className="px-5 py-3 flex items-start gap-3 hover:bg-ink-50/50">
                  <span className="text-lg shrink-0">{n.type==="songs"?"🎵":n.type==="practice"?"📅":"📣"}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-ink-900 truncate">{n.title}</span>
                      <span className="text-[9px] text-ink-400 tabular shrink-0">{fmtRelative(n.at)}</span>
                    </div>
                    <div className="text-[10px] text-ink-500 mt-0.5 line-clamp-2 whitespace-pre-line">{n.body.split("\n").slice(0,2).join(" · ")}</div>
                    <div className="flex items-center gap-2 mt-1">
                      <Avatar id={n.from} size={16} />
                      <span className="text-[9px] text-ink-400">{memberById[n.from].name} → {n.recipients}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { Notify });
