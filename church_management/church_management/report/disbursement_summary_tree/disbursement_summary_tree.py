# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data

def get_columns():
	return [
		{
			"fieldname": "description",
			"label": _("Description"),
			"fieldtype": "Data",
			"width": 300
		},
		{
			"fieldname": "disbursed_amount",
			"label": _("Disbursed Amount"),
			"fieldtype": "Currency",
			"width": 120
		}
	]

def get_data(filters):
	if not filters:
		filters = {}

	data = []
	
	# Month mapping for sorting
	month_map = {
		"January": 1, "February": 2, "March": 3, "April": 4, 
		"May": 5, "June": 6, "July": 7, "August": 8, 
		"September": 9, "October": 10, "November": 11, "December": 12
	}

	# Build WHERE conditions
	conditions = []
	values = {}

	if filters.get("year"):
		conditions.append("p.year_recorded = %(year)s")
		values["year"] = filters.get("year")
	
	if filters.get("month"):
		conditions.append("p.month_recorded = %(month)s")
		values["month"] = filters.get("month")

	if filters.get("purpose"):
		conditions.append("c.purpose = %(purpose)s")
		values["purpose"] = filters.get("purpose")

	if filters.get("department"):
		conditions.append("c.department LIKE %(department)s")
		values["department"] = "%" + filters.get("department") + "%"

	where_clause = "AND " + " AND ".join(conditions) if conditions else ""

	# Fetch data
	query = f"""
		SELECT 
			p.month_recorded,
			p.year_recorded,
			c.purpose,
			c.department,
			c.disbursed_amount
		FROM 
			`tabDisbursement Item` c
			JOIN `tabDisbursement` p ON c.parent = p.name
		WHERE
			p.docstatus = 0
			{where_clause}
		ORDER BY 
			p.year_recorded ASC, p.month_recorded ASC
	"""
	
	items = frappe.db.sql(query, values, as_dict=True)

	# Enhance items with month sorting index and sort in Python
	for item in items:
		item['month_idx'] = month_map.get(item.month_recorded, 0)

	# Sort: Year, then Month Index
	items.sort(key=lambda x: (x.year_recorded, x.month_idx))

	# Grouping Logic
	# Structure: Month -> Purpose -> Department
	
	grouped = {}
	
	for item in items:
		period = f"{item.month_recorded} {item.year_recorded}"
		if period not in grouped:
			grouped[period] = {"total": 0.0, "purposes": {}}
		
		grouped[period]["total"] += (item.disbursed_amount or 0.0)

		purpose = item.purpose or _("Unspecified")
		if purpose not in grouped[period]["purposes"]:
			grouped[period]["purposes"][purpose] = {"total": 0.0, "departments": {}}
		
		grouped[period]["purposes"][purpose]["total"] += (item.disbursed_amount or 0.0)

		dept = item.department or _("Unspecified")
		if dept not in grouped[period]["purposes"][purpose]["departments"]:
			grouped[period]["purposes"][purpose]["departments"][dept] = 0.0
		
		grouped[period]["purposes"][purpose]["departments"][dept] += (item.disbursed_amount or 0.0)

	# Build Tree Rows
	grand_total = 0.0

	for period in grouped:
		period_data = grouped[period]
		grand_total += period_data["total"]
		
		# Level 0: Month
		data.append({
			"description": frappe.bold(period),
			"disbursed_amount": period_data["total"],
			"indent": 0
		})

		for purpose in period_data["purposes"]:
			purpose_data = period_data["purposes"][purpose]
			
			# Level 1: Purpose
			data.append({
				"description": frappe.bold(purpose),
				"disbursed_amount": purpose_data["total"],
				"indent": 1
			})

			for dept in purpose_data["departments"]:
				amount = purpose_data["departments"][dept]
				
				# Level 2: Department
				data.append({
					"description": dept,
					"disbursed_amount": amount,
					"indent": 2
				})
	
	if data:
		data.append({})
		data.append({
			"description": _("Grand Total"),
			"disbursed_amount": grand_total,
			"indent": 0,
			"is_bold": 1
		})

	return data
