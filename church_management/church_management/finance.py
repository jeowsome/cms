"""Shared finance rules: funds, disbursement lines and their states.

One place for the rules every finance screen, report and export must agree
on, so the statement, the Excel workbook, the Fund Summary and the audit log
can never count a line differently:

  fund          derived from the line's Source Account (it is not stored)
  line state    Claimed (paid out), Unclaimed (committed, pending) or
                Voided (discontinued, never to be paid — counted nowhere)
  paid by       Church funds (cash leaves a church account when claimed) or
                a Creditor (the expense is real, but no church money has
                moved; a Creditor Payable records what we owe)
"""
import calendar
from datetime import date, timedelta

import frappe
import frappe.utils
from frappe.utils import flt, getdate

MONTH_NAMES = list(calendar.month_name)[1:]
FUNDS = ("General", "Mission", "Benevolence", "White Gift")

CLAIMED, UNCLAIMED, VOIDED = "Claimed", "Unclaimed", "Voided"
CHURCH, CREDITOR = "Church funds", "Creditor"
WHITE_GIFT_PURPOSE = "White Gift Project"

# Disbursement child tables in form order: (fieldname, label, child doctype)
LINE_TABLES = (
	[(f"disbursement_item_week_{w}", f"Week {w} Allowances", "Disbursement Week Item") for w in range(1, 6)]
	+ [(f"expense_item_week_{w}", f"Week {w} Expenses", "Disbursement Week Expense Item") for w in range(1, 6)]
	+ [
		("monthly_expense_items", "Monthly Expenses", "Disbursement Week Expense Item"),
		("monthly_disbursement_items", "Monthly Mission Support", "Disbursement Week Item"),
	]
)
LINE_FIELDS = tuple(t[0] for t in LINE_TABLES)
SECTION_LABEL = {t[0]: t[1] for t in LINE_TABLES}
CHILD_DOCTYPE = {t[0]: t[2] for t in LINE_TABLES}


# ---------------------------------------------------------------- schema

def schema_ready():
	"""True once this site has been migrated to the finance-upgrade schema.

	The code ships to every site of the bench at once, but each site gets the
	new tables/columns only when it is migrated. Until then the new rules stay
	switched off so the site keeps working exactly as before. Only a positive
	answer is cached (per request), so a migration in progress picks it up."""
	if getattr(frappe.local, "cm_finance_ready", False):
		return True
	try:
		ready = (
			frappe.db.table_exists("Creditor Payable")
			and frappe.db.table_exists("Disbursement Audit Log")
			and frappe.db.has_column("Disbursement Week Item", "paid_by")
			and frappe.db.has_column("Disbursement Week Expense Item", "paid_by")
			and frappe.db.has_column("Church Worker", "disbursement_department")
		)
	except Exception:
		ready = False
	if ready:
		frappe.local.cm_finance_ready = True
	return bool(ready)


# ---------------------------------------------------------------- funds

def fund_for_source(src):
	"""Fund a disbursement line draws from, by its source account.
	Lines without a source fall into General so fund totals reconcile."""
	s = (src or "").lower()
	if "white gift" in s:
		return "White Gift"
	if "mission" in s:
		return "Mission"
	if "benevolence" in s:
		return "Benevolence"
	return "General"


def fund_ledgers(settings=None):
	"""The GL accounts behind each fund's collections, as the statement reads
	them: [(label, [accounts], cumulative, channel, fund)].

	General Cash = Tithes + Offering + Loose + Sunday School cash ledgers.
	White Gift is counted across all years; the rest per period."""
	s = settings or frappe.get_single("Church Management Settings")
	gen_cash = [a for a in (s.tithes_cash_account, s.offering_cash_account, s.loose_cash_account, s.sunday_school_cash_account) if a]
	gen_cls = [a for a in (s.tithes_cashless_account, s.offering_cashless_account, s.loose_cashless_account) if a]
	return [
		("General Cash", gen_cash, False, "cash", "General"),
		("General Cashless", gen_cls, False, "cashless", "General"),
		("Mission Cash", [a for a in [s.mission_cash_account] if a], False, "cash", "Mission"),
		("Mission Cashless", [a for a in [s.mission_cashless_account] if a], False, "cashless", "Mission"),
		("Benevolence Cash", [a for a in [s.benevolence_cash_account] if a], False, "cash", "Benevolence"),
		("Benevolence Cashless", [a for a in [s.benevolence_cashless_account] if a], False, "cashless", "Benevolence"),
		("White Gift Cash", [a for a in [s.white_gift_cash_account] if a], True, "cash", "White Gift"),
		("White Gift Cashless", [a for a in [s.white_gift_cashless_account] if a], True, "cashless", "White Gift"),
	]


