// Member registration — public-facing form.
// Capture: email, first/last name, birthday, contact number, member-since (optional), skills.
// On submit → confirmation screen with the receipt email preview shown alongside.

const SKILLS = [
  { id: "leader",   label: "Worship Leader",  desc: "Lead vocals + cue the band",       group: "lead",   icon: "M19.114 5.636a9 9 0 010 12.728M16.463 8.288a5.25 5.25 0 010 7.424M6.75 8.25l4.72-4.72a.75.75 0 011.28.53v15.88a.75.75 0 01-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.01 9.01 0 012.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75z" },
  { id: "vocals",   label: "Backup Singing",  desc: "Harmonies and supporting vocals",  group: "vocals", icon: "M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" },
  { id: "guitar",   label: "Guitar",          desc: "Acoustic or electric",             group: "instr",  icon: "M14.121 7.629A3 3 0 009.017 9.43c-.023.212-.002.425.028.636l.506 3.541a4.5 4.5 0 01-.43 2.65L9 16.5l1.539-.5a4.5 4.5 0 012.65-.43l3.541.506c.21.03.424.051.636.028a3 3 0 001.802-5.104m-2.658-2.658L17 6l3 3m-1.379 1.379L21 12.5" },
  { id: "bass",     label: "Bass",            desc: "Rhythm + low end",                 group: "instr",  icon: "M9 9.75V21m0-11.25a2.25 2.25 0 012.25-2.25h.5a2.25 2.25 0 012.25 2.25V21M9 9.75h5M3 21h18" },
  { id: "drums",    label: "Beatbox / Drums", desc: "Cajón, kit, or beatbox",           group: "instr",  icon: "M3.75 9.75A.75.75 0 014.5 9h15a.75.75 0 010 1.5h-15a.75.75 0 01-.75-.75zM12 3v6m-3-3l3 3 3-3M5 14h14l-1.5 6h-11L5 14z" },
  { id: "devotion", label: "Devotion",        desc: "Open in scripture & prayer",       group: "lead",   icon: "M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" },
];

