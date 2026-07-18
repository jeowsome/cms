## Current Task
Donations SPA: department expenses vs collections, multi-recorder invites with per-record access + removal UI; financial statement admin-only with projected (unclaimed) view; /app desk gated.

## Key Decisions
- Donation visibility is per record: assigned_to OR Donation Assignee rows; remove_recorder promotes next assignee
- /app restricted via before_request hook to admins + users on Pasig General records (desk_guard.py)
- After Donation doctype edits, always re-export fixtures — stale fixtures/doctype.json reverts DocFields on migrate

## Next Steps
- Deploys still need: npm run build + sudo bench restart (or supervisorctl restart frappe-bench-web:)
- hooks.py Account fixture filter still lists NTC names (exports empty account.json) — update to JBC

## Data fixes applied 2026-07-18 (DB-only, no code)
- Mission Support items sourced to Mission Cash - JBC (8 unclaimed Jun/Jul + 4 claimed Mar/Apr); DT - 2026 template + purpose default_account set
- 2 claimed April wk4 allowances re-sourced Cash - JBC → General Cash - JBC; "Unassigned Source" row now gone
