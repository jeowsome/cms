# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ChurchWorker(Document):

	def autoname(self):
		self.first_name = self.first_name.title()
		self.last_name = self.last_name.title() if self.last_name else ""
		self.full_name = f"{self.first_name} {self.last_name or ''}".title()
		self.name = self.full_name
