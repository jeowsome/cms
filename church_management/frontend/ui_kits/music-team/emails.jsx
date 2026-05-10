// Email templates — receipt (after submit) + verification (after admin approves).
// Rendered inside an "email client" frame so reviewers can see the whole touchpoint.

function EmailTemplates() {
  const [tab, setTab] = React.useState("receipt");
  return (
    <div className="bg-[#f0eee9] w-full p-8" style={{minHeight:"100%"}}>
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center gap-2 mb-4">
          <h2 className="font-display text-2xl font-bold text-ink-900">Email touchpoints</h2>
          <span className="text-[11px] text-ink-400 italic">Two automated emails — receipt + confirmation</span>
        </div>
        <div className="flex gap-1 mb-3">
          {[
            { id: "receipt", label: "1 · Registration receipt", sub: "Sent immediately after submit" },
            { id: "verified", label: "2 · Verification confirmation", sub: "Sent after admin approval" },
          ].map(t => (
            <button key={t.id} onClick={() => setTab(t.id)}
              className={`flex-1 px-4 py-3 rounded-xl text-left transition-colors
                ${tab === t.id ? "bg-white shadow-sm ring-1 ring-rose-300" : "bg-ink-100/40 hover:bg-white/60"}`}>
              <div className={`text-xs font-bold ${tab === t.id ? "text-rose-700" : "text-ink-700"}`}>{t.label}</div>
              <div className="text-[10px] text-ink-400 mt-0.5">{t.sub}</div>
            </button>
          ))}
        </div>
        {tab === "receipt" ? <ReceiptEmail /> : <VerifiedEmail />}
      </div>
    </div>
  );
}

function EmailFrame({ from, to, subject, children }) {
  return (
    <div className="bg-white rounded-2xl shadow-xl ring-1 ring-ink-100 overflow-hidden">
      {/* Email client chrome */}
      <div className="bg-ink-50/70 border-b border-ink-200 px-5 py-3 flex items-center gap-3">
        <div className="flex gap-1.5"><div className="w-2.5 h-2.5 rounded-full bg-rose-400" /><div className="w-2.5 h-2.5 rounded-full bg-amber-400" /><div className="w-2.5 h-2.5 rounded-full bg-emerald-400" /></div>
        <div className="text-[11px] font-mono text-ink-500 ml-2">Inbox · 1 unread</div>
      </div>
      <div className="border-b border-ink-100 px-6 py-4 grid grid-cols-[80px_1fr] gap-y-1 text-xs">
        <div className="text-ink-400 font-medium">From</div><div className="text-ink-900 font-semibold">{from}</div>
        <div className="text-ink-400 font-medium">To</div><div className="text-ink-900">{to}</div>
        <div className="text-ink-400 font-medium">Subject</div><div className="text-ink-900 font-bold">{subject}</div>
      </div>
      <div>{children}</div>
    </div>
  );
}

