"""Excel workbook behind the financial statement's "Download" button.

Built for an accountant checking the year's cash flow by hand:

  Summary            the statement's own figures (funds, accounts, position)
                     plus tie-out checks against the detail sheets
  Monthly Cash Flow  money in by fund, money paid out by fund, net and running
  Collections        every Collection of the year, drafts included
  Disbursements      every disbursement line item, claimed and unclaimed
  Ledger Postings    the GL entries behind the account balances
  Fund Summary       collections, committed disbursements and balance per
                     fund, by purpose and department, with the team's comments
  Payables           every creditor payable and reimbursement
  Audit Log          every change to a disbursement line, with reasons

Nothing is filtered out silently: drafts, cancelled documents and unclaimed
items are listed with a Status column and a "Counted in Statement" column
that says whether the statement includes the row, and how.
"""

import calendar
import io
from datetime import datetime

import frappe
from frappe.utils import getdate, now_datetime, nowdate
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from church_management.church_management import creditors as cred
from church_management.church_management import finance as fin
from church_management.church_management import fund_summary
from church_management.www.financial_statement import MONTH_NAMES, get_context

DOC_STATUS = {0: "Draft", 1: "Submitted", 2: "Cancelled"}
FUNDS = ("General", "Mission", "Benevolence", "White Gift")

MONEY = '#,##0.00;[Red]-#,##0.00'
DATE = 'yyyy-mm-dd'
DATETIME = 'yyyy-mm-dd hh:mm'

HEAD_FILL = PatternFill("solid", fgColor="1E3A5F")
HEAD_FONT = Font(bold=True, color="FFFFFF")
TITLE_FONT = Font(bold=True, size=14)
SECTION_FONT = Font(bold=True, size=12, color="1E3A5F")
BOLD = Font(bold=True)
MUTED = Font(italic=True, color="7F7F7F")
TOTAL_FILL = PatternFill("solid", fgColor="E8EEF5")
TOP_BORDER = Border(top=Side(style="thin", color="1E3A5F"))
STATUS_FILLS = {
    "Draft": PatternFill("solid", fgColor="FFF2CC"),
    "Cancelled": PatternFill("solid", fgColor="E7E6E6"),
    "Unclaimed": PatternFill("solid", fgColor="FCE4D6"),
    "Claimed": PatternFill("solid", fgColor="E2EFDA"),
    "Voided": PatternFill("solid", fgColor="E7E6E6"),
    "Paid": PatternFill("solid", fgColor="E2EFDA"),
    "Partly Paid": PatternFill("solid", fgColor="FFF2CC"),
    "Unpaid": PatternFill("solid", fgColor="FCE4D6"),
    "Submitted": PatternFill("solid", fgColor="E2EFDA"),
    "OK": PatternFill("solid", fgColor="E2EFDA"),
    "MISMATCH": PatternFill("solid", fgColor="F8CBAD"),
}

# Disbursement child tables in form order, with the label the form shows
DISB_SECTIONS = (
    [(f"disbursement_item_week_{w}", f"Week {w} Allowances") for w in range(1, 6)]
    + [(f"expense_item_week_{w}", f"Week {w} Expenses") for w in range(1, 6)]
    + [("monthly_expense_items", "Monthly Expenses"),
       ("monthly_disbursement_items", "Monthly Mission Support")]
)


# ---------------------------------------------------------------- helpers

def _f(v):
    return float(v or 0)


def _v(v):
    """Cell value: round floats to centavos so sums carry no float noise."""
    return round(v, 2) + 0.0 if isinstance(v, float) else v


def _statement(year):
    """The statement page's own figures for the whole year (no month filter)."""
    saved = frappe.form_dict
    frappe.form_dict = frappe._dict(year=str(year), month="", group_by="Source")
    try:
        return get_context(frappe._dict())
    finally:
        frappe.form_dict = saved


def _sheet_table(ws, headers, rows, money_cols=(), date_cols=(), datetime_cols=(),
                 status_cols=(), widths=None, start_row=1, muted_when=None):
    """Header + rows with formats, frozen header, filter and column widths.

    muted_when(row) -> True greys out rows the statement does not count."""
    for c, h in enumerate(headers, 1):
        cell = ws.cell(row=start_row, column=c, value=h)
        cell.fill, cell.font = HEAD_FILL, HEAD_FONT
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    idx = {h: i + 1 for i, h in enumerate(headers)}
    for r, row in enumerate(rows, start_row + 1):
        muted = muted_when(row) if muted_when else False
        for c, v in enumerate(row, 1):
            cell = ws.cell(row=r, column=c, value=_v(v))
            if muted:
                cell.font = MUTED
        for h in money_cols:
            ws.cell(row=r, column=idx[h]).number_format = MONEY
        for h in date_cols:
            ws.cell(row=r, column=idx[h]).number_format = DATE
        for h in datetime_cols:
            ws.cell(row=r, column=idx[h]).number_format = DATETIME
        for h in status_cols:
            cell = ws.cell(row=r, column=idx[h])
            if cell.value in STATUS_FILLS:
                cell.fill = STATUS_FILLS[cell.value]
    last = start_row + len(rows)
    ws.freeze_panes = ws.cell(row=start_row + 1, column=1)
    ws.auto_filter.ref = f"A{start_row}:{get_column_letter(len(headers))}{max(last, start_row + 1)}"
    ws.row_dimensions[start_row].height = 32
    for c, h in enumerate(headers, 1):
        w = (widths or {}).get(h) or max(10, min(40, len(str(h)) + 2))
        ws.column_dimensions[get_column_letter(c)].width = w
    return idx, last


