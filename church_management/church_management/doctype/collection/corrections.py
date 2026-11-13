"""Corrections to a submitted Collection, with an audit trail.

A submitted Collection is locked and has a Journal Entry posted. To fix a
mistake it is *reopened*: the Journal Entry is cancelled (reversing its
ledger postings) and the Collection goes back to draft so it can be edited
the normal way. Submitting it again posts a fresh Journal Entry.

Every reopen is recorded as a Version document on the Collection — Frappe's
own change log, which Finance users cannot edit or delete. The record keeps
who reopened it, when and why, a snapshot of the collection as it was, and —
once resubmitted — exactly what changed and the old and new Journal Entries.
"""
import json

import frappe
from frappe import _
from frappe.utils import flt, get_fullname, now

ENTRY_TABLES = {
	"tithes_collection": ("Tithes Collection", "Tithes"),
	"offering_collection": ("Offering Collection", "Offering"),
	"mission_collection": ("Mission Collection", "Mission"),
}
TALLY_TABLE = ("collection_tally", "Collection Tally")
ROW_FIELDS = {"amount": "Amount", "account_type": "Paid by", "number": "Envelope"}
HEADER_FIELDS = {
	"date": ("Service", "Date and time"),
	"attendees": ("Service", "Attendees"),
	"benevolence_collection": ("Others", "Benevolence (cash)"),
	"benevolence_collection_cls": ("Others", "Benevolence (cashless)"),
	"loose_collection": ("Others", "Loose (cash)"),
	"loose_collection_cls": ("Others", "Loose (cashless)"),
	"sunday_school_collection": ("Others", "Sunday School"),
}
TOTAL_FIELDS = ("grand_total", "grand_total_cls", "all_grand_total")
MIN_REASON_LENGTH = 5


def _snapshot(doc):
	"""The parts of a collection a correction can change."""
	return {
		"fields": {f: (str(doc.get(f)) if f == "date" and doc.get(f) else doc.get(f)) for f in HEADER_FIELDS},
		"totals": {f: flt(doc.get(f)) for f in TOTAL_FIELDS},
		"rows": {
			table: [
				{
					"name": r.name,
					"number": r.number or "",
					"who": " ".join(p for p in (r.first_name, r.last_name) if p),
					"amount": flt(r.amount),
					"account_type": r.account_type or "Cash",
				}
				for r in doc.get(table)
			]
			for table in ENTRY_TABLES
		},
		"tally": {
			str(r.denum_name): {"quantity": r.quantity or 0, "quantity_coins": r.quantity_coins or 0}
			for r in doc.get(TALLY_TABLE[0])
		},
	}


def _diff(before, after):
	"""Human-readable list of what differs between two snapshots."""
	changes = []
	for table, (_dt, section) in ENTRY_TABLES.items():
		old = {r["name"]: r for r in before["rows"].get(table, [])}
		new = {r["name"]: r for r in after["rows"].get(table, [])}
		for name, r in old.items():
			if name not in new:
				changes.append({"kind": "removed", "section": section, "who": r["who"], "envelope": r["number"],
					"old": r["amount"], "account_type": r["account_type"]})
		for name, r in new.items():
			if name not in old:
				if not r["number"] and not r["amount"]:
					continue
				changes.append({"kind": "added", "section": section, "who": r["who"], "envelope": r["number"],
					"new": r["amount"], "account_type": r["account_type"]})
				continue
			for field, label in ROW_FIELDS.items():
				a, b = old[name][field], r[field]
				if (flt(a) != flt(b)) if field == "amount" else (a != b):
					changes.append({"kind": "changed", "section": section, "who": r["who"] or old[name]["who"],
						"envelope": r["number"], "field": label, "old": a, "new": b})
	for field, (section, label) in HEADER_FIELDS.items():
		a, b = before["fields"].get(field), after["fields"].get(field)
		same = (a == b) if field == "date" else (flt(a) == flt(b))
		if not same:
			changes.append({"kind": "changed", "section": section, "field": label, "old": a, "new": b})
	for denum in sorted(set(before["tally"]) | set(after["tally"]), key=lambda d: -flt(d)):
		a = before["tally"].get(denum, {"quantity": 0, "quantity_coins": 0})
		b = after["tally"].get(denum, {"quantity": 0, "quantity_coins": 0})
		for key, label in (("quantity", "pieces"), ("quantity_coins", "coins")):
			if (a[key] or 0) != (b[key] or 0):
				changes.append({"kind": "changed", "section": "Cash tally", "field": f"₱{denum} {label}",
					"old": a[key] or 0, "new": b[key] or 0, "count": True})
	return changes