function ReceiptEmail() {
  return (
    <EmailFrame
      from="Jezreel Baptist Church · Music Team <noreply@jbc-pasig.org>"
      to="Maria Dela Cruz <maria.delacruz@example.com>"
      subject="We received your music team registration"
    >
      {/* Header band */}
      <div className="bg-gradient-to-br from-rose-600 to-rose-800 text-white px-10 py-10 text-center">
        <div className="inline-flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.25em] text-rose-200 mb-3">
          <span className="w-6 h-px bg-rose-300" />Jezreel Baptist Church<span className="w-6 h-px bg-rose-300" />
        </div>
        <h1 className="font-display font-bold text-3xl leading-tight">Registration received.</h1>
        <p className="text-rose-100 text-sm mt-2">Thank you for stepping up to serve.</p>
      </div>

      <div className="px-10 py-8">
        <p className="text-ink-700 text-sm leading-relaxed">Hi Maria,</p>
        <p className="text-ink-700 text-sm leading-relaxed mt-3">
          We received your registration for the JBC Music Team. Your details are with the worship leader for review,
          and we'll match them against your existing church records before activating your account.
        </p>

        {/* Submitted details */}
        <div className="mt-6 bg-ink-50/60 rounded-xl border border-ink-100 overflow-hidden">
          <div className="px-5 py-3 border-b border-ink-100 text-[10px] font-black uppercase tracking-widest text-ink-500">
            What you submitted
          </div>
          <div className="px-5 py-4 grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
            <Detail k="Email"          v="maria.delacruz@example.com" />
            <Detail k="Phone"          v="+63 917 555 0123" mono />
            <Detail k="Birthday"       v="May 22, 1994" />
            <Detail k="Member since"   v="January 2018" />
            <div className="col-span-2 pt-2 border-t border-ink-100">
              <div className="text-[10px] font-black uppercase tracking-widest text-ink-400 mb-1.5">Skills</div>
              <div className="flex flex-wrap gap-1.5">
                {["Backup Singing","Worship Leader","Devotion"].map(s => (
                  <span key={s} className="text-[11px] font-semibold text-rose-700 bg-rose-100 px-2 py-0.5 rounded-full ring-1 ring-rose-200">{s}</span>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="mt-6">
          <div className="text-[10px] font-black uppercase tracking-widest text-ink-500 mb-2">What happens next</div>
          <ol className="space-y-2 text-sm text-ink-700">
            <li className="flex items-start gap-2.5"><span className="w-5 h-5 rounded-full bg-rose-100 text-rose-700 flex items-center justify-center text-[11px] font-black shrink-0 mt-0.5">1</span><span>The worship leader reviews and verifies your details.</span></li>
            <li className="flex items-start gap-2.5"><span className="w-5 h-5 rounded-full bg-rose-100 text-rose-700 flex items-center justify-center text-[11px] font-black shrink-0 mt-0.5">2</span><span>You'll receive a confirmation email when verified — typically within 3 days.</span></li>
            <li className="flex items-start gap-2.5"><span className="w-5 h-5 rounded-full bg-rose-100 text-rose-700 flex items-center justify-center text-[11px] font-black shrink-0 mt-0.5">3</span><span>Sign in with the email above to access your schedule.</span></li>
          </ol>
        </div>

        <p className="text-ink-700 text-sm leading-relaxed mt-6">
          If anything in the summary above is incorrect, just reply to this email and we'll fix it before activation.
        </p>
        <p className="text-ink-700 text-sm leading-relaxed mt-4">
          Grace and peace,<br /><span className="font-semibold">JBC Music Team</span>
        </p>
      </div>

      <div className="bg-ink-50/40 border-t border-ink-100 px-10 py-5 text-[10px] text-ink-400 text-center leading-relaxed">
        Jezreel Baptist Church · Pasig, Metro Manila<br />
        This is an automated message. Reply directly to reach the worship leader.
      </div>
    </EmailFrame>
  );
}

function VerifiedEmail() {
  return (
    <EmailFrame
      from="Jezreel Baptist Church · Music Team <noreply@jbc-pasig.org>"
      to="Maria Dela Cruz <maria.delacruz@example.com>"
      subject="🎵 You're in! Welcome to the JBC Music Team"
    >
      {/* Header — celebratory variant */}
      <div className="relative bg-gradient-to-br from-emerald-600 via-emerald-700 to-emerald-900 text-white px-10 py-12 text-center overflow-hidden">
        <div className="absolute -top-12 -right-12 w-40 h-40 rounded-full bg-white/10" />
        <div className="absolute -bottom-8 -left-8 w-28 h-28 rounded-full bg-white/5" />
        <div className="relative">
          <div className="w-14 h-14 mx-auto rounded-full bg-white text-emerald-700 flex items-center justify-center shadow-lg mb-4">
            <svg className="w-8 h-8" fill="none" stroke="currentColor" strokeWidth="3" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5"/></svg>
          </div>
          <div className="inline-flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.25em] text-emerald-200 mb-3">
            <span className="w-6 h-px bg-emerald-300" />Verified Member<span className="w-6 h-px bg-emerald-300" />
          </div>
          <h1 className="font-display font-bold text-3xl leading-tight">Welcome to the team, Maria.</h1>
          <p className="text-emerald-100 text-sm mt-2 italic">"Sing to the Lord a new song." — Psalm 96:1</p>
        </div>
      </div>

      <div className="px-10 py-8">
        <p className="text-ink-700 text-sm leading-relaxed">Hi Maria,</p>
        <p className="text-ink-700 text-sm leading-relaxed mt-3">
          Great news — your music team registration has been verified. You're officially part of the JBC Music Team
          and your account is now active. Use the email below to sign in.
        </p>

        {/* Account card */}
        <div className="mt-6 bg-gradient-to-br from-rose-50 to-rose-100/40 rounded-xl border border-rose-200 px-5 py-5">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-gradient-to-br from-rose-500 to-rose-700 text-white flex items-center justify-center font-bold text-base shrink-0">MD</div>
            <div className="min-w-0 flex-1">
              <div className="text-[10px] font-black uppercase tracking-widest text-rose-700">Sign in as</div>
              <div className="font-bold text-ink-900 mt-0.5 truncate">maria.delacruz@example.com</div>
              <div className="flex flex-wrap gap-1 mt-2">
                {["Backup Singing","Worship Leader","Devotion"].map(s => (
                  <span key={s} className="text-[10px] font-semibold text-rose-700 bg-white px-1.5 py-0.5 rounded ring-1 ring-rose-200">{s}</span>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* CTA */}
        <div className="mt-6 text-center">
          <a className="inline-flex items-center gap-2 px-6 py-3 bg-rose-600 text-white rounded-xl font-bold text-sm shadow-md hover:bg-rose-700">
            Open my schedule
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3"/></svg>
          </a>
          <div className="text-[10px] text-ink-400 mt-2 font-mono">cms.jbc-pasig.org/music-team</div>
        </div>

        <div className="mt-8">
          <div className="text-[10px] font-black uppercase tracking-widest text-ink-500 mb-3">What you can do now</div>
          <div className="grid grid-cols-3 gap-3">
            <Capability icon="📅" title="Your schedule" sub="See where you're playing this month" />
            <Capability icon="🚫" title="Mark unavailable" sub="Block dates you can't serve" />
            <Capability icon="🎵" title="Practice notices" sub="Get songs and practice times" />
          </div>
        </div>

        <p className="text-ink-700 text-sm leading-relaxed mt-7">
          We're glad to have you serving with us. Faith will reach out before your first Sunday with practice details.
        </p>
        <p className="text-ink-700 text-sm leading-relaxed mt-4">
          To God be the glory,<br /><span className="font-semibold">Faith Mangahas</span>
          <span className="text-ink-400 text-[11px] block">Worship Leader · JBC Pasig</span>
        </p>
      </div>

      <div className="bg-ink-50/40 border-t border-ink-100 px-10 py-5 text-[10px] text-ink-400 text-center leading-relaxed">
        Jezreel Baptist Church · Pasig, Metro Manila<br />
        Need help signing in? Reply directly or text +63 917 555 0100.
      </div>
    </EmailFrame>
  );
}

function Detail({ k, v, mono }) {
  return (
    <div>
      <div className="text-[10px] font-black uppercase tracking-widest text-ink-400 mb-0.5">{k}</div>
      <div className={`text-ink-900 font-semibold ${mono ? "font-mono tabular text-[13px]" : ""}`}>{v}</div>
    </div>
  );
}

function Capability({ icon, title, sub }) {
  return (
    <div className="bg-ink-50/60 rounded-xl border border-ink-100 p-3 text-center">
      <div className="text-2xl mb-1">{icon}</div>
      <div className="text-[11px] font-bold text-ink-900">{title}</div>
      <div className="text-[10px] text-ink-500 mt-0.5">{sub}</div>
    </div>
  );
}

Object.assign(window, { EmailTemplates });
