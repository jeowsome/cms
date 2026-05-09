"""
One-shot cleanup: delete orphan week-5 child rows on Disbursements whose month
only has 4 Sundays.

Usage:
    # Dry run (default) — shows what WOULD be deleted, makes no changes:
    bench --site jbc-pasig.com execute church_management.church_management.cleanup_week5_rows.run

    # Actually delete:
    bench --site jbc-pasig.com execute church_management.church_management.cleanup_week5_rows.run --kwargs "{'apply': True}"

Safety:
    - Recomputes Sundays for each disbursement's month and ONLY touches months with exactly 4 Sundays.
    - Skips any week-5 row that has been claimed (status == "Claimed" OR has received_by/received_date).
    - Prints a per-doc plan first; rerun with apply=True to commit.
"""

import calendar
import datetime

import frappe


WEEK5_FIELDS = ("disbursement_item_week_5", "expense_item_week_5")
MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def _sundays_in(month_name, year):
    if month_name not in MONTHS or not year:
        return None
    month_idx = MONTHS.index(month_name) + 1
    year = int(year)
    days = calendar.monthrange(year, month_idx)[1]
    return sum(
        1 for d in range(1, days + 1)
        if datetime.date(year, month_idx, d).weekday() == 6
    )


def _is_claimed(row):
    status = (row.get("status") or "").strip()
    if status == "Claimed":
        return True
    if row.get("received_by") and row.get("received_date"):
        return True
    return False


def run(apply=False):
    """Scan all Disbursements; delete week-5 rows on 4-Sunday months."""
    apply = bool(apply)
    mode = "APPLY" if apply else "DRY-RUN"
    print(f"\n=== Week-5 cleanup [{mode}] ===\n")

    names = frappe.get_all("Disbursement", pluck="name")
    total_deleted = 0
    total_skipped_claimed = 0
    docs_changed = 0

    for name in names:
        doc = frappe.get_doc("Disbursement", name)
        sundays = _sundays_in(doc.month_recorded, doc.year_recorded)

        if sundays is None:
            print(f"[skip] {name}: cannot parse month/year ({doc.month_recorded!r}/{doc.year_recorded!r})")
            continue

        # Only act on months with EXACTLY 4 Sundays. 5-Sunday months legitimately use week_5.
        if sundays != 4:
            continue

        plan = []  # list of (table_field, row, reason)
        for field in WEEK5_FIELDS:
            rows = doc.get(field) or []
            for row in rows:
                if _is_claimed(row):
                    plan.append((field, row, "SKIP-claimed"))
                else:
                    plan.append((field, row, "DELETE"))

        if not plan:
            continue

        print(f"\n--- {name} ({doc.month_recorded}-{doc.year_recorded}, {sundays} Sundays) ---")
        for field, row, action in plan:
            label = row.get("worker") or row.get("description") or row.get("name")
            amount = row.get("amount") or 0
            print(f"  [{action}] {field}: {label!r:30s} amount={amount} status={row.get('status')!r} received_by={row.get('received_by')!r}")

        deletable = [(f, r) for f, r, a in plan if a == "DELETE"]
        skipped = sum(1 for _, _, a in plan if a == "SKIP-claimed")
        total_skipped_claimed += skipped

        if not deletable:
            continue

        if apply:
            for field in WEEK5_FIELDS:
                kept = [r for r in (doc.get(field) or []) if _is_claimed(r)]
                doc.set(field, kept)
            doc.save(ignore_permissions=True)
            docs_changed += 1
            total_deleted += len(deletable)

    print(f"\n=== Summary [{mode}] ===")
    print(f"  Disbursements touched: {docs_changed}")
    print(f"  Rows deleted:          {total_deleted}")
    print(f"  Claimed rows skipped:  {total_skipped_claimed}")
    if not apply:
        print("\n  Re-run with apply=True to commit the deletions:\n"
              "  bench --site jbc-pasig.com execute church_management.church_management.cleanup_week5_rows.run --kwargs \"{'apply': True}\"")
    else:
        frappe.db.commit()
        print("  Committed.")
