// Copyright (c) 2025, Jeomar Bayoguina and contributors
// For license information, please see license.txt

frappe.query_reports["Financial Summary GL"] = {
    "filters": [
        {
            "fieldname": "year",
            "label": __("Year"),
            "fieldtype": "Int",
            "default": new Date().getFullYear(),
            "reqd": 1
        }
    ]
};