# ---------------------------------------------------------------- dates

def month_index(month_name):
	return MONTH_NAMES.index(month_name) + 1 if month_name in MONTH_NAMES else None


def sundays(year, month):
	first = date(year, month, 1)
	d = first + timedelta(days=(6 - first.weekday()) % 7)
	out = []
	while d.month == month:
		out.append(d)
		d += timedelta(days=7)
	return out


def due_date(year, month_idx, field):
	"""Week N lines fall due on the month's Nth Sunday; monthly lines by month end."""
	if field.startswith(("disbursement_item_week_", "expense_item_week_")):
		suns = sundays(year, month_idx)
		w = int(field.rsplit("_", 1)[1])
		if w <= len(suns):
			return suns[w - 1]
	return date(year, month_idx, calendar.monthrange(year, month_idx)[1])


def months_in_range(from_date, to_date):
	f, t = getdate(from_date), getdate(to_date)
	return max(0, (t.year * 12 + t.month) - (f.year * 12 + f.month) + 1)


def average_months(from_date, to_date, today=None):
	"""Months to divide by for monthly averages.

	A range that runs past the current month (e.g. a whole year still in
	progress) is averaged over the months up to and including the current
	month — the months that have actually happened. A range wholly in the
	past, or wholly in the future, uses all its months."""
	f, t = getdate(from_date), getdate(to_date)
	today = getdate(today) if today else getdate(frappe.utils.nowdate())
	if f <= today < t:
		t = min(t, date(today.year, today.month, calendar.monthrange(today.year, today.month)[1]))
	return max(1, months_in_range(f, t))


def ym_in_range(year, month_idx, from_date, to_date):
	"""True when the month (year, month_idx) lies within the date range."""
	f, t = getdate(from_date), getdate(to_date)
	key = int(year) * 12 + month_idx
	return f.year * 12 + f.month <= key <= t.year * 12 + t.month


def period_label(from_date, to_date):
	f, t = getdate(from_date), getdate(to_date)
	if (f.year, f.month) == (t.year, t.month):
		return f"{MONTH_NAMES[f.month - 1]} {f.year}"
	if f.year == t.year:
		return f"{MONTH_NAMES[f.month - 1]}–{MONTH_NAMES[t.month - 1]} {t.year}"
	return f"{MONTH_NAMES[f.month - 1]} {f.year}–{MONTH_NAMES[t.month - 1]} {t.year}"


# ---------------------------------------------------------------- lines

def state(row):
	"""Claimed / Unclaimed / Voided — by status only. (Received By + Date
	without the Claimed status is not a claim: the claim guard makes the two
	agree for every new claim.)"""
	if row is None:
		return None
	st = row.get("status")
	if st == VOIDED:
		return VOIDED
	return CLAIMED if st == CLAIMED else UNCLAIMED


def paid_by_creditor(row):
	return (row.get("paid_by") or CHURCH) == CREDITOR


def pays_from_church_account(row):
	"""A claimed line paid with church money: deducted from its source account."""
	return state(row) == CLAIMED and not paid_by_creditor(row)


def line_label(row):
	return (
		row.get("worker") or row.get("description") or row.get("remarks")
		or row.get("purpose") or row.get("name")
	)


def iter_lines(doc):
	"""(fieldname, section label, row) for every line of a Disbursement."""
	if not doc:
		return
	for field in LINE_FIELDS:
		for row in doc.get(field) or []:
			yield field, SECTION_LABEL[field], row


def find_line(doc, row_name):
	for field, label, row in iter_lines(doc):
		if row.name == row_name:
			return field, label, row
	frappe.throw(frappe._("Line {0} was not found in {1}.").format(row_name, doc.name))


