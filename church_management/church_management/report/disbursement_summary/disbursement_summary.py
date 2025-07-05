# Copyright (c) 2025, [Your Name] and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from collections import defaultdict
from datetime import datetime

def execute(filters=None):
    if not filters: filters = {}
    if not filters.get("year"): filters["year"] = datetime.now().year

    columns = get_columns()
    data = get_data(filters)
    
    return columns, data

def get_columns():
    return [
        {
            "label": _("Disbursement Details"),
            "fieldname": "details",
            "fieldtype": "Link",
            "options": "Disbursement",
            "width": 400
        },
        {
            "label": _("Total Amount"),
            "fieldname": "total_amount",
            "fieldtype": "Currency",
            "width": 200
        }
    ]

def get_data(filters):
    year = filters.get("year")
    
    disbursements = frappe.db.sql(f"""
        SELECT name, month_recorded, total_amount_disbursed
        FROM `tabDisbursement`
        WHERE year_recorded = %(year)s
        ORDER BY creation DESC
    """, {"year": year}, as_dict=True)

    if not disbursements:
        frappe.msgprint(_("No Disbursements found for the year {0}").format(year))
        return []

    grouped_data = defaultdict(list)
    for d in disbursements:
        grouped_data[d.month_recorded].append(d)

    month_order = [
        "January", "February", "March", "April", "May", "June", "July",
        "August", "September", "October", "November", "December"
    ]

    report_rows = []
    grand_total = 0

    for month in month_order:
        if month in grouped_data:
            records = grouped_data[month]
            month_total = sum(record.total_amount_disbursed for record in records)
            grand_total += month_total

            # <-- MODIFIED: Removed the <strong> tags. Now sending plain text. -->
            report_rows.append({
                "details": month,
                "total_amount": month_total,
                "indent": 0
            })

            for record in records:
                report_rows.append({
                    "details": record.name,
                    "total_amount": record.total_amount_disbursed,
                    "indent": 1
                })

    if report_rows:
        report_rows.append({}) 
        # <-- MODIFIED: Removed the <strong> tags here too. -->
        report_rows.append({
            "details": _("Grand Total"),
            "total_amount": grand_total,
            "indent": 0
        })

    return report_rows