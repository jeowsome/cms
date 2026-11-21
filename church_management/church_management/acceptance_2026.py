"""Acceptance checks for the finance upgrades (brief, "Acceptance checks").

    bench --site <site> execute church_management.church_management.acceptance_2026.run

Read-only for real data: the two scenario checks (a school payable with a
partial reimbursement, and a claim reversed and re-claimed) run inside a
savepoint that is rolled back, so nothing they create is kept.
"""
import io

import frappe
from frappe.utils import flt

FROM, TO = "2026-01-01", "2026-11-30"
PENDING_BEFORE_VOIDS = 164390.0
VOIDED_TOTAL = 20590.0

EXPECTED = {
	"collections": {"total": 1649459.14, "Mission": 156002.00, "Benevolence": 19752.25, "White Gift": 143000.00, "General": 1330704.89},
	"disbursements": {"total": 1512958, "Mission": 112680, "Benevolence": 8818, "White Gift": 88120, "General": 1303340},
	"surplus": 136501.14,
	"balances": {"Mission": 43322.00, "Benevolence": 10934.25, "White Gift": 54880.00, "General": 27364.89},
	"by_purpose": {
		"Allowance": 882700, "Benevolence": 8818, "Digital": 7800, "Government": 55340, "Kitchen Supplies": 6650,
		"Love Gift": 34500, "Maintenance": 2400, "Mission Support": 112680, "Professional Fees": 18000,
		"Regular Activity": 38300, "Rent": 185900, "Special Event": 44250, "Student Allowance": 13000,
		"Transportation": 14500, "White Gift Project": 88120,
	},
	"by_department": {
		"Cainta General": 181100, "Mission": 112680, "Pasig ColSPro": 11500, "Pasig General": 1172528,
		"Pasig Ladies": 2050, "Pasig Music Team": 1000, "Pasig SocMed": 2500, "Pasig Sunday School": 17800,
		"Pasig Young People": 11800,
	},
}


class Report:
	def __init__(self):
		self.rows, self.failed = [], 0

	def check(self, section, label, expected, actual):
		ok = abs(flt(expected) - flt(actual)) < 0.005 if isinstance(expected, (int, float)) else expected == actual
		self.failed += 0 if ok else 1
		self.rows.append((section, label, expected, actual, "OK" if ok else "MISMATCH"))

	def note(self, section, label, value):
		self.rows.append((section, label, "", value, "info"))

	def print(self):
		w = max(len(r[1]) for r in self.rows) + 2
		section = None
		for s, label, exp, act, status in self.rows:
			if s != section:
				print(f"\n== {s}")
				section = s
			fmt = lambda v: f"{v:,.2f}" if isinstance(v, (int, float)) else str(v)
			print(f"  {label:<{w}} expected {fmt(exp):>16}   actual {fmt(act):>16}   {status}")
		print(f"\n{len([r for r in self.rows if r[4] != 'info'])} checks, {self.failed} mismatch(es)")


def run():
	frappe.set_user("Administrator")
	rep = Report()
	fund_summary_checks(rep)
	tie_out_checks(rep)
	pending_check(rep)
	scenario(rep, payable_scenario)
	scenario(rep, reverse_reclaim_scenario)
	rep.print()
	return {"checks": len(rep.rows), "mismatches": rep.failed}


def fund_summary_checks(rep):
	from church_management.church_management import fund_summary

	fs = fund_summary.compute(FROM, TO, with_comments=False)
	sec = f"Fund Summary {fs['period']}"
	rep.check(sec, "Collections total", EXPECTED["collections"]["total"], fs["collections"]["total"])
	for f in ("Mission", "Benevolence", "White Gift", "General"):
		rep.check(sec, f"Collections {f}", EXPECTED["collections"][f], fs["collections"]["by_fund"][f])
	rep.check(sec, "Disbursements total", EXPECTED["disbursements"]["total"], fs["disbursements"]["total"])
	for f in ("Mission", "Benevolence", "White Gift", "General"):
		rep.check(sec, f"Disbursements {f}", EXPECTED["disbursements"][f], fs["disbursements"]["by_fund"][f])
	rep.check(sec, "Surplus", EXPECTED["surplus"], fs["surplus"])
	for f in fs["funds"]:
		rep.check(sec, f"Balance {f['fund']}", EXPECTED["balances"][f["fund"]], f["balance"])
	for p, v in EXPECTED["by_purpose"].items():
		rep.check("By purpose", p, v, fs["by_purpose"].get(p, 0))
	for p in sorted(set(fs["by_purpose"]) - set(EXPECTED["by_purpose"])):
		rep.check("By purpose", f"{p} (unexpected)", 0, fs["by_purpose"][p])
	got_dept = {d["department"]: d["total"] for d in fs["by_department"]}
	for d, v in EXPECTED["by_department"].items():
		rep.check("By department", d, v, got_dept.get(d, 0))
	for d in sorted(set(got_dept) - set(EXPECTED["by_department"])):
		rep.check("By department", f"{d} (unexpected)", 0, got_dept[d])