def _total_row(ws, row, headers, label, values, label_col=1):
    """A labelled totals row below a table. values: {header: number}."""
    idx = {h: i + 1 for i, h in enumerate(headers)}
    ws.cell(row=row, column=label_col, value=label).font = BOLD
    for c in range(1, len(headers) + 1):
        cell = ws.cell(row=row, column=c)
        cell.fill, cell.border = TOTAL_FILL, TOP_BORDER
    for h, v in values.items():
        cell = ws.cell(row=row, column=idx[h], value=_v(v))
        cell.number_format, cell.font = MONEY, BOLD


def _kv_block(ws, row, title, pairs, note=None):
    """Section title then label/amount pairs in columns A/B. Returns next free row."""
    ws.cell(row=row, column=1, value=title).font = SECTION_FONT
    row += 1
    if note:
        ws.cell(row=row, column=1, value=note).font = MUTED
        row += 1
    for label, value in pairs:
        ws.cell(row=row, column=1, value=label)
        cell = ws.cell(row=row, column=2, value=_v(value))
        if isinstance(value, float):
            cell.number_format = MONEY
        elif isinstance(value, int):
            cell.number_format = "0"
        row += 1
    return row + 1


def _grid_block(ws, row, title, headers, rows, note=None, money_from=1):
    """Section title then a small table; columns from money_from on are amounts."""
    ws.cell(row=row, column=1, value=title).font = SECTION_FONT
    row += 1
    if note:
        ws.cell(row=row, column=1, value=note).font = MUTED
        row += 1
    for c, h in enumerate(headers, 1):
        cell = ws.cell(row=row, column=c, value=h)
        cell.fill, cell.font = HEAD_FILL, HEAD_FONT
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    ws.row_dimensions[row].height = 32
    for r in rows:
        row += 1
        for c, v in enumerate(r, 1):
            cell = ws.cell(row=row, column=c, value=_v(v))
            if c > money_from and isinstance(v, (int, float)):
                cell.number_format = MONEY
            if v in ("OK", "MISMATCH"):
                cell.fill = STATUS_FILLS[v]
            if r and r[0] == "Total":
                cell.font, cell.fill, cell.border = BOLD, TOTAL_FILL, TOP_BORDER
    return row + 2


# ---------------------------------------------------------------- data

def _collections(year):
    rows = frappe.get_all(
        "Collection",
        filters=[["date", ">=", f"{year}-01-01"], ["date", "<", f"{year + 1}-01-01"]],
        fields=["name", "date", "docstatus", "cost_center", "attendees", "journal_entry",
                "tithes_total", "tithes_total_cls", "offering_total", "offering_total_cls",
                "mission_total", "mission_total_cls", "benevolence_collection", "benevolence_collection_cls",
                "loose_collection", "loose_collection_cls", "sunday_school_collection",
                "grand_total", "grand_total_cls", "tally_total", "cash_grand_total_difference",
                "no_of_tithes", "no_of_tithes_cls", "no_of_offering", "no_of_offering_cls",
                "no_of_mission", "no_of_mission_cls", "amended_from"],
        order_by="date asc, name asc",
    )
    for c in rows:
        d = c.date if isinstance(c.date, datetime) else datetime.combine(getdate(c.date), datetime.min.time())
        c.dt = d
        c.month = MONTH_NAMES[d.month - 1]
        suffix = (c.name or "").rsplit(" ", 1)[-1].upper()
        c.service = suffix.title() if suffix in ("MORNING", "EVENING") else ("Morning" if d.hour < 12 else "Evening")
        c.status = DOC_STATUS.get(c.docstatus, str(c.docstatus))
        c.counted = c.docstatus == 1
        c.funds = {
            "General": sum(_f(c[k]) for k in ("tithes_total", "tithes_total_cls", "offering_total", "offering_total_cls",
                                               "loose_collection", "loose_collection_cls", "sunday_school_collection")),
            "Mission": _f(c.mission_total) + _f(c.mission_total_cls),
            "Benevolence": _f(c.benevolence_collection) + _f(c.benevolence_collection_cls),
        }
    return rows


def _disbursement_items(year):
    """Every line item of every Disbursement of the year, in form order,
    plus direct creditor payables (kind == "direct_payable")."""
    today = getdate(nowdate())
    out = []
    for ln in fin.collect_lines(year=year):
        if ln.kind == "line" and ln.docstatus == 2:
            counted = "No (cancelled)"
        elif ln.voided:
            counted = "No - voided"
        elif ln.creditor_paid:
            counted = "Yes - paid by creditor"
        elif ln.claimed:
            counted = "Yes - paid out"
        else:
            counted = "Yes - pending"
        ln.doc_status = DOC_STATUS.get(ln.docstatus, str(ln.docstatus))
        ln.claim_status = ln.status
        ln.counted_label = counted
        ln.days_overdue = (today - ln.due).days if (ln.pending and ln.due and ln.due < today) else None
        out.append(ln)
    return out


