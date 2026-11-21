"""Line rules, guards and the append-only audit log for Disbursement lines.

Runs inside Disbursement.validate / on_update, so every path that changes a
line — the finance app, the desk form, a patch — goes through the same
rules and leaves the same trail:

  defaults   department from the worker (or Mission for mission support),
             purpose from the worker, White Gift lines -> White Gift Project
  guards     a claim needs Received By + Received Date; a claimed line can
             only change through Reverse claim / Edit claim with a reason;
             a voided line needs a reason; lines whose creditor payable has
             reimbursements cannot change what was reimbursed
  log        one Disbursement Audit Log entry per change, with the before and
             after value of every changed field and the reason

Callers say what they are doing through doc.flags:
  doc.flags.line_actions = {row_name: {"action": "Reverse Claim", "reason": "..."}}
  doc.flags.audit_reason = "reason for every change in this save"
"""
import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

from church_management.church_management import finance as fin

MIN_REASON = 5
DEPARTMENT_REQUIRED_FROM_YEAR = 2026

LABELS = {
	"status": "Claim Status", "amount": "Amount", "received_by": "Received By",
	"received_date": "Received Date", "source": "Source Account", "purpose": "Purpose",
	"department": "Department", "worker": "Payee / Worker", "description": "Description",
	"remarks": "Remarks", "void_reason": "Void Reason", "paid_by": "Paid By", "creditor": "Creditor",
	"creditor_paid_date": "Date Creditor Paid", "creditor_reference": "Creditor Reference",
	"is_planned": "Is Planned", "original_amount": "Original Amount",
}
TRACKED = tuple(LABELS)
CLAIM_FIELDS = ("amount", "received_by", "received_date", "source")
STATUS_FIELDS = ("status", "void_reason", "received_by", "received_date")
CREDITOR_FIELDS = ("paid_by", "creditor", "creditor_paid_date", "creditor_reference")
# A reimbursed payable fixes these on its line
PAYABLE_LOCKED = ("amount", "status", "paid_by", "creditor", "source")


# ---------------------------------------------------------------- helpers

def _norm(field, v):
	if field == "amount" or field == "original_amount":
		return flt(v)
	if field == "is_planned":
		return int(v or 0)
	if field in ("received_date", "creditor_paid_date"):
		return str(getdate(v)) if v else None
	if field == "paid_by":
		return v or fin.CHURCH
	if field == "status":
		return fin.state({"status": v})
	return (v or None) if not isinstance(v, str) else (v.strip() or None)


def _changed(prev, row, fields=TRACKED):
	out = {}
	present = set(row.meta.get_valid_columns()) if hasattr(row, "meta") else set(row)
	for f in fields:
		if f not in present:
			continue
		a, b = _norm(f, prev.get(f)), _norm(f, row.get(f))
		if a != b:
			out[f] = [a, b]
	return out


def _act(doc, row_name):
	return (doc.flags.line_actions or {}).get(row_name) or {}


def _reason(doc, row_name):
	r = _act(doc, row_name).get("reason") or doc.flags.audit_reason or ""
	return r.strip()


def require_reason(reason, what):
	if len((reason or "").strip()) < MIN_REASON:
		frappe.throw(_("Please give a reason for {0} (at least {1} characters).").format(what, MIN_REASON))


def _month_key(doc):
	m = fin.month_index(doc.month_recorded)
	return (int(doc.year_recorded), m) if m and doc.year_recorded else None


def _row_desc(field, row):
	return f"{fin.SECTION_LABEL.get(field, field)} · {fin.line_label(row)} (₱{flt(row.get('amount')):,.2f})"


# ---------------------------------------------------------------- defaults

