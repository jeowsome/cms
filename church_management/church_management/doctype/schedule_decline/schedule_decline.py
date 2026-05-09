import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class ScheduleDecline(Document):
	def before_insert(self):
		if not self.declined_at:
			self.declined_at = now_datetime()
		if self.member and not self.member_name:
			first = frappe.db.get_value("Church Member", self.member, "firstname") or ""
			last = frappe.db.get_value("Church Member", self.member, "lastname") or ""
			self.member_name = (first + " " + last).strip() or self.member
