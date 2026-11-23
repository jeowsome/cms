# Copyright (c) 2026, Jeomar Bayoguina and contributors
# For license information, please see license.txt
import frappe
from frappe import _
from frappe.model.document import Document


class GPOAGoal(Document):
	def validate(self):
		dup = frappe.db.exists(
			"GPOA Goal",
			{"gpoa": self.gpoa, "department": self.department, "metric": self.metric, "name": ["!=", self.name]},
		)
		if dup:
			frappe.throw(_("{0} already has a {1} goal in {2}.").format(self.department, self.metric, self.gpoa))
