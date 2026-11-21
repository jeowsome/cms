import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class CreditorPayable(Document):
	"""What the church owes a creditor for one expense they paid on its behalf.

	Payables recorded from a disbursement line are created, updated and
	cancelled by that line (change the line, not the payable). Direct payables
	— for expenses never on a monthly document — are entered here and count
	as an expense themselves."""

	def validate(self):
		if flt(self.amount) <= 0:
			frappe.throw(_("Amount must be more than zero."))
		if not self.source_type:
			self.source_type = "Direct"
		if self.source_type == "Disbursement Line" and not self.flags.from_line and not self.is_new():
			frappe.throw(_("This payable comes from disbursement line {0}. Correct the line instead.").format(self.disbursement))
		if self.source_type == "Direct":
			self.disbursement = self.disbursement_row = self.section = None
		self.outstanding_amount = flt(self.amount) - flt(self.paid_amount)

	def before_update_after_submit(self):
		self.validate()
		if flt(self.amount) < flt(self.paid_amount):
			frappe.throw(_("Amount cannot be less than the ₱{0:,.2f} already reimbursed.").format(flt(self.paid_amount)))

	def on_update_after_submit(self):
		from church_management.church_management.creditors import refresh_payable
		refresh_payable(self.name)
		if self.source_type == "Direct":
			self._log("Payable Updated", {"amount": [None, flt(self.amount)]})

	def on_submit(self):
		from church_management.church_management.creditors import refresh_payable
		refresh_payable(self.name)
		if self.source_type == "Direct":
			self._log("Payable Created", {"amount": [None, flt(self.amount)]})

	def before_cancel(self):
		if self.source_type == "Disbursement Line" and not self.flags.from_line:
			frappe.throw(_("This payable comes from disbursement line {0}. Change the line instead.").format(self.disbursement))
		if flt(self.paid_amount) > 0:
			frappe.throw(_("₱{0:,.2f} of this payable has been reimbursed. Cancel those reimbursements first.").format(flt(self.paid_amount)))

	def on_cancel(self):
		from church_management.church_management.creditors import refresh_payable
		refresh_payable(self.name)
		if self.source_type == "Direct":
			self._log("Payable Cancelled", {"amount": [flt(self.amount), None]})

	def _log(self, action, changes):
		from church_management.church_management import disbursement_audit as audit
		row = frappe._dict(name=self.name, description=self.description, amount=self.amount)
		audit.log(None, "direct_payable", row, action, changes, self.flags.audit_reason or "",
			("Creditor Payable", self.name))
