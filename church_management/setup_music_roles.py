"""Idempotently create the church-management roles used by the SPA.

Naming kept (`setup_music_roles`) for backwards-compat with hooks.py and other
patches, but this now seeds the full role catalogue used to gate the SPA:

  - Finance Team        — Disbursement CRUD
  - Music Team Leader   — full music CRUD + registrations queue
  - Music Team Member   — slim profile/schedule view
  - Worship Leader      — songs, practice time, lineup edit

System Manager / Administrator implicitly bypasses every check.
"""
import frappe


ROLES = [
	{"role_name": "Finance Team", "desk_access": 0},
	{"role_name": "Music Team Member", "desk_access": 0},
	{"role_name": "Music Team Leader", "desk_access": 0},
	{"role_name": "Worship Leader", "desk_access": 0},
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