def apply_defaults(doc):
	"""Fill department/purpose defaults before the guards run."""
	workers = {}

	def worker(name):
		if name and name not in workers:
			workers[name] = frappe.db.get_value(
				"Church Worker", name, ["disbursement_department", "default_purpose"], as_dict=True
			) or frappe._dict()
		return workers.get(name) or frappe._dict()

	for field, _label, row in fin.iter_lines(doc):
		if not row.get("paid_by"):
			row.paid_by = fin.CHURCH
		if row.get("status") not in (fin.CLAIMED, fin.UNCLAIMED, fin.VOIDED):
			row.status = fin.UNCLAIMED
		w = worker(row.get("worker"))
		if not row.get("purpose") and w.get("default_purpose"):
			row.purpose = w.default_purpose
		if not row.get("department"):
			if w.get("disbursement_department"):
				row.department = w.disbursement_department
			elif row.get("purpose") == "Mission Support":
				row.department = "Mission" if frappe.db.exists("Department Name", "Mission") else None
		if fin.fund_for_source(row.get("source")) == "White Gift" and frappe.db.exists("Disbursement Purpose", fin.WHITE_GIFT_PURPOSE):
			row.purpose = fin.WHITE_GIFT_PURPOSE


# ---------------------------------------------------------------- guards

def validate(doc):
	"""Guards for every line change. Called from Disbursement.validate."""
	before = doc.get_doc_before_save()
	old = {row.name: (field, row) for field, _l, row in fin.iter_lines(before)} if before else {}
	warnings = []
	year = int(doc.year_recorded or 0)
	missing_dept = []

	for field, _label, row in fin.iter_lines(doc):
		prev = old.get(row.name, (None, None))[1] if row.name else None
		st, pst = fin.state(row), fin.state(prev)
		act = _act(doc, row.name)
		reason = _reason(doc, row.name)
		what = _row_desc(field, row)

		if year >= DEPARTMENT_REQUIRED_FROM_YEAR and not row.get("department"):
			missing_dept.append(what)

		# Voided: needs a reason, and only an unclaimed line can be voided
		if st == fin.VOIDED:
			row.void_reason = (row.get("void_reason") or "").strip()
			if pst != fin.VOIDED:
				require_reason(row.void_reason, _("voiding {0}").format(what))
				if pst == fin.CLAIMED:
					frappe.throw(_("{0} is claimed. Reverse the claim first, then void it.").format(what))
				if row.get("payable"):
					frappe.throw(_("{0} was paid by a creditor; it cannot be voided.").format(what))
		elif pst == fin.VOIDED:
			require_reason(reason, _("restoring the voided line {0}").format(what))
			row.void_reason = None

		# A new claim needs who received it and when (or, for a creditor, who paid and when)
		if st == fin.CLAIMED and pst != fin.CLAIMED:
			if fin.paid_by_creditor(row):
				if not row.get("creditor") or not row.get("creditor_paid_date"):
					frappe.throw(_("{0}: choose the creditor and the date they paid.").format(what))
				if not row.get("received_date"):
					row.received_date = row.creditor_paid_date
			elif not row.get("received_by") or not row.get("received_date"):
				frappe.throw(_("{0}: Received By and Received Date are required to mark it Claimed.").format(what))

		if prev is not None and pst == fin.CLAIMED:
			changed = _changed(prev, row, CLAIM_FIELDS + CREDITOR_FIELDS)
			if st == fin.UNCLAIMED:
				if act.get("action") != "Reverse Claim":
					frappe.throw(_("{0} is claimed. Use Reverse claim and give a reason to set it back to Unclaimed.").format(what))
				require_reason(reason, _("reversing the claim on {0}").format(what))
				row.received_by = None
				row.received_date = None
			elif changed and act.get("action") not in ("Edit Claim",) and not doc.flags.allow_claim_edit:
				frappe.throw(_("{0} is claimed. Use Edit claim and give a reason to change {1}.").format(
					what, ", ".join(LABELS[f] for f in changed)))
			elif changed:
				require_reason(reason, _("editing the claim on {0}").format(what))
				if fin.paid_by_creditor(row) and (not row.get("creditor") or not row.get("creditor_paid_date")):
					frappe.throw(_("{0}: choose the creditor and the date they paid.").format(what))
				if not fin.paid_by_creditor(row) and (not row.get("received_by") or not row.get("received_date")):
					frappe.throw(_("{0}: Received By and Received Date cannot be cleared on a claimed line.").format(what))

		# Keep "Original Amount (before edit)" working for every amount change
		if prev is not None and flt(prev.get("amount")) != flt(row.get("amount")) and not row.get("amount_edited"):
			row.original_amount = flt(prev.get("amount"))
			row.amount_edited = 1

		# A payable with reimbursements fixes the line it came from
		if prev is not None and prev.get("payable"):
			_guard_reimbursed(prev.payable, _changed(prev, row, PAYABLE_LOCKED), what)

		if prev is not None and _changed(prev, row) and act.get("action") != "Claim":
			warnings += period_warnings(doc)

	for name, (field, row) in old.items():
		if not any(r.name == name for _f, _l, r in fin.iter_lines(doc)):
			what = _row_desc(field, row)
			if fin.state(row) == fin.CLAIMED and not doc.flags.allow_delete_claimed:
				frappe.throw(_("{0} is claimed and cannot be deleted. Reverse the claim first.").format(what))
			if row.get("payable"):
				_guard_reimbursed(row.payable, {"deleted": [1, 0]}, what)
			warnings += period_warnings(doc)

	if missing_dept:
		frappe.throw(
			_("Department is required on every line. Missing on:") + "<br>" + "<br>".join(missing_dept[:20])
			+ ("<br>…" if len(missing_dept) > 20 else ""),
			title=_("Department required"),
		)

	doc.flags.audit_warnings = sorted(set(warnings))
	if doc.flags.audit_warnings and not doc.flags.quiet_warnings:
		for w in doc.flags.audit_warnings:
			frappe.msgprint(w, indicator="orange", alert=True)


