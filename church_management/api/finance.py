"""Finance endpoints for the SPA: creditors and payables, reimbursements,
the Fund Summary (with the finance team's comments) and the audit log.

Every endpoint is Finance Team / System Manager only (perms.require_finance).
"""
import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

from church_management.api import permissions as perms
from church_management.church_management import creditors as cred
from church_management.church_management import disbursement_audit as audit
from church_management.church_management import fund_summary
from church_management.church_management import finance as fin


# ---------------------------------------------------------------- creditors

@frappe.whitelist()
def get_creditors(include_inactive=0):
	perms.require_finance()
	filters = {} if int(include_inactive or 0) else {"active": 1}
	return frappe.get_all("Creditor", filters=filters, fields=["name", "active", "contact_person", "contact_number", "notes"],
		order_by="name asc")


@frappe.whitelist()
def save_creditor(creditor_name, contact_person=None, contact_number=None, notes=None, active=1):
	perms.require_finance()
	name = (creditor_name or "").strip()
	if not name:
		frappe.throw(_("Creditor name is required."))
	doc = frappe.get_doc("Creditor", name) if frappe.db.exists("Creditor", name) else frappe.new_doc("Creditor")
	doc.update({"creditor_name": name, "contact_person": contact_person, "contact_number": contact_number,
				"notes": notes, "active": int(active)})
	doc.save(ignore_permissions=True)
	return doc.name


@frappe.whitelist()
def who_we_owe(as_of=None):
	perms.require_finance()
	return cred.who_we_owe(as_of)


@frappe.whitelist()
def creditor_history(creditor, from_date=None, to_date=None):
	perms.require_finance()
	return cred.creditor_history(creditor, from_date, to_date)


@frappe.whitelist()
def get_open_payables(creditor):
	perms.require_finance()
	cred_rows = cred.who_we_owe(None, creditor)["creditors"]
	return cred_rows[0]["items"] if cred_rows else []


@frappe.whitelist()
def create_direct_payable(creditor, posting_date, amount, fund, purpose, department, description, reference=None, reason=None):
	"""Record an expense a creditor paid that is not on any monthly document."""
	perms.require_finance()
	p = frappe.get_doc({
		"doctype": "Creditor Payable", "source_type": "Direct", "creditor": creditor, "posting_date": posting_date,
		"amount": flt(amount), "fund": fund, "purpose": purpose, "department": department,
		"description": description, "reference": reference,
	})
	p.flags.audit_reason = reason
	p.insert(ignore_permissions=True)
	p.submit()
	return p.name


@frappe.whitelist()
def cancel_direct_payable(name, reason):
	perms.require_finance()
	audit.require_reason(reason, _("cancelling a payable"))
	p = frappe.get_doc("Creditor Payable", name)
	p.flags.audit_reason = reason
	p.flags.ignore_permissions = True
	p.cancel()
	return {"success": True}


@frappe.whitelist()
def create_reimbursement(creditor, posting_date, source_account, received_by, allocations, reference=None, remarks=None):
	"""Pay a creditor back. allocations: [{payable, amount}] — one payable may be paid in part."""
	perms.require_finance()
	allocations = frappe.parse_json(allocations) if isinstance(allocations, str) else allocations
	r = frappe.get_doc({
		"doctype": "Creditor Reimbursement", "creditor": creditor, "posting_date": posting_date,
		"source_account": source_account, "received_by": received_by, "reference": reference, "remarks": remarks,
		"allocations": [{"payable": a["payable"], "amount": flt(a["amount"])} for a in allocations if flt(a.get("amount"))],
	})
	r.insert(ignore_permissions=True)
	r.submit()
	return r.name


@frappe.whitelist()
def cancel_reimbursement(name, reason):
	perms.require_finance()
	audit.require_reason(reason, _("cancelling a reimbursement"))
	r = frappe.get_doc("Creditor Reimbursement", name)
	r.flags.audit_reason = reason
	r.flags.ignore_permissions = True
	r.cancel()
	return {"success": True}


# ---------------------------------------------------------------- fund summary

@frappe.whitelist()
def get_fund_summary(from_date=None, to_date=None):
	perms.require_finance()
	from_date, to_date = _range(from_date, to_date)
	return fund_summary.compute(from_date, to_date)


@frappe.whitelist()
def save_fund_comment(from_date, to_date, fund, comments):
	perms.require_finance()
	if fund not in fin.FUNDS:
		frappe.throw(_("Unknown fund {0}.").format(fund))
	name = frappe.db.get_value("Fund Summary Comment", {"from_date": from_date, "to_date": to_date, "fund": fund})
	doc = frappe.get_doc("Fund Summary Comment", name) if name else frappe.new_doc("Fund Summary Comment")
	doc.update({"from_date": from_date, "to_date": to_date, "fund": fund, "comments": comments})
	doc.save(ignore_permissions=True)
	return {"name": doc.name, "modified": str(doc.modified)}


def _range(from_date, to_date):
	today = getdate(nowdate())
	f = getdate(from_date) if from_date else today.replace(month=1, day=1)
	t = getdate(to_date) if to_date else today
	if f > t:
		frappe.throw(_("From must be on or before To."))
	return str(f), str(t)


# ---------------------------------------------------------------- audit log

@frappe.whitelist()
def search_audit_log(from_date=None, to_date=None, user=None, action=None, month=None, year=None,
					 disbursement=None, text=None, limit=500):
	perms.require_finance()
	filters = []
	if from_date:
		filters.append(["timestamp", ">=", f"{from_date} 00:00:00"])
	if to_date:
		filters.append(["timestamp", "<=", f"{to_date} 23:59:59"])
	if user:
		filters.append(["user", "=", user])
	if action:
		filters.append(["action", "=", action])
	if month:
		filters.append(["month", "=", month])
	if year:
		filters.append(["year", "=", int(year)])
	if disbursement:
		filters.append(["disbursement", "=", disbursement])
	or_filters = None
	if text:
		like = f"%{text}%"
		or_filters = [["line_label", "like", like], ["summary", "like", like], ["reason", "like", like],
					  ["reference_name", "like", like]]
	return frappe.get_all(
		"Disbursement Audit Log", filters=filters, or_filters=or_filters,
		fields=["name", "timestamp", "user", "user_name", "action", "disbursement", "month", "year", "section",
				"row_name", "line_label", "amount", "summary", "reason", "reference_doctype", "reference_name"],
		order_by="timestamp desc, creation desc", limit_page_length=int(limit),
	)


@frappe.whitelist()
def get_audit_actions():
	perms.require_finance()
	return (frappe.get_meta("Disbursement Audit Log").get_field("action").options or "").split("\n")
