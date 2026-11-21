frappe.query_reports["Creditor History"] = {
	filters: [
		{ fieldname: "creditor", label: __("Creditor"), fieldtype: "Link", options: "Creditor", reqd: 1 },
		{ fieldname: "from_date", label: __("From"), fieldtype: "Date" },
		{ fieldname: "to_date", label: __("To"), fieldtype: "Date" },
	],
};
