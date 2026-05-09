# JBC CMS Design System

Design system for **Jezreel Baptist Church — Pasig**, supporting the Church Management System (CMS) — a Frappe/Vue app that tracks collections (tithes, offerings, missions, benevolence, white gift) and disbursements (weekly allowances, expenses, mission support) for the local church's accounting.

> _"πάντα εἰς δόξαν θεοῦ" — "All for the glory of God"_ (inscribed on the church seal)

**Mission:** A local church committed to proclaiming God's Word to its community. All for His glory.

---

## Sources

| Source | Reference |
|---|---|
| Logo (church seal) | `uploads/jbc_logo.jpg` (user-provided) → `assets/jbc_logo.jpg` |
| Codebase | GitHub `jeowsome/cms@main` — imported to `church_management/` |
| Live site | `jbc-pasig.com` (production, not accessed) |
| Author | Jeomar Bayoguina |
| Framework | Frappe (Python/JS) + Vue 3 SPA frontend (Vite, Tailwind v3, Pinia Colada, Reka UI, @vueuse/core) |

### Key product surfaces found
1. **Vue 3 SPA** — the Disbursement UI (`/church_management` hash-routed), mobile-first with responsive sidebar/bottom-nav. This is the primary product surface and the design reference for all UI kit work.
2. **Public financial statement page** — a server-rendered Jinja+Alpine page at `/financial_statement` that shows yearly fund summaries, account balances, and monthly disbursement drill-downs.
3. **Frappe Desk doctypes** — Collection, Disbursement, White Gift, Church Member, Church Worker, etc. These use standard Frappe Desk chrome, NOT custom designs — so they're out of scope for this system.

---

## Products in this design system

- **`ui_kits/cms-app/`** — JSX recreation of the mobile-first Disbursement SPA (sidebar, bottom-nav, list page, form page with weekly tabs, modals, data table, status badges, currency display).
- **`ui_kits/financial-statement/`** — JSX recreation of the public Financial Statement page (hero, filters, virtual fund cards, account balances table, monthly breakdowns).

---

## CONTENT FUNDAMENTALS

The CMS is an **operational tool for church treasurers and workers**, not an evangelistic or inspirational surface. Copy is terse, functional, and bookkeeping-flavored.

### Tone & voice
- **Neutral-operational, not devotional.** Inside the CMS, there are no scripture callouts, no "welcome home" language, no emoji. The design is a financial ledger made friendly.
- **Third-person / impersonal.** UI strings address the data, not the user. "New Disbursement", "Claim Item", "Receive By", "No active workers found." The app never says "you" or "I".
- **Church-domain nouns, accounting-domain verbs.** Nouns are ministry-specific (*Tithes, Offering, Mission, Benevolence, White Gift, Worker, Purpose*). Verbs are accounting-flavored (*claim, disburse, reconcile, submit, cancel, post, credit, debit*).
- **No honorifics on names.** Worker and member names are written plain — "Jeomar Bayoguina", not "Bro. Jeomar", not "Pastor Jonathan". Roles (Pastor, Deacon, Worship Leader, Usher) are stored as *roles* on the person record and surfaced as meta chips next to the name, never baked into the name string.
- **Currency is Philippine peso (₱ / PHP)** everywhere. Numbers always formatted `en-PH` with 2 decimals.

### Casing
- **Sentence case** for body copy, buttons, descriptions.  ("New Disbursement", "No records found.", "Save Row")
- **Title Case** for proper nouns (doctype names, section headings): "Total Claimed", "Virtual Fund Summary", "Effective Account Balances (Cash & Bank)".
- **ALL CAPS** with wide tracking (`tracking-widest` = 0.1em) for overline/eyebrow labels only — form field labels, table column heads, stat-card captions. Always paired with small sizes (9–11px) and heavy weight (700–900).
- **Abbreviations:** "JBC" for the company, "JBC CMS" for the product, "GL" for General Ledger. Month-year compounds use hyphen: `January-2026`.

### Voice in practice (examples lifted from the repo)

| Surface | Copy |
|---|---|
| Page title | "Disbursements" / "New Disbursement" |
| Page subtitle | "Monthly expenditure records" / "Create monthly disbursement" |
| Empty state | "No disbursements yet" / "No items for this period." |
| Overline label | "TOTAL CLAIMED" · "PLANNED AMOUNT" · "UNCLAIMED" · "PERIOD" |
| Section header | "Week 1 — Allowances & Disbursements" |
| Button (primary) | "New Disbursement", "Claim Item", "Confirm Claim", "Save Row" |
| Button (ghost) | "Back", "Cancel" |
| Status chips | "Draft" / "Submitted" / "Cancelled" / "Claimed" / "Unclaimed" |
| Confirmation | "Are you sure you want to permanently delete this row?" |
| Validation | "Please provide a worker and amount." |
| Inline hint | "No active workers found. Check Church Worker records." |
| Footnote | "* Available Balance = Ledger Balance (includes Collections) minus all Claimed Disbursements that haven't been reconciled as bank transactions yet." |

