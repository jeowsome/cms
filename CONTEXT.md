## Current Task
Donations SPA: department expenses vs collections, multi-recorder invites with per-record access + removal UI; financial statement admin-only with projected (unclaimed) view; /app desk gated.

## Key Decisions
- Donation visibility is per record: assigned_to OR Donation Assignee rows; remove_recorder promotes next assignee
- /app restricted via before_request hook to admins + users on Pasig General records (desk_guard.py)
- After Donation doctype edits, always re-export fixtures — stale fixtures/doctype.json reverts DocFields on migrate

## Next Steps
- Deploys still need: npm run build + sudo bench restart (or supervisorctl restart frappe-bench-web:)
- 6 claimed items in "Unassigned Source" still need real source accounts
- hooks.py Account fixture filter still lists NTC names (exports empty account.json) — update to JBC
