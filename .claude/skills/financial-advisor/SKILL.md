---
name: financial-advisor
description: Generate a treasurer-style budget advisory for JBC Pasig from live collection and disbursement aggregates. Use when the user asks for financial advice, a budget review, which allotments to adjust, or invokes /financial-advisor (optional argument = fiscal year, defaults to the statement's current year).
---

# JBC Financial Advisor

Produce a written budget advisory for Jezreel Baptist Church Pasig, grounded in
live data. The audience is the church finance committee — write like a
trusted treasurer: concrete pesos, plain language, honest about uncertainty.

## Step 1 — Gather the data

Run (append `--kwargs "{'year': '<YYYY>'}"` if a year argument was given):

```bash
cd /home/frappe/frappe-bench && bench --site jbc-pasig.com execute church_management.financial_advisor_data.run
```

This prints one JSON document (aggregates only — no donor/member records):

- `trend` — per month: `collections`, `claimed` disbursements, `unclaimed` commitments
- `funds` — General / Mission / Benevolence / White Gift: collected, disbursed, unclaimed
- `purpose_totals` — per allotment: claimed, unclaimed, total (sorted desc)
- `monthly_commitments_by_purpose` — month → purpose → committed amount (for trend/growth analysis)
- `account_balances` — ledger vs available per cash/bank account
- `rule_based_insights` — the deterministic tips already shown on the statement page; do not merely repeat these — go deeper

Domain notes:
- "Unclaimed" = committed in a disbursement record but not yet paid out; it is
  already promised money, so treat collections − claimed − unclaimed as the real net.
- The White Gift fund is cumulative across years and excluded from operating net.
- Mission-purpose donations are held for Mission funds and are not departmental
  spending money.
- Allowances are recurring worker support — recommend changes there with extra
  care (they affect people's livelihoods); prefer phased or partial adjustments.

## Step 2 — Analyze

Work through, computing actual numbers (never hand-wave):

1. **Position**: YTD collections vs total commitments; how many months ran negative; the run-rate (avg monthly collections vs avg monthly commitments) and what year-end looks like if it continues.
2. **Allotment concentration**: which purposes dominate; ₱ impact of a 5–10% adjustment on each of the top 3 vs eliminating small ones entirely.
3. **Trends**: use `monthly_commitments_by_purpose` to find purposes growing or shrinking month over month; call out one-off spikes vs recurring growth.
4. **Unclaimed backlog**: where it sits, how old the pattern is, what claiming or releasing it does to the projected balance.
5. **Fund health**: any fund overdrawn or near depletion; whether account balances can actually cover the unclaimed commitments.

## Step 3 — Write the advisory

Structure (keep the whole thing readable in ~2 minutes):

1. **Bottom line** — 2–3 sentences: overall position and the single most important action.
2. **What the numbers say** — the analysis above, only the findings that matter, each with its peso figure.
3. **Recommendations** — 3–5, ordered by impact. Each names the allotment, the specific adjustment (₱/month or %), the annualized effect, and the trade-off. Distinguish "do now" from "watch next month".
4. **Watch list** — anything not yet actionable but trending wrong.

Do not fabricate numbers; every figure must come from the JSON or arithmetic on
it (show the arithmetic for derived figures). If data looks inconsistent, say
so rather than smoothing over it. End by reminding that the interactive charts
live at /financial_statement.
