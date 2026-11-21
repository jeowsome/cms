"""Money we owe to others: expenses a creditor paid on the church's behalf.

Kept outside the GL, like claims: a claimed line is deducted from its source
account by the statement, not posted. So:

  creditor pays    the line is Claimed with Paid By = Creditor. The expense
                   counts in every purpose/department/fund report, no church
                   account moves, and a submitted Creditor Payable records
                   what we owe (synced from the line on every save).
  we reimburse     a submitted Creditor Reimbursement settles one or more
                   payables (in full or in part) from one source account of
                   the same fund. The statement deducts it from that account
                   on its date. The expense is not counted again.

A payable can also be entered directly, for an expense that was never on a
monthly disbursement document; it then counts as an expense itself.
"""
import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

from church_management.church_management import disbursement_audit as audit
from church_management.church_management import finance as fin


# ---------------------------------------------------------------- payable state

def refresh_payable(name):
	"""Recompute paid / outstanding / status from submitted reimbursements."""
	if not fin.schema_ready():
		return
	p = frappe.db.get_value("Creditor Payable", name, ["amount", "docstatus"], as_dict=True)
	if not p:
		return
	paid = flt(frappe.db.sql(
		"""select coalesce(sum(a.amount), 0) from `tabCreditor Reimbursement Allocation` a
		join `tabCreditor Reimbursement` r on r.name = a.parent
		where a.payable = %s and r.docstatus = 1""", name)[0][0])
	outstanding = flt(p.amount) - paid
	if p.docstatus == 2:
		status = "Cancelled"
	elif p.docstatus == 0:
		status = "Draft"
	elif outstanding <= 0.005:
		status = "Paid"
	elif paid > 0:
		status = "Partly Paid"
	else:
		status = "Unpaid"
	frappe.db.set_value("Creditor Payable", name,
		{"paid_amount": paid, "outstanding_amount": outstanding, "status": status}, update_modified=False)


def outstanding_as_of(as_of=None, payable_names=None):
	"""{payable: outstanding} counting only reimbursements dated on/before as_of."""
	if not fin.schema_ready():
		return {}
	filters = {"docstatus": 1}
	if payable_names is not None:
		if not payable_names:
			return {}
		filters["name"] = ["in", list(payable_names)]
	if as_of:
		filters["posting_date"] = ["<=", as_of]
	pays = frappe.get_all("Creditor Payable", filters=filters, fields=["name", "amount"])
	if not pays:
		return {}
	cond, args = "", [tuple(p.name for p in pays)]
	if as_of:
		cond, args = " and r.posting_date <= %s", args + [as_of]
	paid = dict(frappe.db.sql(
		f"""select a.payable, sum(a.amount) from `tabCreditor Reimbursement Allocation` a
		join `tabCreditor Reimbursement` r on r.name = a.parent
		where a.payable in %s and r.docstatus = 1{cond} group by a.payable""", args))
	return {p.name: flt(p.amount) - flt(paid.get(p.name)) for p in pays}


# ---------------------------------------------------------------- sync from lines

def sync_from_disbursement(doc):
	"""Create, update or cancel the payable behind each creditor-paid line."""
	if not fin.schema_ready():
		return
	before = doc.get_doc_before_save()
	current = set()
	for field, _label, row in fin.iter_lines(doc):
		current.add(row.name)
		wanted = (doc.docstatus < 2 and fin.state(row) == fin.CLAIMED and fin.paid_by_creditor(row))
		if wanted:
			values = _payable_values(doc, field, row)
			if row.get("payable") and frappe.db.get_value("Creditor Payable", row.payable, "docstatus") == 1:
				_update_payable(doc, field, row, values)
			else:
				p = frappe.get_doc({"doctype": "Creditor Payable", "source_type": "Disbursement Line", **values})
				p.flags.from_line = True
				p.insert(ignore_permissions=True)
				p.submit()
				_set_row_payable(row, p.name)
				audit.log(doc, field, row, "Payable Created",
					{"payable": [None, p.name], "amount": [None, flt(p.amount)]},
					audit._reason(doc, row.name), ("Creditor Payable", p.name))
		elif row.get("payable"):
			_cancel_line_payable(doc, field, row, row.payable)
			_set_row_payable(row, None)
	if before:
		for field, _label, row in fin.iter_lines(before):
			if row.name not in current and row.get("payable"):
				_cancel_line_payable(doc, field, row, row.payable)


def _payable_values(doc, field, row):
	return {
		"creditor": row.creditor,
		"posting_date": row.creditor_paid_date,
		"amount": flt(row.amount),
		"reference": row.get("creditor_reference"),
		"fund": fin.fund_for_source(row.get("source")),
		"purpose": row.get("purpose") or "Allowance",
		"department": row.get("department"),
		"description": (fin.line_label(row) or doc.name)[:140],
		"disbursement": doc.name,
		"disbursement_row": row.name,
		"section": fin.SECTION_LABEL.get(field, field),
	}


def _set_row_payable(row, value):
	row.payable = value
	frappe.db.set_value(row.doctype, row.name, "payable", value, update_modified=False)


