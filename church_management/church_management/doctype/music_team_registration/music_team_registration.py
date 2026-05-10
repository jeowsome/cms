import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class MusicTeamRegistration(Document):
	def before_insert(self):
		if not self.submitted_on:
			self.submitted_on = now_datetime()
		if not self.status:
			self.status = "Pending"

	def soft_match(self):
		"""Try to find a Church Member by envelope_number, then by email."""
		if self.envelope_number:
			match = frappe.db.get_value(
				"Church Member", {"envelope_number": self.envelope_number}, "name"
			)
			if match:
				return match
		if self.email:
			match = frappe.db.get_value(
				"Church Member", {"email_address": self.email}, "name"
			)
			if match:
				return match
		return None
