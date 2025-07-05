# Copyright (c) 2024, [Your Name] and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from datetime import datetime

def execute(filters=None):
    """
    Executes the report generation.

    Args:
        filters (dict): A dictionary of filters applied by the user.

    Returns:
        tuple: A tuple containing the list of columns and the data as a list of dictionaries.
    """
    if not filters:
        filters = {}

    columns = get_columns()
    data = get_data(filters)
    
    return columns, data

def get_columns():
    """
    Defines the columns for the report.
    """
    return [
        {
            "label": _("Month"),
            "fieldname": "month",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("Total Collection"),
            "fieldname": "total_collection",
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "label": _("Tithes"),
            "fieldname": "tithes",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("Offering"),
            "fieldname": "offering",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("Mission"),
            "fieldname": "mission",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("Benevolence"),
            "fieldname": "benevolence",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("Loose"),
            "fieldname": "loose",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("Sunday School"),
            "fieldname": "sunday_school",
            "fieldtype": "Currency",
            "width": 150
        }
    ]

def get_data(filters):
    """
    Fetches the data from the database based on the provided filters.
    """
    conditions = ""
    query_args = {}

    # Safely add year filter
    # The 'year' filter is mandatory as defined in the JS file.
    year = filters.get("year")
    conditions += "WHERE YEAR(date) = %(year)s"
    query_args["year"] = year

    # Add month filter only if a month is selected by the user
    if filters.get("month"):
        conditions += " AND MONTHNAME(date) = %(month)s"
        query_args["month"] = filters.get("month")

    # The main SQL query
    query = f"""
        SELECT
            MONTHNAME(date) as month,
            SUM(all_grand_total) as total_collection,
            SUM(all_tithes_total) as tithes,
            SUM(all_offering_total) as offering,
            SUM(all_mission_total) as mission,
            SUM(all_benevolence_total) as benevolence,
            SUM(all_loose_total) as loose,
            SUM(sunday_school_collection) as sunday_school
        FROM `tabCollection`
        {conditions}
        GROUP BY MONTHNAME(date), MONTH(date)
        ORDER BY MONTH(date)
    """

    # Execute the query using Frappe's safe SQL function to prevent injection
    data = frappe.db.sql(query, query_args, as_dict=True)
    
    return data