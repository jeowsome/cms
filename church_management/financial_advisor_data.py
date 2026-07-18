"""Aggregate financial data dump for the /financial-advisor skill.

Run via:
    bench --site jbc-pasig.com execute church_management.financial_advisor_data.run
    bench --site jbc-pasig.com execute church_management.financial_advisor_data.run --kwargs "{'year': '2026'}"

Prints a single JSON document with the same aggregates the financial
statement page uses — monthly trend, fund summary, allotment breakdown,
account balances — plus per-month-per-purpose detail for trend analysis.
Aggregates only; no donor or member-level records.
"""
import json
from collections import defaultdict

import frappe

TABLES = (
    [f"disbursement_item_week_{w}" for w in range(1, 6)]
    + [f"expense_item_week_{w}" for w in range(1, 6)]
    + ["monthly_disbursement_items", "monthly_expense_items"]
)


def run(year=None):
    from church_management.www import financial_statement as fsmod

    if year:
        frappe.form_dict["year"] = str(year)
    ctx = frappe._dict()
    fsmod.get_context(ctx)

    # Per-month per-purpose commitments (claimed + unclaimed) for trend analysis
    by_month_purpose = defaultdict(lambda: defaultdict(float))
    for d in frappe.get_all(
        "Disbursement",
        filters={"year_recorded": ctx["selected_year"], "docstatus": ["<", 2]},
        fields=["name", "month_recorded"],
    ):
        doc = frappe.get_doc("Disbursement", d.name)
        for table in TABLES:
            for item in doc.get(table) or []:
                purp = item.get("purpose") or "No Purpose"
                by_month_purpose[d.month_recorded][purp] += item.get("amount") or 0.0

    print(json.dumps({
        "year": ctx["selected_year"],
        "trend": ctx["trend"],
        "funds": ctx["financial_summary"]["funds"],
        "totals": {
            "cash_collected": ctx["financial_summary"]["cash_collected"],
            "cashless_collected": ctx["financial_summary"]["cashless_collected"],
            "total_disbursed": ctx["financial_summary"]["total_disbursed"],
            "total_unclaimed": ctx["financial_summary"]["total_unclaimed"],
        },
        "purpose_totals": ctx["purpose_totals"],
        "monthly_commitments_by_purpose": {
            m: dict(p) for m, p in by_month_purpose.items()
        },
        "account_balances": ctx["account_balances"],
        "rule_based_insights": ctx["insights"],
    }, indent=1, default=str))
