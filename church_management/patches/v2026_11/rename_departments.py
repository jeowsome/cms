"""Rename departments to the names the finance team uses.

Missionary -> Mission, Pasig Social Media -> Pasig SocMed. rename_doc
updates every link (worker ministry, donations, disbursement lines,
templates). Safe to run twice: skips when the old name is gone.
"""
import frappe

RENAMES = {"Missionary": "Mission", "Pasig Social Media": "Pasig SocMed"}


def execute():
	for old, new in RENAMES.items():
		if not frappe.db.exists("Department Name", old):
			continue
		if frappe.db.exists("Department Name", new):
			# Both exist: fold the old one into the new name
			frappe.rename_doc("Department Name", old, new, merge=True, force=True, show_alert=False)
		else:
			frappe.rename_doc("Department Name", old, new, force=True, show_alert=False)
		print(f"Department {old} renamed to {new}")