def _ledger(statement, year):
    """GL entries for every account behind the statement's account balances."""
    accounts = {}
    for a in statement.get("account_balances") or []:
        for acc in a.get("ledgers") or []:
            accounts[acc] = (a["name"], a.get("fund"), a.get("cumulative"))
    if not accounts:
        return []
    gl = frappe.get_all(
        "GL Entry",
        filters={"account": ["in", list(accounts)]},
        fields=["posting_date", "account", "debit", "credit", "voucher_type", "voucher_no",
                "remarks", "is_cancelled"],
        order_by="posting_date asc, creation asc",
    )
    je_to_collection = dict(frappe.get_all("Collection", filters={"journal_entry": ["is", "set"]},
                                           fields=["journal_entry", "name"], as_list=True))
    je_to_wg = dict(frappe.get_all("White Gift", filters={"journal_entry": ["is", "set"]},
                                   fields=["journal_entry", "name"], as_list=True))
    rows = []
    for g in gl:
        label, fund, cumulative = accounts[g.account]
        in_year = getdate(g.posting_date).year == year
        if not (in_year or cumulative):
            continue
        source = (je_to_collection.get(g.voucher_no) or je_to_wg.get(g.voucher_no)
                  or ("(cancelled entry)" if g.is_cancelled else "(not from a collection)"))
        rows.append([
            getdate(g.posting_date), g.account, label, fund,
            _f(g.debit), _f(g.credit), _f(g.debit) - _f(g.credit),
            g.voucher_type, g.voucher_no, source,
            "Cancelled" if g.is_cancelled else "Active",
            "No (cancelled)" if g.is_cancelled else ("Yes - all years" if cumulative else "Yes"),
            (g.remarks or "")[:200],
        ])
    return rows


# ---------------------------------------------------------------- sheets

