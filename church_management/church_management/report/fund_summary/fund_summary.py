"""Fund Summary: collections, committed disbursements and balance per fund
for any range of months. Same figures as the finance app and the export
(church_management.church_management.fund_summary)."""
import frappe
from frappe import _

from church_management.api import permissions as perms
from church_management.church_management import fund_summary


def execute(filters=None):
	perms.require_finance()
	filters = frappe._dict(filters or {})
	fs = fund_summary.compute(filters.from_date, filters.to_date)
	n = fs["months"]
	columns = [
		{"label": _("Line"), "fieldname": "line", "fieldtype": "Data", "width": 360},
		{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 160},
		{"label": _("Monthly Average"), "fieldname": "avg", "fieldtype": "Currency", "width": 160},
	]
	rows = []

	def add(line, amount=None, indent=0, bold=False):
		rows.append({"line": line, "amount": amount, "avg": round(amount / n, 2) if amount is not None else None,
					 "indent": indent, "bold": 1 if bold else 0})

	order = ("Mission", "Benevolence", "White Gift", "General")
	add(_("TOTAL COLLECTIONS"), fs["collections"]["total"], bold=True)
	for f in order:
		add(_("{0} Fund").format(f), fs["collections"]["by_fund"][f], 1)
	add(_("TOTAL DISBURSEMENTS (committed)"), fs["disbursements"]["total"], bold=True)
	for f in order:
		add(_("{0} Disbursements").format(f), fs["disbursements"]["by_fund"][f], 1)
		if f == "General":
			for p, v in fs["disbursements"]["general_by_purpose"].items():
				add(p, v, 2)
	add(_("SURPLUS / (DEFICIT)"), fs["surplus"], bold=True)
	add("")
	for f in fs["funds"]:
		add(_("{0} FUND").format(f["fund"].upper()), None, bold=True)
		add(_("Collections"), f["collections"], 1)
		add(_("Disbursements"), f["disbursements"], 1)
		add(_("Balance"), f["balance"], 1, bold=True)
		add(_("Paid out (church money)"), f["paid_out"], 1)
		add(_("Pending claims"), f["pending"], 1)
		add(_("Owed to creditors"), f["owed"], 1)
		add(_("After pending claims and payables"), f["after_pending_and_payables"], 1)
		comment = (fs.get("comments") or {}).get(f["fund"], {}).get("comments")
		if comment:
			for ln in comment.splitlines():
				add("💬 " + ln, None, 1)
	add("")
	add(_("DISBURSEMENT PER DEPARTMENT"), None, bold=True)
	for d in fs["by_department"]:
		add(d["department"], d["total"], 1, bold=True)
		for p, v in d["purposes"].items():
			add(p, v, 2)
	add(_("DISBURSEMENT PER PURPOSE"), None, bold=True)
	for p, v in fs["by_purpose"].items():
		add(p, v, 1)
	message = _("{0} · {1} month(s). Collections = active GL postings (cash + cashless; White Gift all years). "
				"Disbursements = Claimed + Unclaimed, Voided excluded.").format(fs["period"], n)
	return columns, rows, message
