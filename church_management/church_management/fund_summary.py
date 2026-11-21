"""Fund Summary: how much money each fund has, for any range of months.

Replaces the pivot tables the finance team built by hand (Sheet1/Sheet2):

  collections     active GL postings on each fund's cash and cashless
                  accounts in the range, cash and cashless combined
                  (White Gift: every posting up to the end date, all years)
  disbursements   committed basis — Claimed + Unclaimed, Voided excluded —
                  for every monthly document whose month lies in the range,
                  plus direct creditor payables dated in the range
  balance         collections − disbursements, per fund and in total

Cash and cashless stay separate accounts everywhere else; they are only
grouped by fund here.

Each fund also shows where its balance sits: church money actually paid out
(claimed lines paid by the church + reimbursements to creditors), what is
still pending, and what is owed to creditors. Cash − pending − owed equals
the committed balance whenever every reimbursement in the range is for an
expense in the range.
"""
import frappe
from frappe.utils import flt, getdate

from church_management.church_management import creditors as cred
from church_management.church_management import finance as fin


def collections_by_fund(from_date, to_date, settings=None):
	out = {f: 0.0 for f in fin.FUNDS}
	for _label, accounts, cumulative, _channel, fund in fin.fund_ledgers(settings):
		if not accounts:
			continue
		cond = "posting_date <= %(to)s" if cumulative else "posting_date between %(from)s and %(to)s"
		out[fund] += flt(frappe.db.sql(
			f"""select coalesce(sum(debit) - sum(credit), 0) from `tabGL Entry`
			where is_cancelled = 0 and account in %(accounts)s and {cond}""",
			{"accounts": tuple(accounts), "from": from_date, "to": to_date})[0][0])
	return out


def lines_in_range(from_date, to_date):
	"""Counted (not cancelled, not voided) lines of the range."""
	return [ln for ln in fin.collect_lines(from_date=from_date, to_date=to_date, include_cancelled=False) if ln.counted]


def compute(from_date, to_date, with_comments=True):
	from_date, to_date = str(getdate(from_date)), str(getdate(to_date))
	# Averages: months up to the current month when the range is still running
	months = fin.average_months(from_date, to_date)
	settings = frappe.get_single("Church Management Settings")

	coll = collections_by_fund(from_date, to_date, settings)
	lines = lines_in_range(from_date, to_date)

	def total(rows):
		return sum(r.amount for r in rows)

	disb = {f: total(r for r in lines if r.fund == f) for f in fin.FUNDS}
	by_purpose, general_by_purpose, by_dept = {}, {}, {}
	for r in lines:
		p = r.purpose or "No Purpose"
		d = r.department or "No Department"
		by_purpose[p] = by_purpose.get(p, 0.0) + r.amount
		if r.fund == "General":
			general_by_purpose[p] = general_by_purpose.get(p, 0.0) + r.amount
		dd = by_dept.setdefault(d, {"department": d, "total": 0.0, "purposes": {}})
		dd["total"] += r.amount
		dd["purposes"][p] = dd["purposes"].get(p, 0.0) + r.amount

	# Where each fund's balance sits
	reimbursed = cred.reimbursed_by_account(from_date, to_date)
	reimbursed_by_fund = {}
	for acc, amt in reimbursed.items():
		f = fin.fund_for_source(acc)
		reimbursed_by_fund[f] = reimbursed_by_fund.get(f, 0.0) + flt(amt)
	payable_names = [r.payable for r in lines if r.payable and r.claimed]
	owed = cred.owed_by_fund(to_date, payable_names) if payable_names else {}

	funds = []
	for f in fin.FUNDS:
		c, dsb = coll[f], disb[f]
		paid_out = total(r for r in lines if r.fund == f and r.cash_out) + reimbursed_by_fund.get(f, 0.0)
		pending = total(r for r in lines if r.fund == f and r.pending)
		cash = c - paid_out
		funds.append({
			"fund": f, "collections": c, "disbursements": dsb, "balance": c - dsb,
			"avg_collections": round(c / months, 2), "avg_disbursements": round(dsb / months, 2),
			"avg_balance": round((c - dsb) / months, 2),
			"paid_out": paid_out, "cash_balance": cash, "pending": pending, "owed": owed.get(f, 0.0),
			"after_pending_and_payables": cash - pending - owed.get(f, 0.0),
		})

	coll_total, disb_total = sum(coll.values()), sum(disb.values())
	out = {
		"from_date": from_date, "to_date": to_date, "months": months,
		"period": fin.period_label(from_date, to_date),
		"collections": {"total": coll_total, "by_fund": coll},
		"disbursements": {
			"total": disb_total, "by_fund": disb,
			"general_by_purpose": dict(sorted(general_by_purpose.items())),
		},
		"surplus": coll_total - disb_total,
		"funds": funds,
		"by_department": sorted(
			({**d, "purposes": dict(sorted(d["purposes"].items()))} for d in by_dept.values()),
			key=lambda d: d["department"]),
		"by_purpose": dict(sorted(by_purpose.items())),
		"line_count": len(lines),
	}
	if with_comments:
		out["comments"] = comments(from_date, to_date)
	return out


def comments(from_date, to_date):
	if not fin.schema_ready():
		return {f: {"comments": "", "modified": "", "modified_by": None} for f in fin.FUNDS}
	rows = frappe.get_all("Fund Summary Comment", filters={"from_date": from_date, "to_date": to_date},
		fields=["fund", "comments", "modified", "modified_by"])
	by = {r.fund: r for r in rows}
	return {f: {"comments": (by.get(f) or {}).get("comments") or "",
				"modified": str((by.get(f) or {}).get("modified") or ""),
				"modified_by": (by.get(f) or {}).get("modified_by")} for f in fin.FUNDS}