def _summary_sheet(ws, year, month, st, cols, items, payables):
    fs = st.get("financial_summary") or {}
    pos = st.get("position") or {}
    counted_cols = [c for c in cols if c.counted]
    ws["A1"] = f"Jezreel Baptist Church Pasig — Financial Statement {year}"
    ws["A1"].font = TITLE_FONT
    ws["A2"] = f"Generated {now_datetime():%Y-%m-%d %H:%M} by {frappe.session.user}" + (
        f" · detail sheets filtered to {month}" if month else " · whole year")
    ws["A2"].font = MUTED
    row = 4

    row = _kv_block(ws, row, "How to read this workbook", [
        ("Collections", "Only Submitted collections are counted. Drafts and cancelled ones are listed for reference, greyed out."),
        ("Disbursements", "Every line item is listed. Claimed = paid out; Unclaimed = committed but not yet paid (pending); Voided = discontinued, never to be paid, counted nowhere."),
        ("Creditors", "A line Paid by a creditor is a real expense but takes no church money; we owe the creditor (sheet 'Payables') until a reimbursement repays them from a church account."),
        ("Disbursement status", "Monthly Disbursement documents normally stay in Draft; their items still count. Only cancelled documents are left out."),
        ("Counted in Statement", "Says whether, and how, the statement includes each row. Filter on it to rebuild any total."),
        ("Funds", "General = Tithes + Offering + Loose + Sunday School. Mission and Benevolence are set aside. White Gift is separate and counted across all years."),
        ("Ledger balances", "Come from the GL (sheet 'Ledger Postings'). Claimed disbursements are deducted from the account named as their Source."),
    ])

    # Tie-outs: the statement's figures vs a rebuild from the detail sheets
    stmt_cash, stmt_cls = _f(fs.get("cash_collected")), _f(fs.get("cashless_collected"))
    det_cash = sum((_f(c.grand_total) for c in counted_cols), 0.0)
    det_cls = sum((_f(c.grand_total_cls) for c in counted_cols), 0.0)
    live = [i for i in items if i.counted]
    det_claimed = sum(i.amount for i in live if i.claimed)
    det_unclaimed = sum(i.amount for i in live if i.pending)
    checks = [
        ("Cash collected", stmt_cash, det_cash),
        ("Cashless collected", stmt_cls, det_cls),
        ("Disbursed (claimed, incl. paid by creditors)", _f(fs.get("total_disbursed")), det_claimed),
        ("Pending (unclaimed, excl. voided)", _f(fs.get("total_unclaimed")), det_unclaimed),
        ("Repaid to creditors", _f(fs.get("total_reimbursed")), sum(r["reimbursed"] for r in payables if r["type"] == "Reimbursement" and r["counted"])),
        ("Owed to creditors", _f(fs.get("owed_to_creditors")), sum(r["outstanding"] or 0 for r in payables if r["type"] == "Payable" and r["counted"])),
    ]
    if not month:
        row = _grid_block(ws, row, "Tie-out: statement vs detail sheets",
                          ["Figure", "On statement", "From detail sheets", "Difference", "Check"],
                          [[n, a, b, a - b, "OK" if abs(a - b) < 0.005 else "MISMATCH"] for n, a, b in checks],
                          note="Each statement figure rebuilt from the rows in this file.")

    drafts = [c for c in cols if c.docstatus == 0]
    cancelled = [c for c in cols if c.docstatus == 2]
    row = _kv_block(ws, row, f"Collections{' — ' + month if month else ''}", [
        ("Submitted collections (counted)", len(counted_cols)),
        ("Cash collected", det_cash),
        ("Cashless collected", det_cls),
        ("Total collected", det_cash + det_cls),
        ("   General fund", sum((c.funds["General"] for c in counted_cols), 0.0)),
        ("   Mission fund", sum((c.funds["Mission"] for c in counted_cols), 0.0)),
        ("   Benevolence fund", sum((c.funds["Benevolence"] for c in counted_cols), 0.0)),
        ("Draft collections (NOT counted)", len(drafts)),
        ("   Amount in drafts", sum((_f(c.grand_total) + _f(c.grand_total_cls) for c in drafts), 0.0)),
        ("Cancelled collections (NOT counted)", len(cancelled)),
    ])

    by_fund = [[f,
                sum(i.amount for i in live if i.fund == f and i.cash_out),
                sum(i.amount for i in live if i.fund == f and i.creditor_paid),
                sum(i.amount for i in live if i.fund == f and i.pending)] for f in FUNDS]
    by_fund = [r + [r[1] + r[2] + r[3]] for r in by_fund]
    by_fund.append(["Total"] + [sum(r[k] for r in by_fund) for k in (1, 2, 3, 4)])
    voided = [i for i in items if i.voided and i.docstatus != 2]
    row = _grid_block(ws, row, f"Disbursements by fund{' — ' + month if month else ''}",
                      ["Fund", "Claimed (paid by church)", "Claimed (paid by creditor)", "Unclaimed (pending)", "Total committed"], by_fund,
                      note=f"{sum(1 for i in live if i.claimed)} claimed and {sum(1 for i in live if i.pending)} unclaimed line items. "
                           f"{len(voided)} voided line(s) (₱{sum(i.amount for i in voided):,.2f}) are not counted.")

    fund_rows = [[f["name"], f["received"], f["from_collections"], f["other_postings"], f["claimed"],
                  f["available"], f["cash"], f["cashless"], f["pending"], f.get("owed", 0.0), f["projected"],
                  ", ".join(f["overdrawn_accounts"])] for f in st.get("fund_cards") or []]
    if fund_rows:
        fund_rows.append(["Total"] + [sum(r[k] for r in fund_rows) for k in range(1, 11)] + [""])
    row = _grid_block(ws, row, f"Funds (as on the statement, year {year})",
                      ["Fund", "Received (ledger)", "From collections", "Other postings", "Paid from accounts",
                       "Available", "Cash", "Cashless", "Pending", "Owed to creditors", "After pending & payables",
                       "Overdrawn accounts"],
                      fund_rows,
                      note="Received = GL balance of the fund's cash/cashless accounts. Paid from accounts = claims paid with church money + reimbursements to creditors. "
                           "Available = Received − Paid. After pending & payables = Available − Pending − Owed to creditors.")

    acct_rows = [[a["name"], a.get("fund") or "—", a["ledger_balance"], a["pending_deductions"],
                  a["effective_balance"], a["pending"], a["effective_balance"] - a["pending"]]
                 for a in st.get("account_balances") or []]
    if acct_rows:
        acct_rows.append(["Total", ""] + [sum(r[k] for r in acct_rows) for k in range(2, 7)])
    row = _grid_block(ws, row, "Account balances (as on the statement)",
                      ["Account", "Fund", "Ledger balance", "Claimed from it", "Available", "Pending", "After pending"],
                      acct_rows, money_from=2,
                      note="General Cash = Tithes + Offering + Loose + Sunday School cash ledgers. White Gift is all-years; the rest are this year only.")

    row = _kv_block(ws, row, "Where the money stands (as on the statement)", [
        ("Cash on hand (excl. White Gift)", _f(pos.get("cash"))),
        ("Cashless (excl. White Gift)", _f(pos.get("cashless"))),
        ("Claimed with no matching account", _f(pos.get("unassigned"))),
        ("Available (all operating funds)", _f(pos.get("available"))),
        ("Less pending claims (excl. White Gift)", -_f(pos.get("unclaimed_operating"))),
        ("Less owed to creditors (excl. White Gift)", -_f(pos.get("owed_operating"))),
        ("After pending claims and payables", _f(pos.get("projected"))),
        ("White Gift available", _f(pos.get("white_gift"))),
    ])

    ws.column_dimensions["A"].width = 40
    for col in "BCDEFGHIJ":
        ws.column_dimensions[col].width = 18
    ws.column_dimensions["K"].width = 26


