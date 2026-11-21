frappe.query_reports["Who We Owe"] = {
	filters: [
		{ fieldname: "as_of", label: __("As of"), fieldtype: "Date", default: frappe.datetime.get_today() },
		{ fieldname: "creditor", label: __("Creditor"), fieldtype: "Link", options: "Creditor" },
	],
	tree: true,
	initial_depth: 1,
};