function Register() {
  const [form, setForm] = React.useState({
    email: "", firstName: "", lastName: "", birthday: "", phone: "", memberSince: "", skills: [],
  });
  const [submitted, setSubmitted] = React.useState(false);
  const set = (k, v) => setForm(prev => ({ ...prev, [k]: v }));
  const toggleSkill = (id) => set("skills", form.skills.includes(id) ? form.skills.filter(s => s !== id) : [...form.skills, id]);

  const valid = form.email && form.firstName && form.lastName && form.birthday && form.phone && form.skills.length > 0;

  if (submitted) return <Confirmation form={form} onReset={() => { setSubmitted(false); setForm({ email:"",firstName:"",lastName:"",birthday:"",phone:"",memberSince:"",skills:[] }); }} />;

  return (
    <div className="bg-[#f0eee9] w-full" style={{minHeight:"100%"}}>
      {/* Hero */}
      <div className="relative bg-gradient-to-br from-rose-600 to-rose-800 text-white px-12 pt-14 pb-20 overflow-hidden">
        <div className="absolute -top-20 -right-20 w-64 h-64 rounded-full bg-white/10" />
        <div className="absolute top-32 -left-12 w-40 h-40 rounded-full bg-white/5" />
        <div className="relative max-w-2xl">
          <div className="inline-flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.25em] text-rose-200 mb-3">
            <span className="w-8 h-px bg-rose-300" />
            Jezreel Baptist Church · Music Team
          </div>
          <h1 className="font-display font-bold text-5xl leading-tight tracking-tight">Join the worship roster.</h1>
          <p className="text-rose-100 text-base mt-4 max-w-lg">
            Tell us your details and what you play. We'll match this to your existing records and send a confirmation once you're verified.
          </p>
        </div>
      </div>

      {/* Form card */}
      <div className="px-12 -mt-10 pb-10 relative z-10">
        <div className="bg-white rounded-2xl shadow-xl ring-1 ring-ink-100 max-w-3xl mx-auto overflow-hidden">
          <div className="px-8 py-6 border-b border-ink-100">
            <div className="text-[10px] font-black uppercase tracking-widest text-rose-700">Step 1 of 1</div>
            <h2 className="font-display font-bold text-2xl text-ink-900 mt-0.5">Registration details</h2>
          </div>

          <div className="px-8 py-6 space-y-6">
            {/* Email */}
            <Field label="Church email" required hint="This becomes your sign-in.">
              <input type="email" value={form.email} onChange={e => set("email", e.target.value)} placeholder="you@example.com"
                className="w-full px-4 py-2.5 bg-ink-50 border border-ink-200 rounded-xl text-sm focus:bg-white focus:border-rose-500 focus:ring-2 focus:ring-rose-100 outline-none" />
            </Field>

            {/* Name row */}
            <div className="grid grid-cols-2 gap-4">
              <Field label="First name" required>
                <input value={form.firstName} onChange={e => set("firstName", e.target.value)} placeholder="Maria"
                  className="w-full px-4 py-2.5 bg-ink-50 border border-ink-200 rounded-xl text-sm focus:bg-white focus:border-rose-500 focus:ring-2 focus:ring-rose-100 outline-none" />
              </Field>
              <Field label="Last name" required>
                <input value={form.lastName} onChange={e => set("lastName", e.target.value)} placeholder="Dela Cruz"
                  className="w-full px-4 py-2.5 bg-ink-50 border border-ink-200 rounded-xl text-sm focus:bg-white focus:border-rose-500 focus:ring-2 focus:ring-rose-100 outline-none" />
              </Field>
            </div>

            {/* Birthday + phone */}
            <div className="grid grid-cols-2 gap-4">
              <Field label="Birthday" required>
                <input type="date" value={form.birthday} onChange={e => set("birthday", e.target.value)}
                  className="w-full px-4 py-2.5 bg-ink-50 border border-ink-200 rounded-xl text-sm focus:bg-white focus:border-rose-500 focus:ring-2 focus:ring-rose-100 outline-none tabular" />
              </Field>
              <Field label="Contact number" required hint="Used for practice reminders.">
                <input type="tel" value={form.phone} onChange={e => set("phone", e.target.value)} placeholder="+63 917 555 0123"
                  className="w-full px-4 py-2.5 bg-ink-50 border border-ink-200 rounded-xl text-sm focus:bg-white focus:border-rose-500 focus:ring-2 focus:ring-rose-100 outline-none tabular" />
              </Field>
            </div>

            {/* Member since (optional) */}
            <Field label="Member since" optional hint="Approximate is fine — leave blank if unsure.">
              <input type="month" value={form.memberSince} onChange={e => set("memberSince", e.target.value)}
                className="w-full px-4 py-2.5 bg-ink-50 border border-ink-200 rounded-xl text-sm focus:bg-white focus:border-rose-500 focus:ring-2 focus:ring-rose-100 outline-none tabular" />
            </Field>

            {/* Skills */}
            <Field label="Skills" required hint={`Select all that apply · ${form.skills.length} selected`}>
              <div className="grid grid-cols-2 gap-2.5">
                {SKILLS.map(s => {
                  const checked = form.skills.includes(s.id);
                  return (
                    <button key={s.id} type="button" onClick={() => toggleSkill(s.id)}
                      className={`flex items-start gap-3 p-3 rounded-xl border-2 text-left transition-all
                        ${checked ? "border-rose-500 bg-rose-50/60 shadow-sm" : "border-ink-200 bg-white hover:border-rose-300 hover:bg-rose-50/30"}`}>
                      <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 transition-colors
                        ${checked ? "bg-rose-600 text-white" :
                          s.group === "lead" ? "bg-amber-50 text-amber-700" :
                          s.group === "vocals" ? "bg-rose-50 text-rose-700" :
                          "bg-brand-50 text-brand-700"}`}>
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24" strokeLinecap="round" strokeLinejoin="round"><path d={s.icon} /></svg>
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className={`text-sm font-bold ${checked ? "text-rose-900" : "text-ink-900"}`}>{s.label}</div>
                        <div className="text-[11px] text-ink-500 mt-0.5">{s.desc}</div>
                      </div>
                      <div className={`w-5 h-5 rounded-md border-2 flex items-center justify-center shrink-0 transition-all
                        ${checked ? "border-rose-600 bg-rose-600" : "border-ink-300 bg-white"}`}>
                        {checked && <svg className="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" strokeWidth="3" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7"/></svg>}
                      </div>
                    </button>
                  );
                })}
              </div>
            </Field>

            <div className="flex items-center justify-between pt-5 border-t border-ink-100">
              <p className="text-[11px] text-ink-500 italic max-w-sm">
                We'll review your registration and send a confirmation to your email within a few days.
              </p>
              <button onClick={() => valid && setSubmitted(true)} disabled={!valid}
                className={`px-6 py-3 rounded-xl text-sm font-bold shadow-sm flex items-center gap-2 transition-all
                  ${valid ? "bg-rose-600 text-white hover:bg-rose-700" : "bg-ink-200 text-ink-400 cursor-not-allowed"}`}>
                Submit registration
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3"/></svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Field({ label, required, optional, hint, children }) {
  return (
    <div>
      <div className="flex items-baseline justify-between mb-1.5">
        <label className="text-[10px] font-black uppercase tracking-widest text-ink-700">
          {label}
          {required && <span className="text-rose-600 ml-1">*</span>}
          {optional && <span className="text-ink-400 ml-1.5 font-medium normal-case tracking-normal">(optional)</span>}
        </label>
        {hint && <span className="text-[10px] text-ink-400">{hint}</span>}
      </div>
      {children}
    </div>
  );
}

function Confirmation({ form, onReset }) {
  return (
    <div className="bg-[#f0eee9] w-full p-12" style={{minHeight:"100%"}}>
      <div className="max-w-2xl mx-auto bg-white rounded-2xl shadow-xl ring-1 ring-ink-100 overflow-hidden">
        <div className="px-8 py-10 text-center bg-gradient-to-br from-emerald-50 to-emerald-100/50 border-b border-emerald-200">
          <div className="w-14 h-14 mx-auto rounded-full bg-emerald-600 flex items-center justify-center text-white shadow-lg">
            <svg className="w-7 h-7" fill="none" stroke="currentColor" strokeWidth="3" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5"/></svg>
          </div>
          <h1 className="font-display font-bold text-3xl text-ink-900 mt-4">Registration received.</h1>
          <p className="text-ink-600 text-sm mt-1.5">A receipt has been sent to <strong className="font-semibold">{form.email}</strong></p>
        </div>
        <div className="px-8 py-6">
          <div className="text-[10px] font-black uppercase tracking-widest text-ink-400 mb-2">What happens next</div>
          <ol className="space-y-2.5 text-sm text-ink-700">
            <li className="flex items-start gap-2.5"><span className="w-5 h-5 rounded-full bg-rose-100 text-rose-700 flex items-center justify-center text-[11px] font-black shrink-0 mt-0.5">1</span><span>The worship leader reviews your details and matches them to existing church records.</span></li>
            <li className="flex items-start gap-2.5"><span className="w-5 h-5 rounded-full bg-rose-100 text-rose-700 flex items-center justify-center text-[11px] font-black shrink-0 mt-0.5">2</span><span>You'll receive a confirmation email when your account is verified — usually within 3 days.</span></li>
            <li className="flex items-start gap-2.5"><span className="w-5 h-5 rounded-full bg-rose-100 text-rose-700 flex items-center justify-center text-[11px] font-black shrink-0 mt-0.5">3</span><span>Once verified, you'll be able to view your schedule, mark unavailability, and receive practice notices.</span></li>
          </ol>
          <button onClick={onReset} className="mt-6 text-[11px] font-semibold text-rose-700 hover:underline">← Submit another registration</button>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { Register, SKILLS });
