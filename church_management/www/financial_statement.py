import calendar
import json
from datetime import date, timedelta

import frappe
from frappe.utils import getdate, nowdate


def _sundays(year, month):
    first = date(year, month, 1)
    d = first + timedelta(days=(6 - first.weekday()) % 7)
    out = []
    while d.month == month:
        out.append(d)
        d += timedelta(days=7)
    return out


def _due_date(year, month_idx, field):
    """Week N items fall due on the month's Nth Sunday; monthly items by month end."""
    if field.startswith(('disbursement_item_week_', 'expense_item_week_')):
        suns = _sundays(year, month_idx)
        w = int(field.rsplit('_', 1)[1])
        if w <= len(suns):
            return suns[w - 1]
    return date(year, month_idx, calendar.monthrange(year, month_idx)[1])


def _require_admin():
    """The financial statement is internal — System Manager (admin) only."""
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/financial_statement"
        raise frappe.Redirect
    if "System Manager" not in frappe.get_roles():
        frappe.throw(
            frappe._("You are not permitted to view the financial statement."),
            frappe.PermissionError,
        )


def get_context(context):
    _require_admin()
    context.no_cache = 1

    # 1. Filters Setup
    selected_year = frappe.form_dict.get('year', '2026')
    selected_month = frappe.form_dict.get('month', '')
    group_by = frappe.form_dict.get('group_by', 'Source')

    month_names = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    if selected_month not in month_names:
        selected_month = ''
    if group_by not in ('Source', 'Purpose', 'Department'):
        group_by = 'Source'
    
    # Initialize basic context
    res = {
        'selected_year': selected_year,
        'available_years': ['2026'],
        'selected_month': selected_month,
        'group_by': group_by,
        'group_options': ['Source', 'Purpose', 'Department'],
        'financial_summary': {
            'cash_collected': 0.0,
            'cashless_collected': 0.0,
            'total_disbursed': 0.0,
            'total_unclaimed': 0.0,
            'funds': {
                'General': {'collected': 0.0, 'disbursed': 0.0, 'unclaimed': 0.0},
                'Mission': {'collected': 0.0, 'disbursed': 0.0, 'unclaimed': 0.0},
                'Benevolence': {'collected': 0.0, 'disbursed': 0.0, 'unclaimed': 0.0},
                'White Gift': {'collected': 0.0, 'disbursed': 0.0, 'unclaimed': 0.0}
            }
        },
        'monthly_data': [],
        'account_balances': [],
        'fund_cards': [],
        'spend': None,
        'outlook': None,
        'position': {'cash': 0.0, 'cashless': 0.0, 'unassigned': 0.0, 'available': 0.0,
                     'white_gift': 0.0, 'unclaimed_operating': 0.0, 'projected': 0.0},
        'available_months': [],
        'trend': [],
        'trend_json': '[]',
        'purpose_totals': [],
        'purpose_json': '{}',
        'insights': []
    }

    try:
        settings = frappe.get_single("Church Management Settings")
        
        cols_query = frappe.get_all('Collection',
            fields=['name', 'date', 'grand_total', 'grand_total_cls', 'tithes_total', 'mission_total', 'offering_total', 'benevolence_collection', 'loose_collection', 'sunday_school_collection',
                    'tithes_total_cls', 'mission_total_cls', 'offering_total_cls', 'benevolence_collection_cls', 'loose_collection_cls'],
            filters=[['Collection', 'date', '>=', f'{selected_year}-01-01'], ['Collection', 'date', '<=', f'{selected_year}-12-31'], ['Collection', 'docstatus', '=', 1]])
        
        disb_query = frappe.get_all('Disbursement', fields=['name', 'month_recorded', 'year_recorded'], filters={'year_recorded': selected_year, 'docstatus': ['<', 2]})
        
        active_months = set()
        for c in cols_query:
            if c.date: active_months.add(month_names[getdate(c.date).month - 1])
        for d in disb_query:
            active_months.add(d.month_recorded)
        res['available_months'] = sorted(list(active_months), key=lambda x: month_names.index(x))
        
        fs = res['financial_summary']
        account_deductions = {}
        account_unclaimed = {}
        unclaimed_by_month = {}
        claimed_by_purpose = {}
        unclaimed_by_purpose = {}
        # General (usable) fund flows per month, for the spendable-money trend
        gen_in_by_month, gen_claimed_by_month, gen_unclaimed_by_month = {}, {}, {}
        # General pending split by when it falls due, relative to today
        today = getdate(nowdate())
        year_int = int(selected_year)
        gen_due_now = 0.0
        gen_due_later = {}  # month_name -> amount not yet due
        gen_service_days = set()

        for c in cols_query:
            # General Fund = Tithes + Offering + Loose + Sunday School
            general_in = (
                (c.tithes_total or 0) + (c.tithes_total_cls or 0) +
                (c.offering_total or 0) + (c.offering_total_cls or 0) +
                (c.loose_collection or 0) + (c.loose_collection_cls or 0) +
                (c.sunday_school_collection or 0)
            )
            fs['funds']['General']['collected'] += general_in
            if c.date:
                c_month = month_names[getdate(c.date).month - 1]
                gen_in_by_month[c_month] = gen_in_by_month.get(c_month, 0.0) + general_in
                if general_in:
                    gen_service_days.add(getdate(c.date))
            fs['funds']['Mission']['collected'] += (c.mission_total or 0) + (c.mission_total_cls or 0)
            fs['funds']['Benevolence']['collected'] += (c.benevolence_collection or 0) + (c.benevolence_collection_cls or 0)
            fs['cash_collected'] += c.grand_total or 0.0
            fs['cashless_collected'] += c.grand_total_cls or 0.0

        # White Gift collected = cumulative GL balance (separate doctype, not in Collection)
        for wg_acc in [settings.white_gift_cash_account, settings.white_gift_cashless_account]:
            if wg_acc:
                wg_bal = frappe.db.sql(
                    "SELECT COALESCE(sum(debit)-sum(credit),0) FROM `tabGL Entry` "
                    "WHERE account=%s AND is_cancelled=0", wg_acc
                )[0][0] or 0.0
                fs['funds']['White Gift']['collected'] += wg_bal

        # Pre-process all disbursements once for deductions and fund summary
        disb_items_by_month = {}  # month_name -> list of (item_dict, disb_name)
        for d in disb_query:
            doc = frappe.get_doc('Disbursement', d.name)
            fields = [f'{t}_{w}' for w in range(1, 6) for t in ('disbursement_item_week', 'expense_item_week')]
            fields += ['monthly_expense_items', 'monthly_disbursement_items']
            d_month_idx = month_names.index(d.month_recorded) + 1 if d.month_recorded in month_names else None

            for field, item in ((f, it) for f in fields for it in (doc.get(f) or [])):
                amt = item.get('amount') or 0.0
                purp, src = item.get('purpose'), item.get('source')
                # Map amounts to funds by source account.
                # Items without a source fall into General so fund totals reconcile with total_disbursed.
                src_lower = (src or '').lower()
                if 'white gift' in src_lower: mapped_fund = 'White Gift'
                elif 'mission' in src_lower: mapped_fund = 'Mission'
                elif 'benevolence' in src_lower: mapped_fund = 'Benevolence'
                else: mapped_fund = 'General'

                purp_key = purp or 'No Purpose'
                if item.get('status') != 'Claimed':
                    # Committed but not yet claimed — money already promised out.
                    # Feeds the projected view; excluded from claimed totals below.
                    fs['funds'][mapped_fund]['unclaimed'] += amt
                    fs['total_unclaimed'] += amt
                    unclaimed_by_month[d.month_recorded] = unclaimed_by_month.get(d.month_recorded, 0.0) + amt
                    unclaimed_by_purpose[purp_key] = unclaimed_by_purpose.get(purp_key, 0.0) + amt
                    account_unclaimed[src or ''] = account_unclaimed.get(src or '', 0.0) + amt
                    if mapped_fund == 'General':
                        gen_unclaimed_by_month[d.month_recorded] = gen_unclaimed_by_month.get(d.month_recorded, 0.0) + amt
                        if d_month_idx and _due_date(year_int, d_month_idx, field) > today:
                            gen_due_later[d.month_recorded] = gen_due_later.get(d.month_recorded, 0.0) + amt
                        else:
                            gen_due_now += amt
                    continue

                claimed_by_purpose[purp_key] = claimed_by_purpose.get(purp_key, 0.0) + amt
                account_deductions[src or ''] = account_deductions.get(src or '', 0.0) + amt
                fs['funds'][mapped_fund]['disbursed'] += amt
                fs['total_disbursed'] += amt
                if mapped_fund == 'General':
                    gen_claimed_by_month[d.month_recorded] = gen_claimed_by_month.get(d.month_recorded, 0.0) + amt
                # Store for monthly breakdown. Allowance rows have no description field —
                # fall back to remarks, then purpose + worker.
                worker = item.get('worker')
                fallback = f"{purp} — {worker}" if (purp and worker) else (purp or worker)
                disb_items_by_month.setdefault(d.month_recorded, []).append({
                    'amount': amt, 'source': src, 'purpose': purp,
                    'description': item.get('description') or item.get('remarks') or fallback or "No Description",
                    'received_date': item.get('received_date'),
                    'received_by': item.get('received_by'),
                    'department': item.get('department')
                })

        # Whole-year trend: collections vs disbursements (claimed + unclaimed)
        # per month. Deliberately ignores the month filter — the trend chart
        # always shows the full year so planning has the complete picture.
        g_running = 0.0
        for m in res['available_months']:
            m_idx = month_names.index(m) + 1
            g_in = gen_in_by_month.get(m, 0.0)
            g_claimed = gen_claimed_by_month.get(m, 0.0)
            g_unclaimed = gen_unclaimed_by_month.get(m, 0.0)
            # Running "free to spend" General balance: income minus every
            # commitment so far, claimed or not
            g_running += g_in - g_claimed - g_unclaimed
            res['trend'].append({
                'g_collections': g_in,
                'g_claimed': g_claimed,
                'g_unclaimed': g_unclaimed,
                'g_free': g_running,
                'month': m,
                'collections': sum(
                    (c.grand_total or 0.0) + (c.grand_total_cls or 0.0)
                    for c in cols_query if c.date and getdate(c.date).month == m_idx
                ),
                'claimed': sum(i['amount'] for i in disb_items_by_month.get(m, [])),
                'unclaimed': unclaimed_by_month.get(m, 0.0),
            })
        res['trend_json'] = json.dumps(res['trend'])

        # Allotment breakdown: total committed (claimed + unclaimed) per
        # purpose for the whole year, largest first — shows which allotment
        # takes the most and where a budget adjustment moves the needle.
        purpose_rows = []
        for p in set(claimed_by_purpose) | set(unclaimed_by_purpose):
            c = claimed_by_purpose.get(p, 0.0)
            u = unclaimed_by_purpose.get(p, 0.0)
            purpose_rows.append({'purpose': p, 'claimed': c, 'unclaimed': u, 'total': c + u})
        purpose_rows.sort(key=lambda r: -r['total'])
        res['purpose_totals'] = purpose_rows

        grand_committed = sum(r['total'] for r in purpose_rows)
        # The chart caps at 8 purposes + "Other"; the table keeps the full list.
        chart_rows = purpose_rows
        if len(purpose_rows) > 9:
            head, tail = purpose_rows[:8], purpose_rows[8:]
            chart_rows = head + [{
                'purpose': 'Other',
                'claimed': sum(r['claimed'] for r in tail),
                'unclaimed': sum(r['unclaimed'] for r in tail),
                'total': sum(r['total'] for r in tail),
            }]
        res['purpose_json'] = json.dumps({
            'rows': chart_rows,
            'grand': grand_committed,
            'months': len(res['trend']) or 1,
        })

        # Rule-based planning insights — deterministic advice from this
        # year's numbers, recomputed on every load.
        insights = []
        n_months = len(res['trend'])
        total_coll_ytd = sum(t['collections'] for t in res['trend'])
        if purpose_rows and grand_committed and n_months:
            top = purpose_rows[0]
            share = top['total'] / grand_committed * 100
            per_month = top['total'] / n_months
            insights.append(
                f"{top['purpose']} is the largest allotment: ₱{top['total']:,.0f} "
                f"({share:.0f}% of all {selected_year} commitments), averaging ₱{per_month:,.0f} per month. "
                f"A 10% trim here frees about ₱{top['total'] * 0.1:,.0f} a year — more than most smaller allotments cost in total."
            )
            if len(purpose_rows) >= 3:
                top3 = sum(r['total'] for r in purpose_rows[:3])
                if top3 / grand_committed >= 0.7:
                    names = ", ".join(r['purpose'] for r in purpose_rows[:3])
                    insights.append(
                        f"Spending is concentrated: {names} together make up "
                        f"{top3 / grand_committed * 100:.0f}% of all commitments. Budget planning should start with these three."
                    )
            backlog = max(purpose_rows, key=lambda r: r['unclaimed'])
            if backlog['unclaimed'] > 0:
                insights.append(
                    f"{backlog['purpose']} carries the largest unclaimed backlog (₱{backlog['unclaimed']:,.0f}). "
                    f"Have these claimed — or release the ones no longer needed, which immediately improves the projected balance."
                )
            neg_months = [
                t for t in res['trend']
                if t['collections'] - t['claimed'] - t['unclaimed'] < 0
            ]
            if neg_months:
                worst = min(neg_months, key=lambda t: t['collections'] - t['claimed'] - t['unclaimed'])
                worst_gap = worst['collections'] - worst['claimed'] - worst['unclaimed']
                insights.append(
                    f"{len(neg_months)} of {n_months} months committed more than they collected "
                    f"(worst: {worst['month']}, short ₱{abs(worst_gap):,.0f}). "
                    f"Monthly collections average ₱{total_coll_ytd / n_months:,.0f} — keeping recurring allotments under that keeps every month funded."
                )
        res['insights'] = insights

        # Build monthly highlights
        months_to_process = [selected_month] if selected_month else res['available_months']
        for m in months_to_process:
            m_idx = month_names.index(m) + 1
            m_cols = [c for c in cols_query if getdate(c.date).month == m_idx]
            month_summary = {'month': m, 'cash_collected': 0.0, 'cashless_collected': 0.0, 'total_disbursed': 0.0, 'groups': {}}
            for c in m_cols:
                month_summary['cash_collected'] += c.grand_total or 0.0
                month_summary['cashless_collected'] += sum([c.tithes_total_cls or 0.0, c.mission_total_cls or 0.0, c.offering_total_cls or 0.0, c.benevolence_collection_cls or 0.0, c.loose_collection_cls or 0.0])

            for item in disb_items_by_month.get(m, []):
                amt = item['amount']
                src = item['source']
                month_summary['total_disbursed'] += amt
                grp = "Unknown"
                if group_by == 'Source': grp = src or 'Unknown Source'
                elif group_by == 'Purpose': grp = item['purpose'] or 'Unknown Purpose'
                elif group_by == 'Department': grp = item['department'] or 'Unknown Department'
                if grp not in month_summary['groups']: month_summary['groups'][grp] = {'total': 0.0, 'entries': []}
                month_summary['groups'][grp]['total'] += amt
                month_summary['groups'][grp]['entries'].append({
                    'description': item['description'], 'amount': amt,
                    'date': item['received_date'], 'received_by': item['received_by']
                })
            if month_summary['cash_collected'] > 0 or month_summary['cashless_collected'] > 0 or month_summary['total_disbursed'] > 0:
                res['monthly_data'].append(month_summary)

        # Build account balances using defined fund groups
        # General Cash/Cashless = combined ledger of Tithes+Offering+Loose+Sunday School
        # Deductions come from disbursement items where source matches the account
        def get_gl_balance(account_name, cumulative=False):
            if not account_name:
                return 0.0
            if cumulative:
                result = frappe.db.sql(
                    "SELECT COALESCE(sum(debit)-sum(credit),0) FROM `tabGL Entry` "
                    "WHERE account=%s AND is_cancelled=0",
                    account_name
                )
            else:
                result = frappe.db.sql(
                    "SELECT COALESCE(sum(debit)-sum(credit),0) FROM `tabGL Entry` "
                    "WHERE account=%s AND is_cancelled=0 "
                    "AND posting_date >= %s AND posting_date <= %s",
                    (account_name, f'{selected_year}-01-01', f'{selected_year}-12-31')
                )
            return result[0][0] if result else 0.0

        # Define display accounts: label -> (ledger accounts list, deduction source accounts list, cumulative flag)
        general_cash_ledger = [a for a in [
            settings.tithes_cash_account, settings.offering_cash_account,
            settings.loose_cash_account, settings.sunday_school_cash_account
        ] if a]
        general_cashless_ledger = [a for a in [
            settings.tithes_cashless_account, settings.offering_cashless_account,
            settings.loose_cashless_account
        ] if a]

        # kind drives the "where we stand" KPI cards: cash on hand, cashless, White Gift;
        # fund groups the accounts into the fund cards.
        display_accounts = [
            ('General Cash', general_cash_ledger, ['General Cash - JBC'] + general_cash_ledger, False, 'cash', 'General'),
            ('General Cashless', general_cashless_ledger, ['General Cashless - JBC'] + general_cashless_ledger, False, 'cashless', 'General'),
            ('Mission Cash', [settings.mission_cash_account], [settings.mission_cash_account], False, 'cash', 'Mission'),
            ('Mission Cashless', [settings.mission_cashless_account], [settings.mission_cashless_account], False, 'cashless', 'Mission'),
            ('Benevolence Cash', [settings.benevolence_cash_account], [settings.benevolence_cash_account], False, 'cash', 'Benevolence'),
            ('Benevolence Cashless', [settings.benevolence_cashless_account], [settings.benevolence_cashless_account], False, 'cashless', 'Benevolence'),
            ('White Gift Cash', [settings.white_gift_cash_account], [settings.white_gift_cash_account], True, 'white_gift', 'White Gift'),
            ('White Gift Cashless', [settings.white_gift_cashless_account], [settings.white_gift_cashless_account], True, 'white_gift', 'White Gift'),
        ]

        pos = res['position']
        matched_sources = set()
        for label, ledger_accounts, deduction_sources, cumulative, kind, fund in display_accounts:
            ledger_balance = sum(get_gl_balance(a, cumulative=cumulative) for a in ledger_accounts if a)
            deduction = sum(account_deductions.get(s, 0.0) for s in deduction_sources if s)
            pending = sum(account_unclaimed.get(s, 0.0) for s in set(deduction_sources) if s)
            matched_sources.update(s for s in deduction_sources if s)
            pos[kind] += ledger_balance - deduction
            if ledger_balance != 0 or deduction != 0 or pending != 0:
                # Per-ledger composition, e.g. General Cash = Tithes + Offering + Loose + Sunday School
                parts = [
                    {'name': a.rsplit(' - ', 1)[0], 'balance': get_gl_balance(a, cumulative=cumulative)}
                    for a in ledger_accounts if a
                ] if len(ledger_accounts) > 1 else []
                res['account_balances'].append({
                    'name': label,
                    'parts': parts,
                    'ledger_balance': ledger_balance,
                    'pending_deductions': deduction,
                    'effective_balance': ledger_balance - deduction,
                    'pending': pending,
                    'kind': kind,
                    'fund': fund,
                    'channel': 'cashless' if 'Cashless' in label else 'cash',
                })

        # Claimed items whose source is empty or matches no display account above —
        # shown so the table always reconciles with the fund summary totals.
        unmatched = sum(amt for src, amt in account_deductions.items() if src not in matched_sources)
        unmatched_pending = sum(amt for src, amt in account_unclaimed.items() if src not in matched_sources)
        if unmatched or unmatched_pending:
            res['account_balances'].append({
                'name': 'Unassigned Source',
                'ledger_balance': 0.0,
                'pending_deductions': unmatched,
                'effective_balance': -unmatched,
                'pending': unmatched_pending,
                'kind': 'unassigned',
                'fund': None,
                'is_unassigned': True
            })
        pos['unassigned'] = -unmatched

        # Available = every non-White-Gift account; projected subtracts the
        # operating (non-White-Gift) commitments still waiting to be claimed.
        pos['available'] = pos['cash'] + pos['cashless'] + pos['unassigned']
        pos['unclaimed_operating'] = fs['total_unclaimed'] - fs['funds']['White Gift']['unclaimed']
        pos['projected'] = pos['available'] - pos['unclaimed_operating']

        # Fund cards — the same ledger figures as the account table and the
        # "today" KPIs, grouped by fund, so all three sections reconcile.
        fund_cards = []
        for fund in ('General', 'Mission', 'Benevolence', 'White Gift'):
            accts = [a for a in res['account_balances'] if a.get('fund') == fund]
            received = sum(a['ledger_balance'] for a in accts)
            from_collections = received if fund == 'White Gift' else fs['funds'][fund]['collected']
            available = sum(a['effective_balance'] for a in accts)
            pending = fs['funds'][fund]['unclaimed']
            fund_cards.append({
                'name': fund,
                'received': received,
                'from_collections': from_collections,
                'other_postings': received - from_collections,
                'claimed': sum(a['pending_deductions'] for a in accts),
                'available': available,
                'cash': sum(a['effective_balance'] for a in accts if a['channel'] == 'cash'),
                'cashless': sum(a['effective_balance'] for a in accts if a['channel'] == 'cashless'),
                'pending': pending,
                'projected': available - pending,
                'overdrawn_accounts': [a['name'] for a in accts if a['effective_balance'] < 0],
            })
        res['fund_cards'] = fund_cards

        # What can actually be spent. Only the General fund is unrestricted —
        # Mission and Benevolence are set aside for their purpose, White Gift
        # is separate. Free to spend = General after its pending claims; the
        # comfortable amount keeps a reserve of RESERVE_WEEKS of General spending.
        RESERVE_WEEKS = 1
        gen = next(f for f in fund_cards if f['name'] == 'General')
        n_months = len(res['trend'])
        g_avg_in = sum(t['g_collections'] for t in res['trend']) / n_months if n_months else 0.0
        g_avg_out = sum(t['g_claimed'] + t['g_unclaimed'] for t in res['trend']) / n_months if n_months else 0.0
        reserve = g_avg_out * 12 / 52 * RESERVE_WEEKS
        spend = {
            'usable': gen['available'],
            'pending': gen['pending'],
            'free': gen['projected'],
            'reserve': reserve,
            'reserve_weeks': RESERVE_WEEKS,
            'comfortable': gen['projected'] - reserve,
            'avg_in': g_avg_in,
            'avg_out': g_avg_out,
            'avg_gap': g_avg_in - g_avg_out,
            'restricted': [f for f in fund_cards if f['name'] in ('Mission', 'Benevolence')],
        }
        res['spend'] = spend

        # Outlook: the shortfall above assumes every commitment is paid today,
        # but most of the not-yet-due ones are funded by Sundays still to come.
        # Expected income = average General income per service Sunday so far.
        # Months with no Disbursement yet are estimated at the average monthly
        # General commitment.
        services = len({d - timedelta(days=(d.weekday() + 1) % 7) for d in gen_service_days})
        per_sunday = sum(gen_in_by_month.values()) / services if services else 0.0
        recorded_today = today in gen_service_days

        def sundays_left(m_idx):
            return [d for d in _sundays(year_int, m_idx) if d > today or (d == today and not recorded_today)]

        outlook = None
        if year_int == today.year:
            cur = today.month
            cur_name = month_names[cur - 1]
            due_later_this_month = gen_due_later.get(cur_name, 0.0)
            exp_in_this_month = per_sunday * len(sundays_left(cur))
            after_due_now = spend['usable'] - gen_due_now
            end_of_month = after_due_now - due_later_this_month + exp_in_this_month

            forecast, running = [], end_of_month
            for m_idx in range(cur + 1, 13):
                m_name = month_names[m_idx - 1]
                has_doc = m_name in res['available_months']
                exp_in = per_sunday * len(_sundays(year_int, m_idx))
                exp_out = gen_due_later.get(m_name, 0.0) if has_doc else g_avg_out
                running += exp_in - exp_out
                forecast.append({'month': m_name, 'forecast': True, 'g_expected_in': exp_in,
                                 'g_expected_out': exp_out, 'estimated': not has_doc, 'g_forecast_free': running})
            year_end = running

            # Due now = unclaimed from past months + this month's weeks already passed
            due_now_this_month = gen_unclaimed_by_month.get(cur_name, 0.0) - due_later_this_month
            outlook = {
                'month': cur_name,
                'due_now': gen_due_now,
                'overdue_past': gen_due_now - due_now_this_month,
                'due_now_this_month': due_now_this_month,
                'after_due_now': after_due_now,
                'due_later_this_month': due_later_this_month,
                'sundays_left': len(sundays_left(cur)),
                'per_sunday': per_sunday,
                'exp_in_this_month': exp_in_this_month,
                'end_of_month': end_of_month,
                'year_end': year_end,
                'forecast': forecast,
                'comfortable': min(end_of_month, year_end) - reserve,
            }
            spend['comfortable'] = outlook['comfortable']

            # Trend: expected rest of this month, then forecast months
            for t in res['trend']:
                if t['month'] == cur_name:
                    t['g_expected_in'] = exp_in_this_month
                    t['g_forecast_free'] = end_of_month
            res['trend_json'] = json.dumps(res['trend'] + forecast)
        res['outlook'] = outlook

        # Position insights go first — they're about money on hand today.
        position_tips = []
        verb = "are" if sum(1 for f in spend['restricted'] if f['available']) > 1 else "is"
        restricted_txt = " and ".join(f"{f['name']} ₱{f['available']:,.0f}" for f in spend['restricted'] if f['available'])
        ol = outlook
        if ol and spend['free'] < 0:
            position_tips.append(
                f"The ₱{abs(spend['free']):,.0f} shortfall is a timing gap, not a hole: it assumes every General commitment is paid today. "
                f"Only ₱{ol['due_now']:,.0f} is due now, and Usable Funds (₱{spend['usable']:,.0f}) cover it with ₱{ol['after_due_now']:,.0f} left. "
                f"The other ₱{ol['due_later_this_month']:,.0f} falls due over the next {ol['sundays_left']} Sunday{'s' if ol['sundays_left'] != 1 else ''}, "
                f"when about ₱{ol['exp_in_this_month']:,.0f} more is expected — ending {ol['month']} near ₱{ol['end_of_month']:,.0f}"
                f" and the year near ₱{ol['year_end']:,.0f}."
                + (f" {restricted_txt} {verb} set aside and should not be used to bridge the gap." if restricted_txt else "")
            )
        elif spend['free'] >= 0:
            position_tips.append(
                f"Usable money is the General fund only: ₱{spend['usable']:,.0f}. After its ₱{spend['pending']:,.0f} of pending claims, "
                f"₱{spend['free']:,.0f} is free to spend."
                + (f" {restricted_txt} {verb} set aside and not part of this." if restricted_txt else "")
            )
        else:
            position_tips.append(
                f"There is no free money to spend right now. The General fund (₱{spend['usable']:,.0f}) is ₱{abs(spend['free']):,.0f} short "
                f"of its own ₱{spend['pending']:,.0f} in pending claims. Hold new commitments until collections catch up."
                + (f" {restricted_txt} {verb} set aside for {'their' if verb == 'are' else 'its'} purpose and should not cover this gap." if restricted_txt else "")
            )
        if ol:
            position_tips.append(
                f"Comfortable new spending for the rest of the year: ₱{max(ol['comfortable'], 0):,.0f}. That is the lower of the end-of-{ol['month']} "
                f"and year-end outlooks, minus a {RESERVE_WEEKS}-week reserve (₱{reserve:,.0f}). "
                f"The outlook assumes about ₱{ol['per_sunday']:,.0f} of General income per Sunday and ₱{g_avg_out:,.0f} of General commitments per month "
                f"for months not yet scheduled."
            )
        if ol and ol['overdue_past'] >= 1:
            position_tips.append(
                f"₱{ol['overdue_past']:,.0f} of General commitments from past months is still unclaimed. If they will still be paid, keep them; "
                f"if not, release them — each one released raises the free-to-spend balance."
            )
        if n_months:
            if spend['avg_gap'] < 0:
                position_tips.append(
                    f"General income averages ₱{g_avg_in:,.0f} a month, but General commitments average ₱{g_avg_out:,.0f} — "
                    f"₱{abs(spend['avg_gap']):,.0f} more goes out than comes in each month. Recurring allotments need to drop by about that much "
                    f"for the usable balance to stop shrinking."
                )
            else:
                position_tips.append(
                    f"General income averages ₱{g_avg_in:,.0f} a month against ₱{g_avg_out:,.0f} of commitments, so the usable balance grows by "
                    f"about ₱{spend['avg_gap']:,.0f} a month. That is the amount new recurring spending could take on without eating into savings."
                )
        for f in spend['restricted']:
            if f['projected'] < 0:
                position_tips.append(
                    f"The {f['name']} Fund cannot cover its own pending claims: ₱{f['available']:,.0f} available against "
                    f"₱{f['pending']:,.0f} pending leaves it ₱{abs(f['projected']):,.0f} short."
                )
        for a in res['account_balances']:
            if a.get('fund') and a['effective_balance'] < 0:
                position_tips.append(
                    f"{a['name']} is overdrawn by ₱{abs(a['effective_balance']):,.0f}: ₱{a['pending_deductions']:,.0f} was claimed from it "
                    f"but only ₱{a['ledger_balance']:,.0f} came in. Re-source those claims to the account that actually paid, or record the missing deposit."
                )
        stray = sum(f['other_postings'] for f in fund_cards if f['name'] in ('General', 'Benevolence'))
        if abs(stray) >= 1:
            position_tips.append(
                f"₱{stray:,.2f} in the General/Benevolence ledgers did not come from a submitted collection. "
                f"Check for journal entries left behind by deleted or cancelled collections — they inflate the usable balance."
            )
        wg = next(f for f in fund_cards if f['name'] == 'White Gift')
        if wg['received']:
            position_tips.append(
                f"White Gift has ₱{wg['available']:,.0f} left of ₱{wg['received']:,.0f} received "
                f"({wg['available'] / wg['received'] * 100:.0f}%). It is kept separate, so spending it doesn't affect operations."
            )
        res['insights'] = position_tips + res['insights']
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Financial Statement Error")
    
    context.update(res)
    return context