def _cash_flow_sheet(ws, year, cols, items, payables):
    headers = ["Month", "Collected - Cash", "Collected - Cashless", "Collected - Total",
               "In - General", "In - Mission", "In - Benevolence",
               "Paid Out - General", "Paid Out - Mission", "Paid Out - Benevolence", "Paid Out - Total",
               "Net Cash Flow", "Running Balance",
               "Pending (Unclaimed)", "Paid Out - White Gift", "Draft Collections (not counted)",
               "Paid by Creditors (no cash)", "Repaid to Creditors"]
    months = sorted({c.month for c in cols} | {i.month for i in items if i.month in MONTH_NAMES}
                    | {r["month"] for r in payables if r["month"]},
                    key=MONTH_NAMES.index)
    rows, running = [], 0.0
    for m in months:
        mc = [c for c in cols if c.month == m and c.counted]
        mi = [i for i in items if i.month == m and i.counted]
        cash, cls = sum(_f(c.grand_total) for c in mc), sum(_f(c.grand_total_cls) for c in mc)
        repaid = {f: sum(r["reimbursed"] for r in payables if r["type"] == "Reimbursement" and r["counted"]
                         and r["month"] == m and r["fund"] == f) for f in FUNDS}
        out = {f: sum(i.amount for i in mi if i.cash_out and i.fund == f) + repaid[f] for f in FUNDS}
        out_op = out["General"] + out["Mission"] + out["Benevolence"]
        net = cash + cls - out_op
        running += net
        rows.append([m, cash, cls, cash + cls,
                     sum(c.funds["General"] for c in mc), sum(c.funds["Mission"] for c in mc),
                     sum(c.funds["Benevolence"] for c in mc),
                     out["General"], out["Mission"], out["Benevolence"], out_op,
                     net, running,
                     sum(i.amount for i in mi if i.pending), out["White Gift"],
                     sum(_f(c.grand_total) + _f(c.grand_total_cls) for c in cols if c.month == m and c.docstatus == 0),
                     sum(i.amount for i in mi if i.creditor_paid), sum(repaid.values())])
    ws["A1"] = f"Monthly cash flow {year}"
    ws["A1"].font = TITLE_FONT
    ws["A2"] = ("In = submitted collections. Paid Out = church money that left: claimed items paid by the church plus reimbursements to creditors. "
                "Items a creditor paid are expenses but not cash out until repaid. Net = Collected − Paid Out "
                "(General + Mission + Benevolence); White Gift payouts come from the separate White Gift fund and are shown apart. "
                "Pending items are committed but not yet paid, so they are not in Net.")
    ws["A2"].font = MUTED
    money = headers[1:]
    _, last = _sheet_table(ws, headers, rows, money_cols=money, start_row=4,
                           widths={h: 16 for h in money} | {"Month": 14})
    totals = {h: sum(r[i] for r in rows) for i, h in enumerate(headers) if i and h != "Running Balance"}
    _total_row(ws, last + 1, headers, "Total", totals)


def _collections_sheet(ws, cols):
    headers = ["Collection", "Date", "Service", "Month", "Status", "Counted in Statement",
               "Tithes - Cash", "Tithes - Cashless", "Offering - Cash", "Offering - Cashless",
               "Mission - Cash", "Mission - Cashless", "Benevolence - Cash", "Benevolence - Cashless",
               "Loose - Cash", "Loose - Cashless", "Sunday School - Cash",
               "Total Cash", "Total Cashless", "Grand Total",
               "General Fund", "Mission Fund", "Benevolence Fund",
               "Cash Counted (Tally)", "Cash Over / (Short)",
               "# Tithes Envelopes", "# Offering Envelopes", "# Mission Envelopes",
               "Attendees", "Journal Entry", "Cost Center", "Amended From"]
    rows = []
    for c in cols:
        rows.append([
            c.name, c.dt, c.service, c.month, c.status,
            "Yes" if c.counted else f"No ({c.status.lower()})",
            _f(c.tithes_total), _f(c.tithes_total_cls), _f(c.offering_total), _f(c.offering_total_cls),
            _f(c.mission_total), _f(c.mission_total_cls), _f(c.benevolence_collection), _f(c.benevolence_collection_cls),
            _f(c.loose_collection), _f(c.loose_collection_cls), _f(c.sunday_school_collection),
            _f(c.grand_total), _f(c.grand_total_cls), _f(c.grand_total) + _f(c.grand_total_cls),
            c.funds["General"], c.funds["Mission"], c.funds["Benevolence"],
            _f(c.tally_total), _f(c.cash_grand_total_difference),
            (c.no_of_tithes or 0) + (c.no_of_tithes_cls or 0),
            (c.no_of_offering or 0) + (c.no_of_offering_cls or 0),
            (c.no_of_mission or 0) + (c.no_of_mission_cls or 0),
            c.attendees or 0, c.journal_entry or "", c.cost_center or "", c.amended_from or "",
        ])
    money = headers[6:25]
    _, last = _sheet_table(ws, headers, rows, money_cols=money, datetime_cols=["Date"],
                           status_cols=["Status"], muted_when=lambda r: r[5] != "Yes",
                           widths={"Collection": 22, "Date": 17, "Counted in Statement": 15,
                                   "Journal Entry": 20, "Cost Center": 18} | {h: 14 for h in money})
    for label, keep, r in (("Total — Submitted (counted)", lambda x: x[5] == "Yes", last + 2),
                           ("Total — Drafts (not counted)", lambda x: x[4] == "Draft", last + 3)):
        _total_row(ws, r, headers, label, {h: sum(x[headers.index(h)] for x in rows if keep(x)) for h in money})


