import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class FundSummaryComment(Document):
	"""The finance team's notes on one fund for one Fund Summary period."""

	def validate(self):
		if getdate(self.from_date) > getdate(self.to_date):
			frappe.throw(_("From must be on or before To."))
		dup = frappe.db.exists("Fund Summary Comment", {
			"from_date": self.from_date, "to_date": self.to_date, "fund": self.fund, "name": ["!=", self.name],
		})
		if dup:
			frappe.throw(_("There are already comments for {0} in this period.").format(self.fund))