### Rules
- **No emoji. No exclamation marks.** The only punctuation flourish is the middle dot `·` between inline facts.
- **Numbers carry the emotion.** A bold peso amount does more persuasive work than any adjective. Don't decorate — typeset.
- **Hyphen for required-field markers:** `Source Account *` with a red asterisk.
- **Ellipsis `…` in selects:** "Select worker…", "Select Purpose".
- **"—" (em dash)** as the empty cell placeholder, never "N/A" in the Vue app. (The public page uses "-" / "N/A" — legacy.)
- **Footnotes are italicized gray-400**, prefixed with `*`.

---

## VISUAL FOUNDATIONS

### Colors
- **Primary accent:** Sky-blue scale (`brand-50` → `brand-900`), from Tailwind's `sky` palette. `brand-600` (#0284c7) is the workhorse — primary buttons, key numbers, active tab text, sidebar logo, the active nav indicator dot. `brand-50` is the soft-accent background for pills and hover states.
- **Neutrals:** Tailwind `gray` (slate-leaning). `gray-900` for headings, `gray-700` for sidebar text, `gray-500` for captions, `gray-400` for subtle icons and overline labels. Borders are `gray-100` (hairline) or `gray-200` (default input).
- **Status palette:** `green` (Claimed, positive money, "Collections"), `red` (destructive, negative, "Disbursements"), `amber` (Unclaimed, warning), `blue` (Submitted, Planned). Soft-tint backgrounds (`bg-*-50`) pair with saturated text (`text-*-600/700`) and a tiny colored dot (`bg-*-400`).
- **Logo seal colors** (yellow ring, green continents, ocean blue) do NOT appear in the product chrome. They stay on the seal itself. The product is sky + neutrals.
- **Gradients:** None. The CMS is a flat, color-block product.

### Typography
- **No custom webfonts in the repo.** Tailwind's default `font-sans` (system UI stack) ships untouched. For documentation + cards here we substitute **Inter** (closest neutral geometric humanist match) and **JetBrains Mono** for the `font-mono` class used on source-account codes. _Flagged substitution — if the church wants a specific display face, please supply the TTF/WOFF._
- **Scale:** Tailwind defaults. The app leans heavily on the extreme ends: `text-[9px]` / `text-[10px]` for overlines, `text-xl` / `text-2xl` for page titles, and `text-[11px] uppercase tracking-widest` for eyebrows is the signature move.
- **Weights:** `font-medium` (500) for most UI; `font-semibold` (600) for body-strong; `font-bold` (700) for titles; **`font-black` (900)** for big money numbers and uppercase eyebrow labels — a distinctive motif.
- **Numerals:** Always tabular-nums for currency. Always 2 decimals. Currency sign is `₱ ` (peso + space) in server-rendered surfaces, `PHP` in `Intl.NumberFormat` output.

