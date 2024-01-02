# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Disbursement(Document):
	def autoname(self):
		self.name = f"{self.get('month_recorded')}-{self.get('year_recorded')}-Week-{self.get('week_recorded')}"

	def validate(self):
		self.total_amount_disbursed = sum([disbursed.disbursed_amount for disbursed in self.get("disbursed")])
		self.total_disbursed = len(self.disbursed)
  
  
	@frappe.whitelist()
	def validate_ymw(self):
		doc = frappe.db.exists("Disbursement", {"month_recorded": self.month_recorded, "year_recorded": self.year_recorded, "week_recorded": self.week_recorded})
		return {
			"exists": doc != self.name
		}
      
  
	@frappe.whitelist()
	def populate_template(self):
		dt = frappe.get_doc("Disbursement Template", self.disbursement_template)
		self.set("disbursed", [{"worker_name": row.disbursed_for, "receiver": row.disbursed_to, "disbursed_amount": row.disbursed_amount, "purpose": row.disbursement_purpose} for row in dt.get("disbursement_receivers")])