def tie_out_checks(rep):
	import openpyxl

	from church_management.church_management.financial_statement_export import build_workbook

	content, _name = build_workbook(2026)
	wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
	ws = wb["Summary"]
	in_table = False
	for row in ws.iter_rows(values_only=True):
		if row[0] == "Tie-out: statement vs detail sheets":
			in_table = True
			continue
		if in_table:
			if row[0] in (None, "Figure") or str(row[0]).startswith("Each statement"):
				if row[0] is None and rep.rows and rep.rows[-1][0] == "Summary tie-out":
					break
				continue
			rep.check("Summary tie-out", f"{row[0]} (difference)", 0, row[3])
	rep.note("Export", "Sheets", ", ".join(wb.sheetnames))
	fsws = wb["Fund Summary"]
	rep.note("Export", "Fund Summary title", fsws["A1"].value)
	per_fund = {}
	for row in fsws.iter_rows(values_only=True):
		if row[0] == "Per fund":
			continue
		if row[0] in ("Mission", "Benevolence", "White Gift", "General") and isinstance(row[6], (int, float)) and row[0] not in per_fund:
			per_fund[row[0]] = row
	# Whole-year export while the year is running: averages over the months so far (11 in November)
	from church_management.church_management import finance as fin
	n = fin.average_months("2026-01-01", "2026-12-31")
	rep.note("Export averages", "Months divided by", n)
	for f, bal in EXPECTED["balances"].items():
		rep.check("Export averages", f"{f} average balance / month (= {bal:,.2f} ÷ {n})", round(bal / n, 2), per_fund[f][6])


def pending_check(rep):
	from church_management.church_management import finance as fin

	lines = [ln for ln in fin.collect_lines(year=2026) if ln.kind == "line" and ln.docstatus != 2]
	pending = sum(ln.amount for ln in lines if ln.pending)
	voided = sum(ln.amount for ln in lines if ln.voided)
	rep.check("Voids", "Voided total", VOIDED_TOTAL, voided)
	rep.check("Voids", "Pending now = pending before voids − 20,590", PENDING_BEFORE_VOIDS - VOIDED_TOTAL, pending)


def scenario(rep, fn):
	frappe.db.savepoint("acceptance_scenario")
	try:
		fn(rep)
	finally:
		frappe.db.rollback(save_point="acceptance_scenario")
		frappe.local.cm_finance_ready = False


def _statement():
	from church_management.church_management.financial_statement_export import _statement

	st = _statement(2026)
	acct = {a["name"]: a for a in st["account_balances"]}
	return st, acct