def _disbursements_sheet(ws, items):
    headers = ["Disbursement", "Month", "Document Status", "Section", "Due Date", "Fund", "Source Account",
               "Purpose", "Department", "Payee / Worker", "Description", "Remarks",
               "Original Amount (before edit)", "Amount", "Claim Status", "Received By", "Received Date",
               "Days Overdue", "Counted in Statement", "Paid By", "Creditor", "Date Creditor Paid", "Payable",
               "Void Reason", "Line ID"]
    lines = [i for i in items if i.kind == "line"]
    rows = [[i.disbursement, i.month, i.doc_status, i.section, i.due, i.fund, i.source or "",
             i.purpose or "", i.department or "", i.payee or "", i.description or "", i.remarks or "",
             i.original, i.amount, i.claim_status, i.received_by or "", i.received_date,
             i.days_overdue, i.counted_label, i.paid_by, i.creditor or "", i.creditor_paid_date,
             i.payable or "", i.void_reason or "", i.row_name] for i in lines]
    _, last = _sheet_table(ws, headers, rows, money_cols=["Original Amount (before edit)", "Amount"],
                           date_cols=["Due Date", "Received Date", "Date Creditor Paid"],
                           status_cols=["Claim Status"],
                           muted_when=lambda r: r[18].startswith("No"),
                           widths={"Disbursement": 16, "Section": 20, "Source Account": 26, "Purpose": 20,
                                   "Department": 18, "Payee / Worker": 22, "Description": 34, "Remarks": 28,
                                   "Received By": 22, "Due Date": 12, "Received Date": 12,
                                   "Counted in Statement": 18, "Amount": 14, "Creditor": 26, "Void Reason": 30})
    live = [i for i in lines if i.counted]
    voided = [i for i in lines if i.voided and i.docstatus != 2]
    for label, keep, r, pool in (("Total — Claimed, paid by church", lambda i: i.cash_out, last + 2, live),
                                 ("Total — Claimed, paid by creditor", lambda i: i.creditor_paid, last + 3, live),
                                 ("Total — Unclaimed (pending)", lambda i: i.pending, last + 4, live),
                                 ("Total — All committed", lambda i: True, last + 5, live),
                                 ("Voided (not counted)", lambda i: True, last + 6, voided)):
        _total_row(ws, r, headers, label, {"Amount": sum(i.amount for i in pool if keep(i))})


def _payables_rows(year):
    """Every creditor payable and reimbursement relevant to the year, as flat
    rows. Payables: posted in the year, or posted earlier and still owed at
    the start of it. Outstanding is as of 31 December of the year."""
    start, end = f"{year}-01-01", f"{year}-12-31"
    if not fin.schema_ready():
        return []
    pays = frappe.get_all("Creditor Payable", filters={"posting_date": ["<=", end], "docstatus": [">", 0]},
        fields=["name", "docstatus", "status", "posting_date", "creditor", "fund", "purpose", "department",
                "description", "source_type", "disbursement", "section", "reference", "amount"],
        order_by="posting_date asc, name asc")
    owed_end = cred.outstanding_as_of(end, [p.name for p in pays if p.docstatus == 1])
    owed_start = cred.outstanding_as_of(f"{year - 1}-12-31", [p.name for p in pays if p.docstatus == 1])
    rows = []
    for p in pays:
        in_year = getdate(p.posting_date).year == year
        if not in_year and owed_start.get(p.name, 0) <= 0.005:
            continue
        d = getdate(p.posting_date)
        rows.append({"type": "Payable", "document": p.name, "status": p.status, "date": d,
                     "month": MONTH_NAMES[d.month - 1] if in_year else None,
                     "creditor": p.creditor, "fund": p.fund, "purpose": p.purpose, "department": p.department,
                     "description": p.description, "recorded_from": p.source_type, "disbursement": p.disbursement or "",
                     "section": p.section or "", "payable": p.name, "paid_from": "", "received_by": "",
                     "reference": p.reference or "", "amount": _f(p.amount), "reimbursed": 0.0,
                     "outstanding": owed_end.get(p.name) if p.docstatus == 1 else None,
                     "counted": p.docstatus == 1,
                     "counted_label": "Yes" if p.docstatus == 1 else "No (cancelled)"})
    reimbs = frappe.db.sql("""
        select r.name, r.docstatus, r.posting_date, r.creditor, r.fund, r.source_account, r.received_by,
               r.reference, a.payable, a.amount, p.description, p.purpose, p.department
        from `tabCreditor Reimbursement` r
        join `tabCreditor Reimbursement Allocation` a on a.parent = r.name
        left join `tabCreditor Payable` p on p.name = a.payable
        where r.docstatus > 0 and r.posting_date between %s and %s
        order by r.posting_date, r.name, a.idx""", (start, end), as_dict=True)
    for r in reimbs:
        d = getdate(r.posting_date)
        rows.append({"type": "Reimbursement", "document": r.name, "status": "Submitted" if r.docstatus == 1 else "Cancelled",
                     "date": d, "month": MONTH_NAMES[d.month - 1], "creditor": r.creditor, "fund": r.fund,
                     "purpose": r.purpose, "department": r.department, "description": r.description,
                     "recorded_from": "", "disbursement": "", "section": "", "payable": r.payable,
                     "paid_from": r.source_account, "received_by": r.received_by, "reference": r.reference or "",
                     "amount": 0.0, "reimbursed": _f(r.amount), "outstanding": None,
                     "counted": r.docstatus == 1, "counted_label": "Yes" if r.docstatus == 1 else "No (cancelled)"})
    rows.sort(key=lambda x: (x["date"], 0 if x["type"] == "Payable" else 1, x["document"]))
    return rows


