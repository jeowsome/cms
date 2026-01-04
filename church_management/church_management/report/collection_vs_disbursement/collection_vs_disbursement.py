# Copyright (c) 2025, Jeomar Bayoguina and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from collections import defaultdict

def execute(filters=None):
	if not filters: filters = {}
	
	columns = get_columns()
	data = get_data(filters)
	
	return columns, data

def get_columns():
	return [
		{
			"label": _("Month"),
			"fieldname": "month",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Total Collections"),
			"fieldname": "total_collection",
			"fieldtype": "Currency",
			"width": 150
		},
		{
			"label": _("Total Disbursements"),
			"fieldname": "total_disbursement",
			"fieldtype": "Currency",
			"width": 150
		},
		{
			"label": _("Net Difference"),
			"fieldname": "net_difference",
			"fieldtype": "Currency",
			"width": 150
		}
	]

def get_data(filters):
	year = filters.get("year")
	
	# Fetch Collections
	collections = frappe.db.sql(f"""
		SELECT 
			MONTHNAME(date) as month_name, 
			MONTH(date) as month_num,
			SUM(grand_total + all_grand_total) as total 
		FROM `tabCollection`
		WHERE YEAR(date) = %(year)s
		AND docstatus = 1
		GROUP BY MONTH(date)
		ORDER BY MONTH(date)
	""", {"year": year}, as_dict=True)
	
	# Fetch Disbursements
	disbursements = frappe.db.sql(f"""
		SELECT 
			month_recorded as month_name, 
			SUM(total_amount_disbursed) as total 
		FROM `tabDisbursement`
		WHERE year_recorded = %(year)s
		AND docstatus = 1
		GROUP BY month_recorded
	""", {"year": year}, as_dict=True)
	
	# Process Data
	data_map = defaultdict(lambda: {"collection": 0, "disbursement": 0})
	
	for c in collections:
		data_map[c.month_name]["collection"] = c.total
		
	for d in disbursements:
		data_map[d.month_name]["disbursement"] = d.total
		
	month_order = [
		"January", "February", "March", "April", "May", "June", "July",
		"August", "September", "October", "November", "December"
	]
	
	report_rows = []
	total_coll = 0
	total_disb = 0
	
	for month in month_order:
		coll = data_map[month]["collection"]
		disb = data_map[month]["disbursement"]
		
		if coll == 0 and disb == 0:
			continue
			
		total_coll += coll
		total_disb += disb
		
		report_rows.append({
			"month": month,
			"total_collection": coll,
			"total_disbursement": disb,
			"net_difference": coll - disb
		})
		
	if report_rows:
		report_rows.append({})
		report_rows.append({
			"month": "<b>Total</b>",
			"total_collection": total_coll,
			"total_disbursement": total_disb,
			"net_difference": total_coll - total_disb
		})
		
	return report_rows