def _guard_reimbursed(payable, changed, what):
	if not changed:
		return
	paid = flt(frappe.db.get_value("Creditor Payable", payable, "paid_amount"))
	if paid > 0:
		reimbs = frappe.get_all(
			"Creditor Reimbursement Allocation",
			filters={"payable": payable, "docstatus": 1}, pluck="parent",
		)
		frappe.throw(_(
			"{0} was paid by a creditor and ₱{1:,.2f} of its payable {2} has already been reimbursed ({3}). "
			"Cancel the reimbursement first, then correct the line."
		).format(what, paid, payable, ", ".join(sorted(set(reimbs)))), title=_("Reimbursed payable"))


def period_warnings(doc):
	"""Name the earlier report periods a change to this month falls in."""
	key = _month_key(doc)
	if not key:
		return []
	y, m = key
	today = getdate(nowdate())
	out = []
	if (y, m) < (today.year, today.month):
		out.append(_("This changes {0} {1}, a month that has already closed. Reports already shared for it will differ.").format(doc.month_recorded, y))
	for c in frappe.get_all("Fund Summary Comment", fields=["from_date", "to_date"], distinct=True):
		if fin.ym_in_range(y, m, c.from_date, c.to_date):
			out.append(_("This changes {0} {1}, inside the saved Fund Summary period {2}.").format(
				doc.month_recorded, y, fin.period_label(c.from_date, c.to_date)))
	return out


# ---------------------------------------------------------------- log