def _versions(name):
	"""(Version name, parsed correction dict) for every correction, newest first."""
	out = []
	for v in frappe.get_all(
		"Version",
		filters={"ref_doctype": "Collection", "docname": name, "data": ["like", '%"correction"%']},
		fields=["name", "data"],
		order_by="creation desc",
	):
		try:
			data = json.loads(v.data)
		except ValueError:
			continue
		if isinstance(data.get("correction"), dict):
			out.append((v.name, data))
	return out


def open_correction(name):
	"""The correction still in progress for this collection, if any."""
	for version, data in _versions(name):
		if data["correction"].get("status") == "open":
			return version, data
	return None


def reopen(name, reason):
	"""Reopen a submitted collection for correction. Returns the reloaded doc."""
	reason = (reason or "").strip()
	if len(reason) < MIN_REASON_LENGTH:
		frappe.throw(_("Please say why this collection is being corrected."))

	doc = frappe.get_doc("Collection", name, for_update=True)
	if doc.docstatus != 1:
		frappe.throw(_("Only a submitted collection can be reopened for correction."))
	if open_correction(name):
		frappe.throw(_("Collection {0} is already being corrected.").format(name))

	before = _snapshot(doc)
	old_je = doc.journal_entry

	# Back to draft first, so the Journal Entry is no longer linked from a
	# submitted document and can be cancelled.
	frappe.db.set_value("Collection", name, {"docstatus": 0, "journal_entry": None})
	for _field, child_doctype in [*((t, dt) for t, (dt, _l) in ENTRY_TABLES.items()), TALLY_TABLE]:
		frappe.db.sql(
			f"update `tab{child_doctype}` set docstatus = 0 where parent = %s and parenttype = 'Collection'",
			name,
		)

	if old_je and frappe.db.get_value("Journal Entry", old_je, "docstatus") == 1:
		je = frappe.get_doc("Journal Entry", old_je)
		# Same reasoning as on submit: Finance Team has no ERPNext Accounts role;
		# reversing the entry is a side effect of an authorised correction.
		je.flags.ignore_permissions = True
		je.cancel()

	frappe.get_doc({
		"doctype": "Version",
		"ref_doctype": "Collection",
		"docname": name,
		"data": json.dumps({
			"changed": [], "added": [], "removed": [], "row_changed": [],
			"correction": {
				"status": "open",
				"reason": reason,
				"opened_by": frappe.session.user,
				"opened_on": now(),
				"old_journal_entry": old_je,
				"before": before,
			},
		}),
	}).insert(ignore_permissions=True)

	return frappe.get_doc("Collection", name)


def close(doc):
	"""Called when a collection is submitted: finish its open correction, if any."""
	found = open_correction(doc.name)
	if not found:
		return
	version, data = found
	c = data["correction"]
	after = _snapshot(doc)
	c.update({
		"status": "done",
		"closed_by": frappe.session.user,
		"closed_on": now(),
		"new_journal_entry": doc.journal_entry,
		"changes": _diff(c["before"], after),
		"totals_before": c["before"]["totals"],
		"totals_after": after["totals"],
	})
	# Shown by the desk timeline as an ordinary field change
	old_total, new_total = c["totals_before"]["all_grand_total"], c["totals_after"]["all_grand_total"]
	data["changed"] = [["all_grand_total", old_total, new_total]] if old_total != new_total else []
	frappe.db.set_value("Version", version, "data", json.dumps(data), update_modified=False)


def history(name):
	"""Audit trail for the SPA, newest first (without the bulky snapshots)."""
	out = []
	for version, data in _versions(name):
		c = data["correction"]
		out.append({
			"id": version,
			"status": c.get("status"),
			"reason": c.get("reason"),
			"opened_by": get_fullname(c.get("opened_by")) or c.get("opened_by"),
			"opened_on": c.get("opened_on"),
			"closed_by": get_fullname(c.get("closed_by")) if c.get("closed_by") else None,
			"closed_on": c.get("closed_on"),
			"old_journal_entry": c.get("old_journal_entry"),
			"new_journal_entry": c.get("new_journal_entry"),
			"changes": c.get("changes") or [],
			"totals_before": c.get("totals_before") or (c.get("before") or {}).get("totals"),
			"totals_after": c.get("totals_after"),
		})
	return out