@frappe.whitelist()
def download_disbursements_excel(year):
    if "System Manager" not in frappe.get_roles():
        frappe.throw(
            frappe._("You are not permitted to download the financial statement."),
            frappe.PermissionError,
        )
    from frappe.utils.xlsxutils import make_xlsx
    disbursements = frappe.get_all('Disbursement', filters={'year_recorded': year, 'docstatus': ['<', 2]}, fields=['name', 'month_recorded'])
    data = [["Month", "Date", "Source", "Purpose", "Department", "Description/Remarks", "Received By", "Amount"]]
    for d in disbursements:
        doc = frappe.get_doc('Disbursement', d.name)
        items = []
        for w in range(1, 6):
            items.extend(doc.get(f'disbursement_item_week_{w}') or [])
            items.extend(doc.get(f'expense_item_week_{w}') or [])
        items.extend(doc.get('monthly_expense_items') or [])
        items.extend(doc.get('monthly_disbursement_items') or [])
        for item in items:
            if item.get('status') == 'Claimed':
                amt = item.get('amount') or 0.0
                desc = item.get('description') or item.get('remarks') or item.get('worker') or item.get('purpose') or ""
                data.append([d.month_recorded, item.get('received_date'), item.get('source'), item.get('purpose'), item.get('department'), desc, item.get('received_by'), amt])
    xlsx_file = make_xlsx(data, "Disbursements")
    frappe.response['filename'] = f"Disbursements_{year}.xlsx"
    frappe.response['filecontent'] = xlsx_file.getvalue()
    frappe.response['type'] = 'binary'
