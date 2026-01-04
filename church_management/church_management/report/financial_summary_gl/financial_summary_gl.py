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
			"label": _("Total Collections (GL)"),
			"fieldname": "total_collection",
			"fieldtype": "Currency",
			"width": 150
		},
		{
			"label": _("Total Disbursements (GL)"),
			"fieldname": "total_disbursement",
			"fieldtype": "Currency",
			"width": 150
		},
		{
			"label": _("Net Income (GL)"),
			"fieldname": "net_difference",
			"fieldtype": "Currency",
			"width": 150
		}
	]

def get_data(filters):
	year = filters.get("year")
	
	# Fetch JE Accounts linked to Income (Collections) and Expense (Disbursements)
	entries = frappe.db.sql(f"""
		SELECT 
			MONTHNAME(je.posting_date) as month_name, 
			MONTH(je.posting_date) as month_num,
			acc.root_type,
			jea.cost_center,
			SUM(jea.credit) as total_credit,
			SUM(jea.debit) as total_debit
		FROM `tabJournal Entry` je
		JOIN `tabJournal Entry Account` jea ON je.name = jea.parent
		JOIN `tabAccount` acc ON jea.account = acc.name
		WHERE YEAR(je.posting_date) = %(year)s
		AND je.docstatus = 1
		AND acc.root_type IN ('Income', 'Expense')
		GROUP BY MONTH(je.posting_date), acc.root_type, jea.cost_center
		ORDER BY MONTH(je.posting_date), jea.cost_center
	""", {"year": year}, as_dict=True)
	
	# Process Data
	# Structure: Month -> Cost Center -> {coll, disb}
	data_map = defaultdict(lambda: defaultdict(lambda: {"collection": 0, "disbursement": 0}))
	month_totals = defaultdict(lambda: {"collection": 0, "disbursement": 0})

	for entry in entries:
		# Use "Unspecified" if no cost center
		cc_name = entry.cost_center if entry.cost_center else _("Unspecified")
		
		# Identify Amount Type
		coll = 0
		disb = 0
		if entry.root_type == "Income":
			coll = entry.total_credit
		elif entry.root_type == "Expense":
			disb = entry.total_debit
			
		# Add to breakdowns
		data_map[entry.month_name][cc_name]["collection"] += coll
		data_map[entry.month_name][cc_name]["disbursement"] += disb
		
		# Add to Monthly Totals
		month_totals[entry.month_name]["collection"] += coll
		month_totals[entry.month_name]["disbursement"] += disb
		
	month_order = [
		"January", "February", "March", "April", "May", "June", "July",
		"August", "September", "October", "November", "December"
	]
	
	report_rows = []
	grand_total_coll = 0
	grand_total_disb = 0
	
	for month in month_order:
		m_coll = month_totals[month]["collection"]
		m_disb = month_totals[month]["disbursement"]
		
		if m_coll == 0 and m_disb == 0:
			continue
			
		grand_total_coll += m_coll
		grand_total_disb += m_disb
		
		# Month Header Row
		report_rows.append({
			"month": f"<b>{month}</b>",
			"total_collection": m_coll,
			"total_disbursement": m_disb,
			"net_difference": m_coll - m_disb,
			"indent": 0
		})
		
		# Child Rows (Cost Centers)
		for cc, values in data_map[month].items():
			report_rows.append({
				"month": cc,
				"total_collection": values["collection"],
				"total_disbursement": values["disbursement"],
				"net_difference": values["collection"] - values["disbursement"],
				"indent": 1
			})
			
		report_rows.append({}) # Empty row separator? Maybe not needed with indentation.
		
	if report_rows:
		report_rows.append({
			"month": "<b>Grand Total</b>",
			"total_collection": grand_total_coll,
			"total_disbursement": grand_total_disb,
			"net_difference": grand_total_coll - grand_total_disb,
			"indent": 0
		})
		
	return report_rows
