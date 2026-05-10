"""Idempotently create the Music Team Member + Music Team Leader roles."""
import frappe


ROLES = [
	{"role_name": "Music Team Member", "desk_access": 0},
	{"role_name": "Music Team Leader", "desk_access": 0},
]


def execute():
	for r in ROLES:
		if not frappe.db.exists("Role", r["role_name"]):
			doc = frappe.get_doc({
				"doctype": "Role",
				"role_name": r["role_name"],
				"desk_access": r["desk_access"],
			})
			doc.insert(ignore_permissions=True)
	frappe.db.commit()
