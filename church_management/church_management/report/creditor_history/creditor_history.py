"""What a creditor paid for us, what we repaid, and the running balance."""
import frappe
from frappe import _

from church_management.api import permissions as perms
from church_management.church_management import creditors


def execute(filters=None):
	perms.require_finance()
	f = frappe._dict(filters or {})
	if not f.creditor:
		return [], []
	data = creditors.creditor_history(f.creditor, f.from_date, f.to_date)
	columns = [
		{"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 110},
		{"label": _("Type"), "fieldname": "type", "fieldtype": "Data", "width": 110},
		{"label": _("Document"), "fieldname": "document", "fieldtype": "Dynamic Link", "options": "doctype", "width": 150},
		{"label": _("Doctype"), "fieldname": "doctype", "fieldtype": "Data", "hidden": 1},
		{"label": _("Description"), "fieldname": "description", "fieldtype": "Data", "width": 280},
		{"label": _("Fund"), "fieldname": "fund", "fieldtype": "Data", "width": 100},
		{"label": _("Paid for us"), "fieldname": "increase", "fieldtype": "Currency", "width": 120},
		{"label": _("We repaid"), "fieldname": "decrease", "fieldtype": "Currency", "width": 120},
		{"label": _("Balance owed"), "fieldname": "balance", "fieldtype": "Currency", "width": 130},
		{"label": _("Reference"), "fieldname": "reference", "fieldtype": "Data", "width": 120},
	]
	return columns, data["rows"]