def record(doc):
	"""Write audit entries for every line change of this save (on_update)."""
	if doc.flags.skip_audit:
		return
	before = doc.get_doc_before_save()
	old = {row.name: (field, row) for field, _l, row in fin.iter_lines(before)} if before else {}
	seen = set()
	for field, label, row in fin.iter_lines(doc):
		seen.add(row.name)
		reason = _reason(doc, row.name)
		if row.name not in old:
			log(doc, field, row, "Line Added", {f: [None, _norm(f, row.get(f))] for f in TRACKED if row.get(f) not in (None, "", 0)}, reason)
			if fin.state(row) == fin.CLAIMED:
				log(doc, field, row, "Claim", {}, reason)
			continue
		prev = old[row.name][1]
		changes = _changed(prev, row)
		changes.pop("original_amount", None)
		if not changes:
			continue
		st, pst = fin.state(row), fin.state(prev)
		groups = []
		if st != pst:
			action = {
				(fin.UNCLAIMED, fin.CLAIMED): "Claim", (fin.CLAIMED, fin.UNCLAIMED): "Reverse Claim",
			}.get((pst, st)) or ("Void" if st == fin.VOIDED else "Unvoid")
			take = STATUS_FIELDS + (("source", "remarks") if action == "Claim" else ())
			if action == "Claim" and fin.paid_by_creditor(row):
				take += CREDITOR_FIELDS
			groups.append((action, take))
		elif pst == fin.CLAIMED and any(f in changes for f in CLAIM_FIELDS):
			groups.append(("Edit Claim", CLAIM_FIELDS + ("remarks",)))
		groups += [
			("Amount Edit", ("amount",)),
			("Fund Change" if "source" in changes and fin.fund_for_source(changes["source"][0]) != fin.fund_for_source(changes["source"][1]) else "Line Edit", ("source",)),
			("Purpose Change", ("purpose",)),
			("Department Change", ("department",)),
			("Paid By Change", CREDITOR_FIELDS),
			("Line Edit", TRACKED),
		]
		for action, fields in groups:
			part = {f: changes.pop(f) for f in list(changes) if f in fields}
			if part:
				if action == "Void" and not reason:
					reason = row.get("void_reason") or ""
				log(doc, field, row, action, part, reason)
	for name, (field, row) in old.items():
		if name not in seen:
			log(doc, field, row, "Line Deleted", {"amount": [flt(row.amount), None]}, _reason(doc, name))


def log(doc, field, row, action, changes, reason="", reference=None):
	"""Append one audit entry. doc is the Disbursement (or None for direct payables)."""
	lines = []
	for f, (a, b) in (changes or {}).items():
		fmt = (lambda v: f"₱{flt(v):,.2f}" if v is not None else "—") if f == "amount" else (lambda v: "—" if v in (None, "") else str(v))
		lines.append(f"{LABELS.get(f, f)}: {fmt(a)} → {fmt(b)}")
	entry = frappe.get_doc({
		"doctype": "Disbursement Audit Log",
		"action": action,
		"disbursement": doc.name if doc else None,
		"year": int(doc.year_recorded) if doc and doc.year_recorded else None,
		"month": doc.month_recorded if doc else None,
		"section": fin.SECTION_LABEL.get(field, field) if field else None,
		"row_name": row.get("name") if row else None,
		"line_label": (fin.line_label(row) or "")[:140] if row else None,
		"amount": flt(row.get("amount")) if row else None,
		"changes": frappe.as_json(changes or {}),
		"summary": "\n".join(lines) or action,
		"reason": (reason or "").strip() or None,
		"reference_doctype": reference[0] if reference else None,
		"reference_name": reference[1] if reference else None,
	})
	entry.insert(ignore_permissions=True)
	return entry.name


def history(disbursement=None, row_name=None, limit=500):
	"""Audit entries for a document or one of its lines, newest first."""
	filters = {}
	if disbursement:
		filters["disbursement"] = disbursement
	if row_name:
		filters["row_name"] = row_name
	return frappe.get_all(
		"Disbursement Audit Log", filters=filters,
		fields=["name", "timestamp", "user", "user_name", "action", "disbursement", "month", "year", "section",
				"row_name", "line_label", "amount", "summary", "changes", "reason", "reference_doctype", "reference_name"],
		order_by="timestamp desc, creation desc", limit_page_length=limit,
	)
