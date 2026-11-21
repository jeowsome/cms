frappe.query_reports["Disbursement Audit Log"] = {
	filters: [
		{ fieldname: "from_date", label: __("From"), fieldtype: "Date" },
		{ fieldname: "to_date", label: __("To"), fieldtype: "Date" },
		{ fieldname: "user", label: __("User"), fieldtype: "Link", options: "User" },
		{ fieldname: "action", label: __("Action"), fieldtype: "Select",
		  options: ["", "Claim", "Reverse Claim", "Edit Claim", "Void", "Unvoid", "Amount Edit", "Fund Change",
		            "Purpose Change", "Department Change", "Paid By Change", "Line Edit", "Line Added", "Line Deleted",
		            "Payable Created", "Payable Updated", "Payable Cancelled", "Reimbursement", "Reimbursement Cancelled"] },
		{ fieldname: "year", label: __("Year"), fieldtype: "Int" },
		{ fieldname: "month", label: __("Month"), fieldtype: "Select",
		  options: ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"] },
		{ fieldname: "disbursement", label: __("Disbursement"), fieldtype: "Link", options: "Disbursement" },
		{ fieldname: "text", label: __("Search"), fieldtype: "Data" },
	],
};
