# Copyright (c) 2025, Jeomar Bayoguina and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
from frappe.utils import flt

class Donation(Document):
    def before_save(self):
        """
        Calculates the total amounts from the donation_items child table
        and sets the values in the parent document's fields.
        """
        self.calculate_donation_totals()

    def calculate_donation_totals(self):
        """
        Iterates through the 'donation_items' child table to sum up amounts
        based on the donation_type.

        Sets the following fields on the document:
        - total_donated_cash_amount
        - total_donated_cashless_amount
        - total_donated_amount
        """
        # Initialize variables to store the totals
        total_cash = 0
        total_cashless = 0

        for item in self.get("donated_amounts"):
            # Check the donation_type and add the amount to the corresponding total
            if item.donation_type == "Cash":
                total_cash += item.get("amount_donated", 0)  # Use .get for safety
            elif item.donation_type == "GCash":
                total_cashless += item.get("amount_donated", 0)

        # Set the calculated values to the fields in the main "Donation" doctype
        self.total_donated_cash_amount = flt(total_cash)
        self.total_donated_cashless_amount = flt(total_cashless)
        self.total_donated_amount = flt(total_cash + total_cashless)