def _update_payable(doc, field, row, values):
	p = frappe.get_doc("Creditor Payable", row.payable)
	diff = {k: [p.get(k), v] for k, v in values.items()
			if k in ("amount", "posting_date", "reference", "fund", "purpose", "department", "description", "creditor")
			and (flt(p.get(k)) != flt(v) if k == "amount" else str(p.get(k) or "") != str(v or ""))}
	if not diff:
		return
	if "creditor" in diff or "posting_date" in diff:
		# Different creditor/date is a different debt: replace the payable
		_cancel_line_payable(doc, field, row, p.name)
		_set_row_payable(row, None)
		new = frappe.get_doc({"doctype": "Creditor Payable", "source_type": "Disbursement Line", **values})
		new.flags.from_line = True
		new.insert(ignore_permissions=True)
		new.submit()
		_set_row_payable(row, new.name)
		audit.log(doc, field, row, "Payable Created", {"payable": [p.name, new.name], "amount": [None, flt(new.amount)]},
			audit._reason(doc, row.name), ("Creditor Payable", new.name))
		return
	for k, (_a, b) in diff.items():
		p.set(k, b)
	p.flags.from_line = True
	p.save(ignore_permissions=True)
	audit.log(doc, field, row, "Payable Updated", diff, audit._reason(doc, row.name), ("Creditor Payable", p.name))


def _cancel_line_payable(doc, field, row, name):
	p = frappe.get_doc("Creditor Payable", name)
	if p.docstatus != 1:
		return
	p.flags.from_line = True
	p.cancel()
	audit.log(doc, field, row, "Payable Cancelled", {"payable": [name, None], "amount": [flt(p.amount), None]},
		audit._reason(doc, row.name), ("Creditor Payable", name))


# ---------------------------------------------------------------- reports

def who_we_owe(as_of=None, creditor=None):
	"""Outstanding balance per creditor with the items behind it and their age."""
	as_of = getdate(as_of or nowdate())
	filters = {"docstatus": 1, "posting_date": ["<=", as_of]}
	if creditor:
		filters["creditor"] = creditor
	pays = frappe.get_all("Creditor Payable", filters=filters,
		fields=["name", "creditor", "posting_date", "amount", "fund", "purpose", "department", "description",
				"reference", "source_type", "disbursement", "section"],
		order_by="posting_date asc, name asc")
	out_map = outstanding_as_of(as_of, [p.name for p in pays])
	by = {}
	for p in pays:
		bal = out_map.get(p.name, 0.0)
		if bal <= 0.005:
			continue
		c = by.setdefault(p.creditor, {"creditor": p.creditor, "outstanding": 0.0, "items": []})
		c["outstanding"] += bal
		c["items"].append({**p, "outstanding": bal, "reimbursed": flt(p.amount) - bal,
						   "age_days": (as_of - getdate(p.posting_date)).days})
	rows = sorted(by.values(), key=lambda c: -c["outstanding"])
	for c in rows:
		c["oldest_days"] = max(i["age_days"] for i in c["items"])
	return {"as_of": str(as_of), "total": sum(c["outstanding"] for c in rows), "creditors": rows}


def creditor_history(creditor, from_date=None, to_date=None):
	"""What a creditor paid for us, what we repaid, and the running balance."""
	rows = []
	for p in frappe.get_all("Creditor Payable", filters={"creditor": creditor, "docstatus": 1},
			fields=["name", "posting_date", "amount", "description", "fund", "purpose", "reference", "disbursement"]):
		rows.append({"date": p.posting_date, "type": "Paid for us", "document": p.name, "doctype": "Creditor Payable",
					 "description": p.description, "fund": p.fund, "reference": p.reference,
					 "disbursement": p.disbursement, "increase": flt(p.amount), "decrease": 0.0})
	for r in frappe.get_all("Creditor Reimbursement", filters={"creditor": creditor, "docstatus": 1},
			fields=["name", "posting_date", "total_amount", "source_account", "fund", "reference", "received_by"]):
		rows.append({"date": r.posting_date, "type": "We repaid", "document": r.name, "doctype": "Creditor Reimbursement",
					 "description": f"From {r.source_account} · received by {r.received_by}", "fund": r.fund,
					 "reference": r.reference, "disbursement": None, "increase": 0.0, "decrease": flt(r.total_amount)})
	rows.sort(key=lambda x: (getdate(x["date"]), 0 if x["increase"] else 1, x["document"]))
	bal = 0.0
	out = []
	for x in rows:
		bal += x["increase"] - x["decrease"]
		x["balance"] = bal
		if (not from_date or getdate(x["date"]) >= getdate(from_date)) and (not to_date or getdate(x["date"]) <= getdate(to_date)):
			out.append(x)
	return {"creditor": creditor, "balance": bal, "rows": out}


def reimbursed_by_account(from_date, to_date):
	"""Cash that left each source account to repay creditors, by reimbursement date."""
	if not fin.schema_ready():
		return {}
	return dict(frappe.db.sql(
		"""select source_account, sum(total_amount) from `tabCreditor Reimbursement`
		where docstatus = 1 and posting_date between %s and %s group by source_account""",
		(from_date, to_date)))


def owed_by_fund(as_of=None, payable_names=None):
	"""Outstanding payables per fund."""
	out_map = outstanding_as_of(as_of, payable_names)
	if not out_map:
		return {}
	funds = dict(frappe.get_all("Creditor Payable", filters={"name": ["in", list(out_map)]},
		fields=["name", "fund"], as_list=True))
	by = {}
	for name, bal in out_map.items():
		if bal > 0.005:
			by[funds[name]] = by.get(funds[name], 0.0) + bal
	return by
