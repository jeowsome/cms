import frappe
from frappe.model.document import Document


class Creditor(Document):
	"""A party that can pay church expenses on the church's behalf
	(e.g. Christian Bible Heritage Learning Center)."""

	def validate(self):
		self.creditor_name = (self.creditor_name or "").strip()
