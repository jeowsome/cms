# Copyright (c) 2026, Jeomar Bayoguina and contributors
# For license information, please see license.txt
"""A weekly worship service. Church activities may not overlap one unless
they are part of it, or replace it with the pastor's approval."""
import frappe
from frappe import _
from frappe.model.document import Document

from church_management.church_management import church_calendar as cal


class WorshipService(Document):
	def validate(self):
		if cal.to_time(self.end_time) <= cal.to_time(self.start_time):
			frappe.throw(_("The end time must be after the start time."))
