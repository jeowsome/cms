# Copyright (c) 2026, Jeomar Bayoguina and contributors
# For license information, please see license.txt
"""General Planning of Activities for one year. Goals, regular activities,
budget requests and calendar activities link to it by `gpoa`."""
import frappe
from frappe import _
from frappe.model.document import Document

LINKED = ("GPOA Goal", "GPOA Regular Activity", "GPOA Budget Request")


class GPOA(Document):
	def validate(self):
		if not 2000 <= int(self.year or 0) <= 2100:
			frappe.throw(_("Enter a valid year."))

	def on_trash(self):
		if frappe.db.exists("Church Activity", {"gpoa": self.name}):
			frappe.throw(_("Delete or move this GPOA's calendar activities first."))
		for dt in LINKED:
			frappe.db.delete(dt, {"gpoa": self.name})
