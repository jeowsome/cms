"""Outstanding balance per creditor, with the items behind it and their age."""
import frappe
from frappe import _

from church_management.api import permissions as perms
from church_management.church_management import creditors


def execute(filters=None):
	perms.require_finance()
	f = frappe._dict(filters or {})
	data = creditors.who_we_owe(f.as_of, f.creditor)
	columns = [
		{"label": _("Creditor / Item"), "fieldname": "label", "fieldtype": "Data", "width": 320},
		{"label": _("Payable"), "fieldname": "payable", "fieldtype": "Link", "options": "Creditor Payable", "width": 140},
		{"label": _("Date Paid For Us"), "fieldname": "posting_date", "fieldtype": "Date", "width": 120},
		{"label": _("Age (days)"), "fieldname": "age_days", "fieldtype": "Int", "width": 90},
		{"label": _("Fund"), "fieldname": "fund", "fieldtype": "Data", "width": 100},
		{"label": _("Purpose"), "fieldname": "purpose", "fieldtype": "Data", "width": 130},
		{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 120},
		{"label": _("Reimbursed"), "fieldname": "reimbursed", "fieldtype": "Currency", "width": 120},
		{"label": _("Outstanding"), "fieldname": "outstanding", "fieldtype": "Currency", "width": 120},
		{"label": _("Disbursement"), "fieldname": "disbursement", "fieldtype": "Link", "options": "Disbursement", "width": 130},
	]
	rows = []
	for c in data["creditors"]:
		rows.append({"label": c["creditor"], "outstanding": c["outstanding"], "age_days": c["oldest_days"], "indent": 0})
		for i in c["items"]:
			rows.append({"label": i["description"], "payable": i["name"], "posting_date": i["posting_date"],
						 "age_days": i["age_days"], "fund": i["fund"], "purpose": i["purpose"], "amount": i["amount"],
						 "reimbursed": i["reimbursed"], "outstanding": i["outstanding"],
						 "disbursement": i.get("disbursement"), "indent": 1})
	rows.append({"label": _("Total owed"), "outstanding": data["total"], "indent": 0})
	return columns, rows
