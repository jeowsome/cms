"""Tests for the finance upgrades: line states (Voided), claim guards and
corrections, the append-only audit log, creditor payables and
reimbursements, and the Fund Summary.

Everything is built in the year 2099 so it never mixes with real data, and
every test is rolled back.

Run: bench --site <test site> run-tests --module church_management.church_management.tests.test_finance_upgrades
"""
import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt

from church_management.api import disbursement as api
from church_management.api import finance as fapi
from church_management.church_management import creditors as cred
from church_management.church_management import disbursement_audit as audit
from church_management.church_management import finance as fin
from church_management.church_management import fund_summary

YEAR = 2099
MONTH = "March"
DOC = f"{MONTH}-{YEAR}"
FROM, TO = f"{YEAR}-03-01", f"{YEAR}-03-31"
GEN_CASH = "General Cash - JBC"
BEN_CASH = "Benevolence Cash - JBC"
WG_CASH = "White Gift Cash - JBC"
CREDITOR = "_Test School Creditor"
WORKER = "_Test Finance Worker"
REASON = "Test correction reason"


def _company():
	return frappe.db.get_value("Company", {}, "name")


class TestFinanceUpgrades(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		for d in ("Pasig General", "Cainta General", "Mission"):
			if not frappe.db.exists("Department Name", d):
				frappe.get_doc({"doctype": "Department Name", "department_name": d}).insert()
		for p in ("Allowance", "Benevolence", "Rent", "Mission Support", "White Gift Project", "Maintenance"):
			if not frappe.db.exists("Disbursement Purpose", p):
				frappe.get_doc({"doctype": "Disbursement Purpose", "purpose": p, "active": 1}).insert()
		if not frappe.db.exists("Church Worker", WORKER):
			w = frappe.get_doc({"doctype": "Church Worker", "first_name": "_Test", "last_name": "Finance Worker",
								"full_name": WORKER, "active": 1, "disbursement_department": "Cainta General"})
			w.insert()
			frappe.rename_doc("Church Worker", w.name, WORKER, force=True) if w.name != WORKER else None
		if not frappe.db.exists("Creditor", CREDITOR):
			frappe.get_doc({"doctype": "Creditor", "creditor_name": CREDITOR}).insert()
		if frappe.db.exists("Disbursement", DOC):
			frappe.delete_doc("Disbursement", DOC, force=True)

	def tearDown(self):
		frappe.db.rollback()
		frappe.local.cm_finance_ready = False

	# ------------------------------------------------------------ helpers

	def make_doc(self, expenses=None, allowances=None):
		doc = frappe.get_doc({
			"doctype": "Disbursement", "company": _company(), "month_recorded": MONTH, "year_recorded": YEAR,
			"monthly_expense_items": expenses if expenses is not None else [
				{"description": "Test Rent", "amount": 1000, "source": GEN_CASH, "purpose": "Rent", "department": "Pasig General"},
			],
			"disbursement_item_week_1": allowances or [],
		})
		doc.insert()
		return doc

	def row(self, doc, field="monthly_expense_items", idx=0):
		doc.reload()
		return doc.get(field)[idx]

	def claim(self, doc, row, **kw):
		args = dict(received_by=WORKER, received_date=f"{YEAR}-03-15", source=row.source or GEN_CASH)
		args.update(kw)
		return api.claim_item(doc.name, row.doctype, row.name, **args)

	def log(self, row_name):
		return list(reversed(audit.history(row_name=row_name)))

	def summary(self):
		return fund_summary.compute(FROM, TO, with_comments=False)

	# ------------------------------------------------------------ defaults and required department

	def test_department_defaults_from_worker_and_mission(self):
		doc = self.make_doc(allowances=[
			{"worker": WORKER, "amount": 500, "source": GEN_CASH, "purpose": "Allowance"},
			{"amount": 800, "source": "Mission Cash - JBC", "purpose": "Mission Support"},
		])
		rows = doc.disbursement_item_week_1
		self.assertEqual(rows[0].department, "Cainta General")
		self.assertEqual(rows[1].department, "Mission")

	def test_department_required(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_doc(expenses=[{"description": "No dept", "amount": 10, "source": GEN_CASH, "purpose": "Rent"}])

	def test_white_gift_lines_get_white_gift_project(self):
		doc = self.make_doc(expenses=[{"description": "Repairs", "amount": 10, "source": WG_CASH,
									   "purpose": "Maintenance", "department": "Pasig General"}])
		self.assertEqual(doc.monthly_expense_items[0].purpose, "White Gift Project")

	# ------------------------------------------------------------ claims

	def test_claim_requires_received_by_and_date(self):
		doc = self.make_doc()
		row = self.row(doc)
		row.status = "Claimed"
		row.received_by = WORKER
		with self.assertRaises(frappe.ValidationError):
			doc.save()

	def test_claimed_line_cannot_change_without_edit_claim(self):
		doc = self.make_doc()
		self.claim(doc, self.row(doc))
		doc.reload()
		doc.monthly_expense_items[0].amount = 900
		with self.assertRaises(frappe.ValidationError):
			doc.save()
		doc.reload()
		doc.monthly_expense_items[0].status = "Unclaimed"
		with self.assertRaises(frappe.ValidationError):
			doc.save()

	def test_edit_claim_requires_reason_and_keeps_original_amount(self):
		doc = self.make_doc()
		row = self.row(doc)
		self.claim(doc, row)
		with self.assertRaises(frappe.ValidationError):
			api.edit_claim(doc.name, row.name, {"amount": 900}, "")
		api.edit_claim(doc.name, row.name, {"amount": 900, "source": BEN_CASH}, REASON)
		row = self.row(doc)
		self.assertEqual(flt(row.amount), 900)
		self.assertEqual(flt(row.original_amount), 1000)
		self.assertTrue(row.amount_edited)
		entry = self.log(row.name)[-1]
		self.assertEqual(entry.action, "Edit Claim")
		self.assertEqual(entry.reason, REASON)
		changes = frappe.parse_json(entry.changes)
		self.assertEqual(changes["amount"], [1000.0, 900.0])
		self.assertEqual(changes["source"], [GEN_CASH, BEN_CASH])

	def test_reverse_and_reclaim_leaves_full_trail_and_correct_totals(self):
		doc = self.make_doc()
		row = self.row(doc)
		self.claim(doc, row)
		s = self.summary()
		self.assertEqual(s["disbursements"]["total"], 1000)
		self.assertEqual(s["funds"][0]["paid_out"], 1000)  # General is first

		api.reverse_claim(doc.name, row.name, REASON)
		row = self.row(doc)
		self.assertEqual(row.status, "Unclaimed")
		self.assertFalse(row.received_by or row.received_date)
		s = self.summary()
		self.assertEqual(s["disbursements"]["total"], 1000)  # still committed
		self.assertEqual(s["funds"][0]["paid_out"], 0)
		self.assertEqual(s["funds"][0]["pending"], 1000)

		api.update_item(doc.name, row.doctype, row.name, {"amount": 1200})
		self.claim(doc, self.row(doc))
		s = self.summary()
		self.assertEqual(s["disbursements"]["total"], 1200)
		self.assertEqual(s["funds"][0]["paid_out"], 1200)

		actions = [e.action for e in self.log(row.name)]
		self.assertEqual(actions, ["Line Added", "Claim", "Reverse Claim", "Amount Edit", "Claim"])
		reverse = self.log(row.name)[2]
		self.assertEqual(reverse.reason, REASON)
		self.assertIn("Claimed → Unclaimed", reverse.summary)

	# ------------------------------------------------------------ voids

	def test_void_excludes_line_everywhere_and_is_logged(self):
		doc = self.make_doc(expenses=[
			{"description": "Keep", "amount": 1000, "source": GEN_CASH, "purpose": "Rent", "department": "Pasig General"},
			{"description": "Drop", "amount": 300, "source": GEN_CASH, "purpose": "Rent", "department": "Pasig General"},
		])
		drop = self.row(doc, idx=1)
		with self.assertRaises(frappe.ValidationError):
			api.void_line(doc.name, drop.name, "")
		api.void_line(doc.name, drop.name, "Discontinued — will not be paid")
		doc.reload()
		self.assertEqual(flt(doc.total_amount_disbursed), 1000)
		s = self.summary()
		self.assertEqual(s["disbursements"]["total"], 1000)
		self.assertEqual(s["funds"][0]["pending"], 1000)
		lines = [ln for ln in fin.collect_lines(year=YEAR) if ln.row_name == drop.name]
		self.assertTrue(lines[0].voided and not lines[0].counted)
		self.assertEqual(self.log(drop.name)[-1].action, "Void")
		with self.assertRaises(frappe.ValidationError):
			api.claim_item(doc.name, drop.doctype, drop.name, WORKER, f"{YEAR}-03-15", GEN_CASH)
		api.unvoid_line(doc.name, drop.name, "Event is back on")
		s = self.summary()
		self.assertEqual(s["disbursements"]["total"], 1300)
		self.assertEqual(self.log(drop.name)[-1].action, "Unvoid")

	def test_claimed_line_cannot_be_voided(self):
		doc = self.make_doc()
		row = self.row(doc)
		self.claim(doc, row)
		with self.assertRaises(frappe.ValidationError):
			api.void_line(doc.name, row.name, "Discontinued — will not be paid")

	# ------------------------------------------------------------ audit log

	def test_audit_log_is_append_only(self):
		doc = self.make_doc()
		entry = frappe.get_doc("Disbursement Audit Log", self.log(self.row(doc).name)[0].name)
		entry.reason = "tampered"
		with self.assertRaises(frappe.PermissionError):
			entry.save(ignore_permissions=True)
		with self.assertRaises(frappe.PermissionError):
			frappe.delete_doc("Disbursement Audit Log", entry.name, ignore_permissions=True, force=True)

	def test_period_warning_names_closed_month(self):
		warnings = audit.period_warnings(frappe._dict(month_recorded="March", year_recorded=2026))
		self.assertTrue(any("March 2026" in w for w in warnings))

	# ------------------------------------------------------------ creditors

	def test_creditor_paid_line_payable_and_partial_reimbursement(self):
		doc = self.make_doc()
		row = self.row(doc)
		self.claim(doc, row, received_by=None, received_date=None, paid_by="Creditor", creditor=CREDITOR,
				   creditor_paid_date=f"{YEAR}-03-10", creditor_reference="OR-1")
		row = self.row(doc)
		self.assertTrue(row.payable)
		p = frappe.get_doc("Creditor Payable", row.payable)
		self.assertEqual((p.status, flt(p.outstanding_amount), p.fund), ("Unpaid", 1000, "General"))

		# Expense counts, no church cash moves
		s = self.summary()
		gen = s["funds"][0]
		self.assertEqual(s["disbursements"]["total"], 1000)
		self.assertEqual(s["by_purpose"]["Rent"], 1000)
		self.assertEqual((gen["paid_out"], gen["owed"]), (0, 1000))
		self.assertEqual(cred.reimbursed_by_account(FROM, TO), {})
		owe = cred.who_we_owe(f"{YEAR}-03-31", CREDITOR)
		self.assertEqual(owe["total"], 1000)
		self.assertEqual(owe["creditors"][0]["items"][0]["age_days"], 21)

		# Partial reimbursement: payable and cash account move by the same amount
		r = fapi.create_reimbursement(CREDITOR, f"{YEAR}-03-20", GEN_CASH, "School cashier",
									  [{"payable": p.name, "amount": 400}], "RCPT-9")
		p.reload()
		self.assertEqual((p.status, flt(p.paid_amount), flt(p.outstanding_amount)), ("Partly Paid", 400, 600))
		self.assertEqual(flt(cred.reimbursed_by_account(FROM, TO).get(GEN_CASH)), 400)
		gen = self.summary()["funds"][0]
		self.assertEqual((gen["paid_out"], gen["owed"], gen["disbursements"]), (400, 600, 1000))
		self.assertEqual(gen["after_pending_and_payables"], gen["balance"])  # cash − pending − owed = committed balance
		self.assertEqual(cred.who_we_owe(f"{YEAR}-03-31", CREDITOR)["total"], 600)
		hist = cred.creditor_history(CREDITOR)
		self.assertEqual([x["balance"] for x in hist["rows"]][-2:], [1000, 600])

		# A reimbursed line cannot be reversed or edited until the reimbursement is dealt with
		with self.assertRaises(frappe.ValidationError):
			api.reverse_claim(doc.name, row.name, REASON)
		with self.assertRaises(frappe.ValidationError):
			api.edit_claim(doc.name, row.name, {"amount": 800}, REASON)
		fapi.cancel_reimbursement(r, "Entered against the wrong payable")
		api.reverse_claim(doc.name, row.name, REASON)
		p.reload()
		self.assertEqual(p.docstatus, 2)
		self.assertFalse(self.row(doc).payable)
		actions = [e.action for e in self.log(row.name)]
		for a in ("Claim", "Payable Created", "Reimbursement", "Reimbursement Cancelled", "Reverse Claim", "Payable Cancelled"):
			self.assertIn(a, actions)

	def test_reimbursement_must_use_same_fund(self):
		doc = self.make_doc()
		row = self.row(doc)
		self.claim(doc, row, paid_by="Creditor", creditor=CREDITOR, creditor_paid_date=f"{YEAR}-03-10")
		with self.assertRaises(frappe.ValidationError):
			fapi.create_reimbursement(CREDITOR, f"{YEAR}-03-20", BEN_CASH, "Cashier",
									  [{"payable": self.row(doc).payable, "amount": 100}])

	def test_reimbursement_cannot_exceed_outstanding(self):
		doc = self.make_doc()
		self.claim(doc, self.row(doc), paid_by="Creditor", creditor=CREDITOR, creditor_paid_date=f"{YEAR}-03-10")
		with self.assertRaises(frappe.ValidationError):
			fapi.create_reimbursement(CREDITOR, f"{YEAR}-03-20", GEN_CASH, "Cashier",
									  [{"payable": self.row(doc).payable, "amount": 1500}])

	def test_average_months_stop_at_current_month(self):
		# A year still running averages over the months that happened
		self.assertEqual(fin.average_months("2026-01-01", "2026-12-31", today="2026-11-20"), 11)
		self.assertEqual(fin.average_months("2026-01-01", "2026-11-30", today="2026-11-20"), 11)
		# A finished year, and a range wholly in the future, use all their months
		self.assertEqual(fin.average_months("2025-01-01", "2025-12-31", today="2026-11-20"), 12)
		self.assertEqual(fin.average_months(FROM, TO, today="2026-11-20"), 1)

	def test_averages_rounded_to_centavos(self):
		self.make_doc(expenses=[{"description": "Odd", "amount": 100, "source": GEN_CASH, "purpose": "Rent",
								 "department": "Pasig General"}])
		s = fund_summary.compute(f"{YEAR}-01-01", f"{YEAR}-03-31", with_comments=False)
		gen = s["funds"][0]
		self.assertEqual(s["months"], 3)
		self.assertEqual(gen["avg_disbursements"], 33.33)

	def test_direct_payable_counts_as_expense(self):
		name = fapi.create_direct_payable(CREDITOR, f"{YEAR}-03-05", 250, "General", "Maintenance", "Pasig General",
										  "Aircon cleaning paid by school")
		s = self.summary()
		self.assertEqual(s["disbursements"]["total"], 250)
		self.assertEqual(s["funds"][0]["owed"], 250)
		self.assertEqual(s["funds"][0]["paid_out"], 0)
		self.assertEqual(cred.owed_by_fund(f"{YEAR}-03-31", [name]), {"General": 250})
		self.assertEqual(self.log(name)[-1].action, "Payable Created")
