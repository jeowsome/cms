# Copyright (c) 2026, Jeomar Bayoguina and contributors
# For license information, please see license.txt
"""A recurring department activity in a GPOA (e.g. YP fellowship every 2nd &
4th Sunday). The annual budget is the per-occurrence budget times the number
of dates the rule produces in the GPOA's year."""
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from church_management.church_management import church_calendar as cal


class GPOARegularActivity(Document):
	def validate(self):
		if self.all_day:
			self.start_time = None
			self.end_time = None
		elif bool(self.start_time) != bool(self.end_time):
			frappe.throw(_("Set both a start and an end time, or neither."))
		year = frappe.db.get_value("GPOA", self.gpoa, "year")
		self.occurrences = len(cal.occurrence_dates(self.as_dict(), year)) if year else 0
		self.annual_budget = flt(self.budget_per_occurrence) * (self.occurrences or 0)
