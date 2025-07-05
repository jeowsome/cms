// Copyright (c) 2024, [Your Name] and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Year-end Collections"] = {
    "filters": [
        {
            "fieldname": "year",
            "label": __("Year"),
            "fieldtype": "Int",
            "default": new Date().getFullYear(), // Sets default value to the current year
            "reqd": 1 // Makes this a mandatory field
        },
        {
            "fieldname": "month",
            "label": __("Month"),
            "fieldtype": "Select",
            "options": [
                "", // This empty option represents 'All Months'
                "January",
                "February",
                "March",
                "April",
                "May",
                "June",
                "July",
                "August",
                "September",
                "October",
                "November",
                "December"
            ]
        }
    ]
};