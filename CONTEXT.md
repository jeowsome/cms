## Current Task
Financial statement: usable (General) funds, due-date outlook, ledger-based Funds/Account Balances; Collections live sync.

## Key Decisions
- Only General fund is "usable"; Mission/Benevolence shown as set aside, White Gift separate
- Pending split by due date (week N = Nth Sunday, monthly = month end); outlook uses avg General per Sunday
- Comfortable to spend = min(end-of-month, year-end outlook) − RESERVE_WEEKS (1) of avg General spending

## Next Steps
- Deploys need: npm run build + `sudo supervisorctl restart frappe-bench-web:` (own SSH, needs password)
- Mission Cashless overdrawn −₱10,200; May-2026 PhilHealth ₱1,100 has receiver but Unclaimed — confirm
- JV-00054 cancelled 2026-10-17 (orphan from deleted test collection)
