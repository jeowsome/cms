"""One-time 2026 corrections agreed with the finance team (brief A5).
Each goes through the logged path and checks the current state first, so
running twice changes nothing.

1. Collection 2026-10-18 MORNING: ₱314 recorded as Benevolence Cash belongs
   to Sunday School Cash — reopened for correction (Journal Entry
   ACC-JV-2026-00082 is cancelled), corrected and resubmitted, which posts a
   new Journal Entry. The correction history keeps both.
2. May-2026: add the missing benevolence line (claimed; details in
   people_2026.json, kept off git).
3. August-2026 "Benevolence Monthly" ₱1,000: Edit claim from General Cash to
   Benevolence Cash.
4. Void the eleven unclaimed lines marked Remove (₱20,590).
"""
import frappe
from frappe.utils import flt

from church_management.patches.v2026_11.backfill_2026_lines import load, load_people

COLLECTION = "2026-10-18 MORNING"
MOVE = 314.0
REASON_COLLECTION = "₱314 was recorded as Benevolence Cash; it is Sunday School Cash (finance team, Nov 2026)"
REASON_AUGUST = "Benevolence Monthly is a Benevolence fund expense; it was charged to General Cash by mistake"
VOID_REASON = "Discontinued — will not be paid"


def execute():
	data = load()
	fix_collection()
	add_missing_may_line(load_people())
	move_august(data["august_benevolence"])
	void_lines(data["voids"])


def fix_collection():
	from church_management.church_management.doctype.collection import corrections

	if not frappe.db.exists("Collection", COLLECTION):
		return
	if any(REASON_COLLECTION == h.get("reason") for h in corrections.history(COLLECTION)):
		return  # already corrected
	doc = frappe.get_doc("Collection", COLLECTION)
	if doc.docstatus != 1 or flt(doc.benevolence_collection) < MOVE:
		print(f"  skip collection {COLLECTION}: not in the expected state")
		return
	doc = corrections.reopen(COLLECTION, REASON_COLLECTION)
	doc.benevolence_collection = flt(doc.benevolence_collection) - MOVE
	doc.sunday_school_collection = flt(doc.sunday_school_collection) + MOVE
	doc.flags.ignore_permissions = True
	doc.save()
	doc.submit()
	print(f"  {COLLECTION}: corrected, new Journal Entry {doc.journal_entry}")


def add_missing_may_line(people):
	if people is None:
		print("  people_2026.json not found: missing May line skipped")
		return
	m = people["may_missing_line"]
	if not frappe.db.exists("Disbursement", m["disbursement"]):
		return
	doc = frappe.get_doc("Disbursement", m["disbursement"])
	if any((r.description or "").strip() == m["description"] for r in doc.monthly_expense_items):
		return
	doc.append("monthly_expense_items", {
		"description": m["description"], "amount": m["amount"], "source": m["source"],
		"purpose": m["purpose"], "department": m["department"], "status": "Claimed",
		"received_by": m["received_by"], "received_date": m["received_date"], "paid_by": "Church funds", "is_planned": 0,
	})
	doc.flags.audit_reason = m["reason"]
	doc.flags.quiet_warnings = True
	doc.save(ignore_permissions=True)
	print(f"  {m['disbursement']}: missing benevolence line added")


def move_august(a):
	if not frappe.db.exists("Disbursement", a["disbursement"]):
		return
	doc = frappe.get_doc("Disbursement", a["disbursement"])
	row = next((r for r in doc.monthly_expense_items if r.name == a["row"]), None)
	if not row or row.source == a["new_source"]:
		return
	if row.source != a["old_source"] or flt(row.amount) != flt(a["amount"]):
		print("  skip August Benevolence Monthly: not in the expected state")
		return
	row.source = a["new_source"]
	doc.flags.line_actions = {row.name: {"action": "Edit Claim", "reason": REASON_AUGUST}}
	doc.flags.quiet_warnings = True
	doc.save(ignore_permissions=True)
	print("  August-2026 Benevolence Monthly moved to Benevolence Cash")


def void_lines(voids):
	from church_management.church_management import finance as fin

	by_doc = {}
	for v in voids:
		by_doc.setdefault(v["disbursement"], []).append(v)
	total = 0.0
	for name, items in by_doc.items():
		if not frappe.db.exists("Disbursement", name):
			continue
		doc = frappe.get_doc("Disbursement", name)
		rows = {r.name: r for _f, _l, r in fin.iter_lines(doc)}
		actions = {}
		for v in items:
			row = rows.get(v["row"])
			if not row or fin.state(row) != fin.UNCLAIMED or flt(row.amount) != flt(v["amount"]):
				if row is None or fin.state(row) != fin.VOIDED:
					print(f"  skip void {name} {v['description']}: not in the expected state")
				continue
			row.status = fin.VOIDED
			row.void_reason = VOID_REASON
			actions[row.name] = {"action": "Void", "reason": VOID_REASON}
			total += flt(row.amount)
		if actions:
			doc.flags.line_actions = actions
			doc.flags.quiet_warnings = True
			doc.save(ignore_permissions=True)
	if total:
		print(f"  voided ₱{total:,.2f}")
