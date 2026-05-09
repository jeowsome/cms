import frappe
from frappe.model.document import Document


class MemberUnavailability(Document):
	def validate(self):
		if self.from_date and self.to_date and self.from_date > self.to_date:
			frappe.throw("From date must be on or before To date.")
		if self.member and not self.member_name:
			first = frappe.db.get_value("Church Member", self.member, "firstname") or ""
			last = frappe.db.get_value("Church Member", self.member, "lastname") or ""
			self.member_name = (first + " " + last).strip() or self.member