def payable_scenario(rep):
	"""The school pays a ₱5,000 expense for us; we repay ₱2,000 from General Cash."""
	from church_management.api import disbursement as api
	from church_management.api import finance as fapi
	from church_management.church_management import creditors as cred
	from church_management.church_management import fund_summary

	sec = "Scenario: school payable"
	school = "Christian Bible Heritage Learning Center"
	before_fs = fund_summary.compute(FROM, TO, with_comments=False)
	before_st, before_acct = _statement()

	doc = frappe.get_doc("Disbursement", "November-2026")
	doc.append("monthly_expense_items", {"description": "Acceptance test — paid by the school", "amount": 5000,
		"source": "General Cash - JBC", "purpose": "Maintenance", "department": "Pasig General"})
	doc.flags.quiet_warnings = True
	doc.save()
	row = doc.monthly_expense_items[-1]
	api.claim_item(doc.name, row.doctype, row.name, received_by=None, received_date=None, source="General Cash - JBC",
		paid_by="Creditor", creditor=school, creditor_paid_date="2026-11-10", creditor_reference="TEST-OR")

	fs = fund_summary.compute(FROM, TO, with_comments=False)
	st, acct = _statement()
	gen = next(f for f in fs["funds"] if f["fund"] == "General")
	gen0 = next(f for f in before_fs["funds"] if f["fund"] == "General")
	rep.check(sec, "Expense appears: General disbursements +5,000", gen0["disbursements"] + 5000, gen["disbursements"])
	rep.check(sec, "Expense appears: Maintenance +5,000", before_fs["by_purpose"].get("Maintenance", 0) + 5000, fs["by_purpose"].get("Maintenance"))
	rep.check(sec, "No cash moves: General Cash available unchanged", before_acct["General Cash"]["effective_balance"], acct["General Cash"]["effective_balance"])
	rep.check(sec, "Owed to creditors (statement, General)", 5000, next(f for f in st["fund_cards"] if f["name"] == "General")["owed"])
	owe = cred.who_we_owe("2026-11-20", school)
	rep.check(sec, "Who we owe: school balance", 5000, owe["total"])

	payable = frappe.db.get_value(row.doctype, row.name, "payable")
	fapi.create_reimbursement(school, "2026-11-20", "General Cash - JBC", "School cashier",
		[{"payable": payable, "amount": 2000}], "TEST-RCPT")
	st2, acct2 = _statement()
	rep.check(sec, "Partial repay: payable outstanding", 3000, frappe.db.get_value("Creditor Payable", payable, "outstanding_amount"))
	rep.check(sec, "Partial repay: General Cash down by 2,000", acct["General Cash"]["effective_balance"] - 2000, acct2["General Cash"]["effective_balance"])
	rep.check(sec, "Partial repay: Who we owe", 3000, cred.who_we_owe("2026-11-20", school)["total"])
	rep.check(sec, "Expense not counted twice", fs["disbursements"]["total"], fund_summary.compute(FROM, TO, with_comments=False)["disbursements"]["total"])


def reverse_reclaim_scenario(rep):
	"""Reverse a real claim, then claim it again with a different amount."""
	from church_management.api import disbursement as api
	from church_management.church_management import disbursement_audit as audit
	from church_management.church_management import fund_summary

	sec = "Scenario: reverse and re-claim"
	doc = frappe.get_doc("Disbursement", "October-2026")
	row = next(r for r in doc.monthly_expense_items
			   if r.status == "Claimed" and r.received_by and r.received_date and (r.source or "").startswith("General")
			   and not r.payable)
	amt, who, when, src = flt(row.amount), row.received_by, str(row.received_date), row.source

	def totals():
		fs = fund_summary.compute(FROM, TO, with_comments=False)
		gen = next(f for f in fs["funds"] if f["fund"] == "General")
		return fs["disbursements"]["total"], gen["paid_out"], gen["pending"]

	t0 = totals()
	api.reverse_claim(doc.name, row.name, "Acceptance test: claimed on the wrong line")
	t1 = totals()
	rep.check(sec, "After reverse: committed unchanged", t0[0], t1[0])
	rep.check(sec, "After reverse: paid out − amount", t0[1] - amt, t1[1])
	rep.check(sec, "After reverse: pending + amount", t0[2] + amt, t1[2])
	api.update_item(doc.name, row.doctype, row.name, {"amount": amt + 50}, reason="Acceptance test: corrected amount")
	api.claim_item(doc.name, row.doctype, row.name, received_by=who, received_date=when, source=src)
	t2 = totals()
	rep.check(sec, "After re-claim: committed + 50", t0[0] + 50, t2[0])
	rep.check(sec, "After re-claim: paid out + 50", t0[1] + 50, t2[1])
	rep.check(sec, "After re-claim: pending back", t0[2], t2[2])
	trail = [h.action for h in reversed(audit.history(row_name=row.name))][-3:]
	rep.check(sec, "Audit trail (last 3)", "Reverse Claim → Amount Edit → Claim", " → ".join(trail))
	rev = [h for h in audit.history(row_name=row.name) if h.action == "Reverse Claim"][0]
	rep.check(sec, "Reverse entry keeps old receiver", True, (who or "") in (rev.summary or ""))