def _payables_sheet(ws, year, rows):
    headers = ["Type", "Document", "Status", "Date", "Creditor", "Fund", "Purpose", "Department", "Description",
               "Recorded From", "Disbursement", "Section", "Payable", "Paid From Account", "Received By",
               "Reference", "Amount Owed", "Reimbursed", "Outstanding (31 Dec)", "Counted in Statement"]
    ws["A1"] = f"Creditor payables and reimbursements {year}"
    ws["A1"].font = TITLE_FONT
    ws["A2"] = ("Payable = an expense a creditor paid for us (counted as an expense, no church cash moved). "
                "Reimbursement = church money paid back from the account shown, on that date. Kept outside the GL, like claims.")
    ws["A2"].font = MUTED
    data = [[r["type"], r["document"], r["status"], r["date"], r["creditor"], r["fund"], r["purpose"] or "",
             r["department"] or "", r["description"] or "", r["recorded_from"], r["disbursement"], r["section"],
             r["payable"], r["paid_from"], r["received_by"], r["reference"], r["amount"], r["reimbursed"],
             r["outstanding"], r["counted_label"]] for r in rows]
    _, last = _sheet_table(ws, headers, data, money_cols=["Amount Owed", "Reimbursed", "Outstanding (31 Dec)"],
                           date_cols=["Date"], status_cols=["Status"], start_row=4,
                           muted_when=lambda r: r[-1].startswith("No"),
                           widths={"Creditor": 30, "Description": 32, "Paid From Account": 24, "Document": 18})
    live = [r for r in rows if r["counted"]]
    _total_row(ws, last + 2, headers, "Total — counted",
               {"Amount Owed": sum(r["amount"] for r in live), "Reimbursed": sum(r["reimbursed"] for r in live),
                "Outstanding (31 Dec)": sum(r["outstanding"] or 0 for r in live)})


def _fund_summary_sheet(ws, fsum):
    fs = fsum
    ws["A1"] = f"Fund Summary — {fs['period']}"
    ws["A1"].font = TITLE_FONT
    ws["A2"] = ("Collections = active GL postings on each fund's cash and cashless accounts (combined; White Gift all years). "
                f"Disbursements = committed (Claimed + Unclaimed, Voided excluded). Monthly average = amount ÷ {fs['months']} month(s).")
    ws["A2"].font = MUTED
    row = 4
    c, d = fs["collections"], fs["disbursements"]
    order = ("Mission", "Benevolence", "White Gift", "General")
    pairs = [("TOTAL COLLECTIONS", c["total"])] + [(f"   {f} Fund", c["by_fund"][f]) for f in order]
    pairs += [("TOTAL DISBURSEMENTS", d["total"])] + [(f"   {f} Disbursements", d["by_fund"][f]) for f in order]
    pairs += [(f"      {p}", v) for p, v in d["general_by_purpose"].items()]
    pairs += [("SURPLUS / (DEFICIT)", fs["surplus"])]
    row = _kv_block(ws, row, "Summary", [(k, float(v)) for k, v in pairs])

    fund_rows = [[f["fund"], f["collections"], f["disbursements"], f["balance"], f["avg_collections"],
                  f["avg_disbursements"], f["avg_balance"]] for f in fs["funds"]]
    fund_rows.append(["Total"] + [sum(r[k] for r in fund_rows) for k in range(1, 7)])
    row = _grid_block(ws, row, "Per fund", ["Fund", "Collections", "Disbursements", "Balance",
                      "Avg collections / month", "Avg disbursements / month", "Avg balance / month"], fund_rows)

    pos_rows = [[f["fund"], f["collections"], f["paid_out"], f["cash_balance"], f["pending"], f["owed"],
                 f["after_pending_and_payables"]] for f in fs["funds"]]
    pos_rows.append(["Total"] + [sum(r[k] for r in pos_rows) for k in range(1, 7)])
    row = _grid_block(ws, row, "Where each fund's balance sits", ["Fund", "Collections", "Paid out (church money)",
                      "Cash balance", "Pending claims", "Owed to creditors", "After pending & payables"], pos_rows,
                      note="Paid out = claimed lines paid by the church + reimbursements to creditors in the period.")

    dept_rows = []
    for dd in fs["by_department"]:
        dept_rows.append([dd["department"], "", dd["total"]])
        dept_rows += [["", p, v] for p, v in dd["purposes"].items()]
    dept_rows.append(["Total", "", sum(dd["total"] for dd in fs["by_department"])])
    row = _grid_block(ws, row, "Disbursement per department", ["Department", "Purpose", "Amount"], dept_rows, money_from=2)

    purp_rows = [[p, v] for p, v in fs["by_purpose"].items()] + [["Total", sum(fs["by_purpose"].values())]]
    row = _grid_block(ws, row, "Disbursement per purpose", ["Purpose", "Amount"], purp_rows)

    ws.cell(row=row, column=1, value="Comments").font = SECTION_FONT
    row += 1
    for f in order:
        text = (fs.get("comments") or {}).get(f, {}).get("comments") or "—"
        ws.cell(row=row, column=1, value=f"For {f}").font = BOLD
        cell = ws.cell(row=row, column=2, value=text)
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=7)
        ws.row_dimensions[row].height = max(15, 15 * (text.count("\n") + 1))
        row += 1
    ws.column_dimensions["A"].width = 40
    for col in "BCDEFG":
        ws.column_dimensions[col].width = 20


