"""Searchable audit trail of every disbursement line change."""
import frappe
from frappe import _

from church_management.api import permissions as perms
from church_management.api.finance import search_audit_log


def execute(filters=None):
	perms.require_finance()
	f = frappe._dict(filters or {})
	rows = search_audit_log(from_date=f.from_date, to_date=f.to_date, user=f.user, action=f.action,
							month=f.month, year=f.year, disbursement=f.disbursement, text=f.text, limit=5000)
	columns = [
		{"label": _("When"), "fieldname": "timestamp", "fieldtype": "Datetime", "width": 160},
		{"label": _("User"), "fieldname": "user_name", "fieldtype": "Data", "width": 140},
		{"label": _("Action"), "fieldname": "action", "fieldtype": "Data", "width": 130},
		{"label": _("Disbursement"), "fieldname": "disbursement", "fieldtype": "Link", "options": "Disbursement", "width": 130},
		{"label": _("Section"), "fieldname": "section", "fieldtype": "Data", "width": 140},
		{"label": _("Line"), "fieldname": "line_label", "fieldtype": "Data", "width": 200},
		{"label": _("Amount (after)"), "fieldname": "amount", "fieldtype": "Currency", "width": 110},
		{"label": _("Change"), "fieldname": "summary", "fieldtype": "Data", "width": 320},
		{"label": _("Reason"), "fieldname": "reason", "fieldtype": "Data", "width": 260},
		{"label": _("Reference"), "fieldname": "reference_name", "fieldtype": "Dynamic Link", "options": "reference_doctype", "width": 150},
		{"label": _("Reference Type"), "fieldname": "reference_doctype", "fieldtype": "Data", "hidden": 1},
		{"label": _("Entry"), "fieldname": "name", "fieldtype": "Link", "options": "Disbursement Audit Log", "width": 110},
	]
	for r in rows:
		r["summary"] = (r.get("summary") or "").replace("\n", " · ")
	return columns, rows
