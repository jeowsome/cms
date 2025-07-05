// Copyright (c) 2025, [Your Name] and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Disbursement Summary"] = {
	"filters": [
		{
			"fieldname": "year",
			"label": __("Year"),
			"fieldtype": "Int",
			"default": new Date().getFullYear(),
			"reqd": 1
		}
	],
    // <-- NEW: Formatter function added to apply custom styling -->
    "formatter": function(value, row, column, data, default_formatter) {
        // First, run the default formatter to handle links, currencies, etc.
        value = default_formatter(value, row, column, data);

        // Check if we are in the 'details' column AND it's a parent row (indent is 0)
        if (column.fieldname == "details" && row.meta.indent === 0) {
            // If it is, wrap the value in <strong> tags to make it bold
            return `<strong>${value}</strong>`;
        }
        return value;
    }
};