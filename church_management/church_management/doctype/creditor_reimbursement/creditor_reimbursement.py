import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class CreditorReimbursement(Document):
	"""Church money paid back to a creditor, settling one or more payables
	(each in full or in part) from one source account. The statement deducts
	the total from that account on the reimbursement date."""

	def validate(self):
		from church_management.church_management.finance import fund_for_source

		if frappe.db.get_value("Account", self.source_account, "account_type") not in ("Cash", "Bank"):
			frappe.throw(_("Paid From must be a cash or cashless account."))
		self.fund = fund_for_source(self.source_account)
		if not self.allocations:
			frappe.throw(_("Choose at least one payable to settle."))
		seen = set()
		for a in self.allocations:
			p = frappe.db.get_value("Creditor Payable", a.payable,
				["creditor", "docstatus", "fund", "outstanding_amount", "description"], as_dict=True)
			if not p or p.docstatus != 1:
				frappe.throw(_("Row {0}: payable {1} is not open.").format(a.idx, a.payable))
			if a.payable in seen:
				frappe.throw(_("Row {0}: payable {1} is listed twice.").format(a.idx, a.payable))
			seen.add(a.payable)
			if p.creditor != self.creditor:
				frappe.throw(_("Row {0}: payable {1} is owed to {2}, not {3}.").format(a.idx, a.payable, p.creditor, self.creditor))
			if p.fund != self.fund:
				frappe.throw(_(
					"Row {0}: payable {1} is a {2} fund expense, but {3} is a {4} fund account. "
					"Pay it from an account of the same fund."
				).format(a.idx, a.payable, p.fund, self.source_account, self.fund))
			a.description = p.description
			if self.docstatus == 0:
				a.outstanding_amount = flt(p.outstanding_amount)
			if flt(a.amount) <= 0:
				frappe.throw(_("Row {0}: amount must be more than zero.").format(a.idx))
			if flt(a.amount) - flt(p.outstanding_amount) > 0.005 and self.docstatus == 0:
				frappe.throw(_("Row {0}: ₱{1:,.2f} is more than the ₱{2:,.2f} still owed on {3}.").format(
					a.idx, flt(a.amount), flt(p.outstanding_amount), a.payable))
		self.total_amount = sum(flt(a.amount) for a in self.allocations)

	def before_submit(self):
		# Re-check against the latest balance (another reimbursement may have
		# been submitted since this one was saved)
		for a in self.allocations:
			out = flt(frappe.db.get_value("Creditor Payable", a.payable, "outstanding_amount"))
			if flt(a.amount) - out > 0.005:
				frappe.throw(_("Row {0}: only ₱{1:,.2f} is still owed on {2}.").format(a.idx, out, a.payable))

	def on_submit(self):
		self._settle("Reimbursement", +1)

	def on_cancel(self):
		self._settle("Reimbursement Cancelled", -1)

	def _settle(self, action, sign):
		from church_management.church_management import disbursement_audit as audit
		from church_management.church_management.creditors import refresh_payable
		from church_management.church_management import finance as fin

		for a in self.allocations:
			refresh_payable(a.payable)
			p = frappe.db.get_value("Creditor Payable", a.payable,
				["disbursement", "disbursement_row", "section", "description", "amount", "outstanding_amount"], as_dict=True)
			doc = frappe.get_doc("Disbursement", p.disbursement) if p.disbursement else None
			row = frappe._dict(name=p.disbursement_row or a.payable, description=p.description, amount=p.amount)
			field = next((f for f, label in fin.SECTION_LABEL.items() if label == p.section), "direct_payable")
			audit.log(doc, field, row, action, {
				"reimbursed": [None, sign * flt(a.amount)],
				"outstanding": [flt(p.outstanding_amount) + sign * flt(a.amount), flt(p.outstanding_amount)],
				"source": [None, self.source_account],
			}, self.flags.audit_reason or self.remarks or "", ("Creditor Reimbursement", self.name))
