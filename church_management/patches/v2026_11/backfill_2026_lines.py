"""Department and purpose backfill for 2026, from the finance team's edited
workbook (finance_2026_corrections.json, built from it line by line).

Each change goes through a normal Disbursement save, so it is written to the
Disbursement Audit Log with its before/after value and this reason. A line
is changed only while it still holds the value the workbook replaced, so
running twice changes nothing and a value someone fixed by hand since is
left alone (and reported).
"""
import json
import os

import frappe

REASON = "2026 backfill: department/purpose as set by the finance team in the edited statement workbook (20 Nov 2026)"


def load():
	with open(os.path.join(os.path.dirname(__file__), "finance_2026_corrections.json")) as f:
		return json.load(f)


def load_people():
	"""Names the patches need (workers, payees, the missing May line). Kept in
	people_2026.json on the server only, never in git, because the repository
	is public. Returns None when the file is not there; the steps that need it
	are then skipped with a message."""
	path = os.path.join(os.path.dirname(__file__), "people_2026.json")
	if not os.path.exists(path):
		return None
	with open(path) as f:
		return json.load(f)


def execute():
	from church_management.church_management import finance as fin

	data = load()
	by_doc = {}
	for c in data["changes"]:
		by_doc.setdefault(c["disbursement"], []).append(c)
	applied = skipped = 0
	for name, changes in by_doc.items():
		if not frappe.db.exists("Disbursement", name):
			continue
		doc = frappe.get_doc("Disbursement", name)
		rows = {r.name: r for _f, _l, r in fin.iter_lines(doc)}
		dirty = False
		for c in changes:
			row = rows.get(c["row"])
			if not row:
				print(f"  skip (line gone): {name} {c['line']}")
				skipped += 1
				continue
			cur = row.get(c["field"]) or None
			if cur == c["new"]:
				continue
			if cur != c["old"]:
				print(f"  skip (changed since): {name} {c['line']} {c['field']} is {cur!r}, expected {c['old']!r}")
				skipped += 1
				continue
			row.set(c["field"], c["new"])
			dirty = True
			applied += 1
		if dirty:
			doc.flags.audit_reason = REASON
			doc.flags.quiet_warnings = True
			doc.save(ignore_permissions=True)
	print(f"Backfill: {applied} applied, {skipped} skipped")
