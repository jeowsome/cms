# Copyright (c) 2025, [Your Name] and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from collections import defaultdict
from datetime import datetime

# <-- NEW: Map month names to numbers for filtering -->
MONTH_MAP = {
    "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
    "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12
}

def execute(filters=None):
    if not filters:
        filters = {}
    
    # <-- MODIFIED: No longer need to set defaults here, handled in get_data -->
    if not filters.get("from_year") or not filters.get("to_year"):
        frappe.throw(_("Please select From Year and To Year filters."))
        
    if filters.get("from_year") > filters.get("to_year"):
        frappe.throw(_("From Year cannot be greater than To Year"))

    # <-- MODIFIED: Pass the whole filters dict -->
    columns = get_columns(filters.get("from_year"), filters.get("to_year"))
    data = get_data(filters)
    
    return columns, data

def get_columns(from_year, to_year):
    """Generates dynamic columns based on the selected year range."""
    columns = [
        {
            "label": _("Collection Breakdown"),
            "fieldname": "breakdown",
            "fieldtype": "Data",
            "width": 250,
        }
    ]

    for year in range(to_year, from_year - 1, -1):
        columns.append({
            "label": str(year),
            "fieldname": f"year_{year}",
            "fieldtype": "Currency",
            "width": 150,
        })
    return columns

def get_data(filters): # <-- MODIFIED: Function now takes the full filters dict
    """Fetches and processes data into a nested pivot structure."""
    
    # <-- MODIFIED: Extract filters and set defaults -->
    from_year = filters.get("from_year")
    to_year = filters.get("to_year")
    
    # Get the selected month number, default to 12 (December) if not found
    month_filter_name = filters.get("month", "December")
    month_filter_num = MONTH_MAP.get(month_filter_name, 12)

    collection_mapping = {
        "Tithes": "all_tithes_total", "Offering": "all_offering_total",
        "Mission": "all_mission_total", "Benevolence": "all_benevolence_total",
        "Loose": "all_loose_total", "Sunday School": "sunday_school_collection"
    }
    
    # <-- MODIFIED: The SQL query now includes a condition for the month -->
    raw_data = frappe.db.sql(f"""
        SELECT
            YEAR(date) as year,
            MONTH(date) as month_num,
            MONTHNAME(date) as month_name,
            {', '.join([f'SUM({field}) as {name.lower().replace(" ", "_")}' for name, field in collection_mapping.items()])}
        FROM `tabCollection`
        WHERE
            YEAR(date) BETWEEN %(from_year)s AND %(to_year)s
            AND MONTH(date) <= %(month_num)s -- <-- NEW: Filter up to the selected month
        GROUP BY YEAR(date), MONTH(date), MONTHNAME(date)
        ORDER BY YEAR(date), MONTH(date)
    """, {
        "from_year": from_year,
        "to_year": to_year,
        "month_num": month_filter_num # <-- NEW: Pass month number to query
    }, as_dict=True)

    pivot_data = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    for row in raw_data:
        year = row.year
        month_num = row.month_num
        for name in collection_mapping:
            field_key = name.lower().replace(" ", "_")
            pivot_data[name][month_num][year] += row.get(field_key, 0.0)

    report_rows = []
    years = list(range(to_year, from_year - 1, -1))
    grand_totals = {f"year_{y}": 0.0 for y in years}

    month_names = MONTH_MAP # We can reuse our map
    
    for name in collection_mapping.keys():
        parent_row = {"breakdown": name, "indent": 0}
        
        for year in years:
            # The total is now automatically "Year-To-Date" because the raw_data was pre-filtered
            total_for_year = sum(pivot_data[name][month][year] for month in range(1, month_filter_num + 1))
            parent_row[f"year_{year}"] = total_for_year
            grand_totals[f"year_{year}"] += total_for_year
        
        report_rows.append(parent_row)

        # <-- MODIFIED: Loop only up to the selected month number -->
        for month_num in range(1, month_filter_num + 1):
            # Get month name from number
            month_name = list(month_names.keys())[list(month_names.values()).index(month_num)]
            child_row = {"breakdown": month_name, "indent": 1}
            has_data = False
            for year in years:
                val = pivot_data[name][month_num].get(year, 0.0)
                child_row[f"year_{year}"] = val
                if val > 0:
                    has_data = True
            
            if has_data:
                report_rows.append(child_row)

    total_row = {"breakdown": "Grand Total"}
    total_row.update(grand_totals)
    report_rows.append(total_row)
    
    for row in report_rows:
        if row.get("indent") == 0 or row["breakdown"] == "Grand Total":
            row["breakdown"] = f"<strong>{row['breakdown']}</strong>"

    return report_rows