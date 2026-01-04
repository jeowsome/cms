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

    def on_submit(self):
        self.make_journal_entry()

    def make_journal_entry(self):
        settings = frappe.get_single("Church Management Settings")
        if not settings.default_income_account or not settings.white_gift_cash_account:
            return

        je = frappe.new_doc("Journal Entry")
        je.posting_date = self.year_recorded # Using year_recorded as posting date
        je.voucher_type = "Journal Entry"
        je.company = frappe.db.get_single_value("Global Defaults", "default_company")
        
        accounts = []
        
        # Calculate Splits
        cash_total = 0
        cashless_total = 0
        
        for row in self.get("white_gift_entry"):
            if row.mode == "Cashless":
                cashless_total += flt(row.amount)
            else:
                cash_total += flt(row.amount)

        # Debit White Gift Cash
        if cash_total > 0:
            accounts.append({
                "account": settings.white_gift_cash_account,
                "debit_in_account_currency": cash_total,
                "cost_center": settings.default_cost_center
            })

        # Debit White Gift Cashless
        if cashless_total > 0:
            if not settings.white_gift_cashless_account:
                frappe.throw(_("White Gift Cashless Account is not set in Church Management Settings."))
                
            accounts.append({
                "account": settings.white_gift_cashless_account,
                "debit_in_account_currency": cashless_total,
                "cost_center": settings.default_cost_center
            })

        # Credit White Gift Income Default
        credit_acc = settings.white_gift_income_account or settings.default_income_account
        
        accounts.append({
            "account": credit_acc,
            "credit_in_account_currency": self.total,
            "cost_center": settings.default_cost_center
        })
        
        je.set("accounts", accounts)
        je.save()
        je.submit()
        self.db_set("journal_entry", je.name)
        frappe.msgprint(frappe._("Journal Entry {0} created.").format(je.name))
