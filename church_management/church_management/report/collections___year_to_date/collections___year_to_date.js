// Copyright (c) 2025, [Your Name] and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Collections - Year To Date"] = {
	"filters": [
		{
			"fieldname": "from_year",
			"label": __("From Year"),
			"fieldtype": "Int",
			"default": new Date().getFullYear() - 2, // Default to 3 years ago
			"reqd": 1
		},
		{
			"fieldname": "to_year",
			"label": __("To Year"),
			"fieldtype": "Int",
			"default": new Date().getFullYear(), // Default to current year
			"reqd": 1
		},
		{
			"fieldname": "month",
			"label": __("Up to Month"),
			"fieldtype": "Select",
			"options": [
                "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"
            ],
            // Sets default to the current month name
			"default": new Date().toLocaleString('en-US', { month: 'long' }),
			"reqd": 1
		}
	]
};