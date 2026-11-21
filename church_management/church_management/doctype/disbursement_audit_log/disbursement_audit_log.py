import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_fullname, now_datetime


class DisbursementAuditLog(Document):
	"""Append-only: entries are written by the server and can never be edited
	or deleted through the app, the desk or the API — Administrator included."""

	def before_insert(self):
		self.timestamp = now_datetime()
		self.user = frappe.session.user
		self.user_name = get_fullname(self.user) or self.user

	def validate(self):
		if not self.is_new():
			frappe.throw(_("Audit log entries cannot be changed."), frappe.PermissionError)

	def on_trash(self):
		frappe.throw(_("Audit log entries cannot be deleted."), frappe.PermissionError)

	def before_rename(self, *args, **kwargs):
		frappe.throw(_("Audit log entries cannot be renamed."), frappe.PermissionError)
