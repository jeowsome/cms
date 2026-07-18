# Copyright (c) 2025, Jeomar Bayoguina and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt

class Donation(Document):
    def before_save(self):
        """
        Calculates the total amounts from the donation_items child table
        and sets the values in the parent document's fields.
        """
        mission = self.get_mission_purposes()
        self.mark_mission_items_pending(mission)
        self.calculate_donation_totals(mission)

    def get_mission_purposes(self):
        """Purposes used on this doc that are flagged as mission funds."""
        purposes = {i.purpose for i in self.get("donated_amounts") if i.purpose}
        if not purposes:
            return set()
        return set(
            frappe.get_all(
                "Donation Purpose",
                filters={"name": ["in", list(purposes)], "is_mission": 1},
                pluck="name",
            )
        )

    def mark_mission_items_pending(self, mission):
        """Items whose purpose is a mission fund need admin approval before
        they post to the ledger. Approved items are never touched here."""
        for item in self.get("donated_amounts"):
            if item.approval_status == "Approved":
                continue
            item.approval_status = "Pending" if item.purpose in mission else ""

    def calculate_donation_totals(self, mission):
        """
        Iterates through the 'donation_items' child table to sum up amounts
        based on the donation_type.

        Sets the following fields on the document:
        - total_donated_cash_amount
        - total_donated_cashless_amount
        - total_donated_amount
        - total_mission_amount (mission-purpose donations — held for the
          Mission funds, excluded from the department's spendable total)
        - total_expenses
        """
        # Initialize variables to store the totals
        total_cash = 0
        total_cashless = 0
        total_mission = 0

        for item in self.get("donated_amounts"):
            amount = item.get("amount_donated", 0) or 0
            # Check the donation_type and add the amount to the corresponding total
            if item.donation_type == "Cash":
                total_cash += amount
            elif item.donation_type == "GCash":
                total_cashless += amount
            if item.purpose in mission or item.approval_status in ("Pending", "Approved"):
                total_mission += amount

        # Set the calculated values to the fields in the main "Donation" doctype
        self.total_donated_cash_amount = flt(total_cash)
        self.total_donated_cashless_amount = flt(total_cashless)
        self.total_donated_amount = flt(total_cash + total_cashless)
        self.total_mission_amount = flt(total_mission)
        self.total_expenses = flt(
            sum(e.get("amount_spent", 0) or 0 for e in self.get("expenses"))
        )
