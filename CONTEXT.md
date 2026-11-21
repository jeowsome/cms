## Current Task
Finance upgrades (departments, voids, creditors, claim corrections, audit log, Fund Summary) live on jbc-pasig.com since 2026-11-21; server hardened.

## Key Decisions
- Creditor payables/reimbursements are off-GL like claims; reimburse only from a same-fund account
- Live: developer_mode 0, allow_error_traceback 0, all supervisor programs run as `frappe`, HRMS removed
- Repo is public: no names in commits; patch names in git-ignored `patches/*/people_*.json`; `data/` and `notes/` ignored

## Next Steps
- Make GitHub repo private (old commits still hold church_management/data member/tithe exports)
- Deploy = backup → migrate (once) → `npm run build` → `sudo supervisorctl restart frappe-bench-web: frappe-bench-workers:`
- Runbooks: notes/2026-11-21-finance-go-live-and-server-hardening.md (dev on live site, restore, backups)

## Server Notes
- Daily full backup 02:30 Manila → ~/backups/jbc-pasig.com (30 days); restore: ~/frappe-bench/restore_site_db.sh
- Live scheduler disabled (enable_scheduler 0), as before; run tests only on a temporary test site
- Older open checks (from 2026-11-13, not re-verified): Mission Cashless −₱10,200; May-2026 PhilHealth ₱1,100 Unclaimed
