# Copyright (c) 2025, Jeomar Bayoguina and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

class WhiteGift(Document):
    def validate(self):
        self.calculate_total()
        self.calculate_tally_total()
        self.validate_difference()

    def calculate_total(self):
        total = 0
        for row in self.get("white_gift_entry"):
            total += flt(row.amount)
        self.total = total

    def calculate_tally_total(self):
        tally_total = 0
        for row in self.get("collection_tally"):
            row.total = flt(row.denomination) * flt(row.quantity)
            tally_total += row.total
        self.tally_total = tally_total

    def validate_difference(self):
        self.difference = self.tally_total - self.total
        if self.difference != 0:
            msg = _("Tally Total ({0}) must be equal to White Gift Entry Total ({1}). Difference: {2}").format(
                self.tally_total, self.total, self.difference
            )
            #frappe.throw(msg)
            # User requirement: "validation should be tally_total == white_gift_entry.total"
            # I will enforce it.
            frappe.throw(msg)