def _audit_rows(year):
    if not fin.schema_ready():
        return []
    rows = frappe.db.sql("""
        select timestamp, user_name, action, disbursement, month, section, line_label, row_name, amount,
               summary, reason, reference_doctype, reference_name
        from `tabDisbursement Audit Log`
        where year = %(y)s or (year is null and year(timestamp) = %(y)s)
        order by timestamp, creation""", {"y": year}, as_dict=True)
    return rows


def _audit_sheet(ws, year, rows):
    headers = ["When", "User", "Action", "Disbursement", "Month", "Section", "Line", "Line ID",
               "Line Amount (after)", "Change (before → after)", "Reason", "Reference"]
    ws["A1"] = f"Disbursement audit log {year}"
    ws["A1"].font = TITLE_FONT
    ws["A2"] = "Append-only record of every change to a disbursement line, payable or reimbursement. Nobody can edit or delete entries."
    ws["A2"].font = MUTED
    data = [[r.timestamp, r.user_name, r.action, r.disbursement or "", r.month or "", r.section or "",
             r.line_label or "", r.row_name or "", _f(r.amount) if r.amount is not None else None,
             r.summary or "", r.reason or "",
             f"{r.reference_doctype}: {r.reference_name}" if r.reference_name else ""] for r in rows]
    _sheet_table(ws, headers, data, money_cols=["Line Amount (after)"], datetime_cols=["When"], start_row=4,
                 widths={"When": 17, "User": 20, "Action": 16, "Line": 28, "Change (before → after)": 50,
                         "Reason": 40, "Reference": 30, "Line ID": 12})
    for r in range(5, 5 + len(data)):
        for c in (10, 11):
            ws.cell(row=r, column=c).alignment = Alignment(wrap_text=True, vertical="top")


def _ledger_sheet(ws, rows):
    headers = ["Posting Date", "Account", "Statement Account", "Fund", "Debit", "Credit", "Net (Dr − Cr)",
               "Voucher Type", "Voucher No", "Source Document", "Status", "Counted in Statement", "Remarks"]
    ws["A1"] = "GL postings behind the statement's ledger balances"
    ws["A1"].font = TITLE_FONT
    ws["A2"] = ("Debits to the cash/cashless accounts from submitted collections (and any other journal entries). "
                "Claimed disbursements are not posted to the GL yet; the statement deducts them separately.")
    ws["A2"].font = MUTED
    _, last = _sheet_table(ws, headers, rows, money_cols=["Debit", "Credit", "Net (Dr − Cr)"],
                           date_cols=["Posting Date"], status_cols=["Status"], start_row=4,
                           muted_when=lambda r: r[10] == "Cancelled",
                           widths={"Posting Date": 12, "Account": 26, "Statement Account": 20, "Voucher No": 20,
                                   "Source Document": 22, "Counted in Statement": 16, "Remarks": 40})
    active = [r for r in rows if r[10] == "Active"]
    _total_row(ws, last + 2, headers, "Total — Active postings",
               {"Debit": sum(r[4] for r in active), "Credit": sum(r[5] for r in active),
                "Net (Dr − Cr)": sum(r[6] for r in active)})


# ---------------------------------------------------------------- entry

def build_workbook(year, month=None):
    year = int(year)
    month = month if month in MONTH_NAMES else None

    st = _statement(year)
    cols = _collections(year)
    items = _disbursement_items(year)
    payables = _payables_rows(year)
    ledger = _ledger(st, year)
    # Fund Summary: January to the end of the chosen month; for the whole
    # year, to December — or, while the year is still running, to the end
    # of the current month (so averages divide by the months that happened)
    today = getdate(nowdate())
    end_m = (MONTH_NAMES.index(month) + 1) if month else (today.month if year == today.year else 12)
    fs_to = f"{year}-{end_m:02d}-{calendar.monthrange(year, end_m)[1]:02d}"
    fsum = fund_summary.compute(f"{year}-01-01", fs_to)
    audit_rows = _audit_rows(year)
    if month:
        m_idx = MONTH_NAMES.index(month) + 1
        cols_detail = [c for c in cols if c.month == month]
        items_detail = [i for i in items if i.month == month]
        payables_detail = [r for r in payables if r["month"] == month]
        ledger = [r for r in ledger if r[0].year == year and r[0].month == m_idx]
        audit_detail = [r for r in audit_rows if r.month == month]
    else:
        cols_detail, items_detail, payables_detail, audit_detail = cols, items, payables, audit_rows

    wb = Workbook()
    _summary_sheet(wb.active, year, month, st, cols_detail, items_detail, payables_detail)
    wb.active.title = "Summary"
    _cash_flow_sheet(wb.create_sheet("Monthly Cash Flow"), year, cols, items, payables)
    _collections_sheet(wb.create_sheet("Collections"), cols_detail)
    _disbursements_sheet(wb.create_sheet("Disbursements"), items_detail)
    _ledger_sheet(wb.create_sheet("Ledger Postings"), ledger)
    _fund_summary_sheet(wb.create_sheet("Fund Summary"), fsum)
    _payables_sheet(wb.create_sheet("Payables"), year, payables_detail)
    _audit_sheet(wb.create_sheet("Audit Log"), year, audit_detail)
    for ws in wb.worksheets:
        ws.sheet_view.zoomScale = 90
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True

    buf = io.BytesIO()
    wb.save(buf)
    filename = f"JBC_Financial_Statement_{year}{'_' + month if month else ''}.xlsx"
    return buf.getvalue(), filename