def collect_lines(year=None, from_date=None, to_date=None, include_cancelled=True):
	"""Every disbursement line (and every direct creditor payable) as a flat
	dict, in form order. Filter by year or by a date range of months.

	Each line carries: counted (not cancelled, not voided), claimed, voided,
	cash_out (claimed with church money), the fund, due date and payee."""
	filters = {}
	if year:
		filters["year_recorded"] = int(year)
	if not include_cancelled:
		filters["docstatus"] = ["<", 2]
	docs = frappe.get_all("Disbursement", filters=filters, fields=["name", "month_recorded", "year_recorded", "docstatus"])
	docs = [d for d in docs if month_index(d.month_recorded) and d.year_recorded]
	if from_date and to_date:
		docs = [d for d in docs if ym_in_range(d.year_recorded, month_index(d.month_recorded), from_date, to_date)]
	docs.sort(key=lambda d: (int(d.year_recorded), month_index(d.month_recorded), d.name))

	out = []
	for d in docs:
		doc = frappe.get_doc("Disbursement", d.name)
		y, m = int(d.year_recorded), month_index(d.month_recorded)
		for field, label, it in iter_lines(doc):
			st = state(it)
			out.append(_line_dict(
				kind="line", disbursement=d.name, month=d.month_recorded, m_idx=m, year=y,
				docstatus=d.docstatus, field=field, section=label, due=due_date(y, m, field),
				row=it, status=st,
			))
	out.extend(direct_payable_lines(year=year, from_date=from_date, to_date=to_date))
	return out


def _line_dict(kind, disbursement, month, m_idx, year, docstatus, field, section, due, row, status):
	amt = flt(row.get("amount"))
	counted = docstatus != 2 and status != VOIDED
	creditor_paid = paid_by_creditor(row)
	return frappe._dict(
		kind=kind, disbursement=disbursement, month=month, m_idx=m_idx, year=year, docstatus=docstatus,
		field=field, section=section, due=due, row_name=row.get("name"),
		fund=fund_for_source(row.get("source")), source=row.get("source"),
		purpose=row.get("purpose"), department=row.get("department"),
		payee=row.get("worker") or row.get("default_receiver"),
		description=row.get("description"), remarks=row.get("remarks"),
		original=flt(row.get("original_amount")) if row.get("amount_edited") else None,
		amount=amt, status=status,
		received_by=row.get("received_by"), received_date=row.get("received_date"),
		void_reason=row.get("void_reason"),
		paid_by=row.get("paid_by") or CHURCH, creditor=row.get("creditor"),
		creditor_paid_date=row.get("creditor_paid_date"), creditor_reference=row.get("creditor_reference"),
		payable=row.get("payable"),
		counted=counted, claimed=counted and status == CLAIMED, pending=counted and status == UNCLAIMED,
		voided=status == VOIDED, cash_out=counted and status == CLAIMED and not creditor_paid,
		creditor_paid=counted and status == CLAIMED and creditor_paid,
	)


def direct_payable_lines(year=None, from_date=None, to_date=None):
	"""Expenses a creditor paid that were never on a monthly disbursement
	document. They count like a claimed line paid by that creditor, in the
	month of the date the creditor paid."""
	if not schema_ready():
		return []
	filters = {"source_type": "Direct", "docstatus": 1}
	if year:
		filters["posting_date"] = ["between", [f"{int(year)}-01-01", f"{int(year)}-12-31"]]
	elif from_date and to_date:
		filters["posting_date"] = ["between", [from_date, to_date]]
	out = []
	for p in frappe.get_all(
		"Creditor Payable", filters=filters,
		fields=["name", "creditor", "posting_date", "amount", "fund", "purpose", "department", "description", "reference"],
		order_by="posting_date asc, name asc",
	):
		d = getdate(p.posting_date)
		row = frappe._dict(
			name=p.name, amount=p.amount, purpose=p.purpose, department=p.department,
			description=p.description, status=CLAIMED, paid_by=CREDITOR, creditor=p.creditor,
			creditor_paid_date=p.posting_date, creditor_reference=p.reference, payable=p.name,
			received_date=p.posting_date, source=None,
		)
		line = _line_dict(
			kind="direct_payable", disbursement=p.name, month=MONTH_NAMES[d.month - 1], m_idx=d.month,
			year=d.year, docstatus=1, field="direct_payable", section="Direct Payable", due=d,
			row=row, status=CLAIMED,
		)
		line.fund = p.fund
		out.append(line)
	return out