### Backgrounds
- **Page background:** solid `gray-50` (#f9fafb). No patterns, no images, no gradients, no photography.
- **Surfaces:** pure white (`#ffffff`) cards on top of `gray-50`.
- **Tinted panels:** colored surfaces use `/70` or `/50` opacity on the soft color (`bg-green-50/70`, `bg-gray-50/50`) so they read as tints, not solid blocks.
- **No full-bleed imagery** anywhere. The only image asset referenced is the logo, rendered at 32×32 in the sidebar as a blue rounded-square with the letter "J" — the actual seal is reserved for print/ceremonial use.

### Animation
- **Duration:** 120–300ms, mostly `duration-200` (200ms).
- **Easing:** Tailwind's default (`ease-in-out` ≈ `cubic-bezier(0.4, 0, 0.2, 1)`).
- **Transitions used:** `transition-colors` (most common), `transition-all`, `transition-transform`.
- **Press feedback:** buttons scale down on `:active` — `active:scale-[0.97]` (standard) or `active:scale-[0.98]` for cards, `active:scale-95` for mobile FAB.
- **Modals:** fade-in 200ms + mobile slide-up-from-bottom (`translateY(100%)` → `0`); desktop fade + `translateY(16px) scale(0.95)` → rest.
- **Bottom nav** slides off-screen (`translate-y-full`) with a `duration-300 ease-in-out` transition as the user scrolls up, and slides back in as the user scrolls down.
- **No bounce, no spring physics, no scroll-linked animation, no Lottie.**

### Hover states
- **Primary button:** `bg-brand-600` → `bg-brand-700` (darker).
- **Secondary / ghost:** `bg-gray-50` or `bg-gray-100` fill appears.
- **Table rows:** `hover:bg-gray-50` (or `hover:bg-gray-50/70`).
- **Icon-only buttons:** foreground darkens (`text-gray-400` → `text-gray-600`) AND a soft `hover:bg-gray-100` rounded-lg fill appears.
- **Group-reveal pattern:** row-level action buttons use `opacity-0 group-hover:opacity-100` so the action only surfaces on hover (desktop) — on mobile they're always visible (`sm:opacity-0 sm:group-hover:opacity-100`).

### Press / active states
- **Scale-down:** `active:scale-[0.97]` is the house default; cards use `active:scale-[0.98]`.
- **Color-deepen:** `active:bg-brand-700` on primary, `active:bg-gray-100` on cards.
- **No ripple, no pulse.**

### Focus states
- **2px ring with 2px offset:** `focus:ring-2 focus:ring-offset-2 focus:ring-brand-500` on buttons; `focus:ring-2 focus:ring-brand-500 focus:border-brand-500` on inputs (no offset on fields).
- `focus:outline-none` is always paired with a ring — never nothing.

### Borders & hairlines
- Default border is **1px `gray-200`**; the subtle hairline inside cards and as `divide-y` separators is **1px `gray-100`** or even `gray-50`.
- Cards often carry `border border-gray-100` + `shadow-sm` as a combined low-contrast frame (the border does more work than the shadow).
- Dashed borders (`border-dashed border-gray-200`) mark empty-state drop zones.

### Shadows — light by design
- `shadow-sm` (`0 1px 2px rgba(0,0,0,0.05)`) on cards and primary buttons. That's it for most UI.
- `shadow-lg` on mobile FAB pills, `shadow-xl` on modals, `shadow-2xl` on the primary FAB.
- No colored/tinted shadows, no inset shadows, no glow. Elevation is carried by borders + whitespace.

### Corner radii — a JBC CMS signature
- **Everything is rounded.** The scale: `rounded-lg` (8px) for small chips & inputs, `rounded-xl` (12px) for buttons, inputs, and small cards, `rounded-2xl` (16px) for primary cards, modals, and stat tiles, `rounded-full` for pills, status dots, and the FAB.
- Table headers use `rounded-tl-xl` / `rounded-tr-xl` to match the card's outer radius.

### Transparency & blur
- Used sparingly for soft depth: `bg-gray-50/50`, `bg-green-50/70`, `bg-white/60` (active tab), `bg-black/40` (modal scrim).
- **No `backdrop-blur`.** Blurs are avoided on purpose — mobile perf matters since the CMS is used in church offices on older devices.

### Layout rules
- **Mobile-first.** All pages max out at `max-w-5xl` (1024px) and center with `mx-auto`; page gutters are `px-4` (mobile) → `sm:px-6` (≥640px).
- **Two-chrome system:** `AppSidebar` (desktop, ≥768px, 224px wide, collapsible to 64px) **xor** `BottomNav` (mobile, fixed bottom, 64px tall, auto-hides on scroll-up).
- **Fixed elements:** only the bottom nav (mobile) and the floating action button. The top header is in-flow.
- **Safe area:** `env(safe-area-inset-bottom)` padding on bottom nav for notched phones.
- **Tabs:** a horizontal row of full-width equal-share buttons with a 2px bottom-border indicator on the active tab (`border-brand-500 text-brand-600`). Week labels compress `W1..W5` on mobile, `Week 1..` on desktop.

### Cards
A JBC card = `bg-white` + `rounded-2xl` (16px) + `border border-gray-100` + `shadow-sm`. No colored borders, no left-accent stripes. Stat tiles add a soft-tint background (`bg-green-50/70`) but keep the same radius + border system.

### Status pills
`inline-flex` + `rounded-full` + `px-2.5 py-0.5` + `text-xs font-medium` + a tiny 1.5×1.5 dot of the matching `-400` tint. Backgrounds are `-50` tints, text is `-700`. Dots add a second layer of semantic redundancy (color + shape).

---

## ICONOGRAPHY

- **Strategy:** **Inline Heroicons-style outline SVGs.** The codebase does not ship an icon font or sprite; every icon is a hand-written `<svg stroke="currentColor" fill="none" stroke-width="1.5" viewBox="0 0 24 24">` inside the Vue component that uses it. Paths match Heroicons v2 outline at a glance (24-grid, 1.5 stroke, rounded caps/joins).
- **Weight:** stroke 1.5 for most icons, 2 for small accents, 2.5 for check-marks inside tiny pills.
- **Sizes:** `w-4 h-4` (16px) inline with text; `w-5 h-5` (20px) for nav & buttons; `w-6 h-6` (24px) for bottom-nav; `w-7 h-7` (28px) for FAB; `w-10/12 h-10/12` (40/48px) for empty-state illustrations.
- **Color:** `text-gray-400` subtle · `text-gray-500/600` secondary · `text-brand-600` active · status colors on state icons (green check, red trash).
- **Substitution in this design system:** we link **Heroicons v2 outline via CDN** (`https://unpkg.com/heroicons@2.x/...`) for UI kit recreations — it is a 1:1 match for what the repo hand-rolls. No substitution flag needed; the codebase is effectively using Heroicons already.
- **Emoji:** never used in product chrome.
- **Unicode glyphs:** `·` (middle dot) as inline separator; `—` (em dash) as empty-cell placeholder; `*` (asterisk) as required-field marker; `₱` (peso sign) for currency in server-rendered pages.
- **Logo usage:** the full circular seal (`assets/jbc_logo.jpg`) is for **ceremonial/print** use only (bulletins, statements headers, printed reports). In the product UI, the logo reduces to a 32×32 `brand-600` rounded-lg tile with the letter **"J"** in white — see `AppSidebar.vue`.

---

## Index — what's in this project

```
/
├── README.md                      ← you are here
├── SKILL.md                       ← Agent-Skill wrapper (cross-compat w/ Claude Code)
├── colors_and_type.css            ← CSS variables: colors, type, radii, shadows, motion
├── assets/
│   └── jbc_logo.jpg               ← church seal (ceremonial use)
│
├── preview/                       ← small HTML cards that populate the Design System tab
│   ├── brand-logo.html
│   ├── color-brand.html
│   ├── color-neutrals.html
│   ├── color-semantic.html
│   ├── type-display.html
│   ├── type-body.html
│   ├── type-overlines.html
│   ├── type-money.html
│   ├── spacing-radii.html
│   ├── spacing-shadows.html
│   ├── spacing-scale.html
│   ├── comp-buttons.html
│   ├── comp-badges.html
│   ├── comp-cards.html
│   ├── comp-inputs.html
│   ├── comp-stat-tiles.html
│   ├── comp-tabs.html
│   ├── comp-table-row.html
│   ├── comp-fab.html
│   ├── comp-icons.html
│   └── comp-sidebar.html
│
├── ui_kits/
│   ├── cms-app/                   ← Vue→JSX recreation of the Disbursement SPA
│   │   ├── README.md
│   │   ├── index.html             ← click-thru prototype (list → detail → claim)
│   │   ├── AppShell.jsx
│   │   ├── AppSidebar.jsx
│   │   ├── BottomNav.jsx
│   │   ├── PageHeader.jsx
│   │   ├── AppButton.jsx
│   │   ├── StatusBadge.jsx
│   │   ├── CurrencyDisplay.jsx
│   │   ├── DataTable.jsx
│   │   ├── StatTile.jsx
│   │   ├── WeekTabs.jsx
│   │   ├── ItemRow.jsx
│   │   ├── ClaimModal.jsx
│   │   └── Icon.jsx
│   │
│   └── financial-statement/       ← public Jinja page recreation
│       ├── README.md
│       ├── index.html
│       ├── StatementHero.jsx
│       ├── FilterBar.jsx
│       ├── FundCard.jsx
│       ├── AccountBalancesTable.jsx
│       └── MonthlyBreakdown.jsx
│
└── church_management/             ← imported reference source from jeowsome/cms@main
    ├── frontend/                  ← Vue 3 SPA (primary reference)
    └── www/                       ← Jinja public pages
```

---

## How to use this design system

1. Read this README end-to-end.
2. For a new feature inside the CMS: open `ui_kits/cms-app/index.html` as your visual anchor, then pick the closest existing component and extend. Match the type scale and radius vocabulary or it will look foreign.
3. For a new public-facing page: open `ui_kits/financial-statement/index.html`.
4. Never invent new colors. Use `colors_and_type.css` variables or `brand-*` / `gray-*` / `green|red|amber|blue-*` Tailwind tints.
5. Never draw SVG icons from scratch — use Heroicons v2 outline at 1.5 stroke.

---

## Caveats & open questions

- **Fonts:** the repo does not pin a specific typeface; we substituted **Inter** and **JetBrains Mono** via Google Fonts. Flag this to the product owner if a specific face is desired.
- **Iconography:** paths in the repo are hand-rolled but match Heroicons v2 outline. If you're adding icons via CDN, prefer Heroicons for visual continuity.
- **Frappe Desk chrome** (standard doctype forms, list views, Workspace, reports) is not redesigned here — that's Frappe's default UI and out of scope.
- **White Gift, Collection, Member, Donation** UIs are Frappe Desk only in the current codebase — no custom Vue screens exist yet. The UI kit covers only what the code covers: Disbursement + Public Financial Statement.
- **No dark mode** in the codebase. Not included here.
- **No brand guidelines document** was supplied — tone/voice rules above are inferred from the UI strings. Please review and annotate.
