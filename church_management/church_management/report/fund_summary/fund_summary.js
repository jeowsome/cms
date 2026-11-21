frappe.query_reports["Fund Summary"] = {
	filters: [
		{ fieldname: "from_date", label: __("From"), fieldtype: "Date", reqd: 1,
		  default: frappe.datetime.year_start() },
		{ fieldname: "to_date", label: __("To"), fieldtype: "Date", reqd: 1,
		  default: frappe.datetime.get_today() },
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		return data && data.bold ? `<b>${value}</b>` : value;
	},
	tree: false,
	initial_depth: 3,
};
