"""Idempotent after_migrate seed for the GPOA planner and church calendar:
the Pastor role, the church's venues and the weekly worship services.
Existing records are never changed, so edits made on the site stay."""
import frappe

VENUES = [
	# (name, on premises)
	("Church", 1),
	("3rd Floor", 1),
	("4th Floor", 1),
	("JBC Cainta", 0),
]

SERVICES = [
	# (name, weekday, start, end, venue)
	("Morning Worship", "Sunday", "09:00:00", "11:30:00", "Church"),
	("Evening Worship", "Sunday", "18:00:00", "19:30:00", "Church"),
]


def execute():
	if not frappe.db.table_exists("Church Venue") or not frappe.db.table_exists("Worship Service"):
		return
	if not frappe.db.exists("Role", "Pastor"):
		frappe.get_doc({"doctype": "Role", "role_name": "Pastor", "desk_access": 0}).insert(ignore_permissions=True)
	for name, on_premises in VENUES:
		if not frappe.db.exists("Church Venue", name):
			frappe.get_doc({"doctype": "Church Venue", "venue_name": name, "on_premises": on_premises}).insert(ignore_permissions=True)
	if not frappe.db.count("Worship Service"):
		for name, weekday, start, end, venue in SERVICES:
			frappe.get_doc({
				"doctype": "Worship Service", "service_name": name, "weekday": weekday,
				"start_time": start, "end_time": end, "venue": venue,
			}).insert(ignore_permissions=True)
	frappe.db.commit()
