import calendar
import json
from datetime import date, timedelta
from statistics import mean, median, pstdev

import frappe
from frappe.utils import getdate, nowdate


MONTH_NAMES = list(calendar.month_name)[1:]


def fund_for_source(src):
    """Fund a disbursement item draws from, by its source account.
    Items without a source fall into General so fund totals reconcile."""
    s = (src or '').lower()
    if 'white gift' in s:
        return 'White Gift'
    if 'mission' in s:
        return 'Mission'
    if 'benevolence' in s:
        return 'Benevolence'
    return 'General'


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


# Allotments that are people's livelihoods — never suggest a blunt cut.
SENSITIVE_PURPOSES = {'Allowance'}
LEVEL_ORDER = {'action': 0, 'watch': 1, 'good': 2, 'info': 3}


def _tip(level, title, text):
    """One planning insight. level: action | watch | good | info."""
    return {'level': level, 'title': title, 'text': text}


def _build_plan(months, income_by_month, purpose_by_month, overdue_by_purpose, next_year):
    """Per-allotment budget guide for the General (usable) fund.

    Looks only at completed months so a half-collected current month does not
    skew the averages. For each allotment it works out the usual monthly
    level, whether that level has moved in the last three months, which months
    were unusually big, and from that a suggested monthly budget for next year
    plus a plain-language suggestion.
    """
    n = len(months)
    if not n:
        return None
    incomes = [income_by_month.get(m, 0.0) for m in months]
    avg_in, typical_in = mean(incomes), median(incomes)
    # An unusually big month: more than double the usual level and at least 1% of income
    material = avg_in * 0.01
    recent_n = 3 if n >= 6 else 0

    rows = []
    for purpose, by_month in purpose_by_month.items():
        series = [by_month.get(m, 0.0) for m in months]
        total = sum(series)
        if total <= 0:
            continue
        avg = total / n
        active = [v for v in series if v > 0]
        usual = median(active)
        spikes = [
            {'month': m, 'amount': v, 'extra': v - usual}
            for m, v in zip(months, series)
            if v > usual * 2 and v - usual >= material
        ]
        spike_months = {s['month'] for s in spikes}
        normal = [v for m, v in zip(months, series) if v > 0 and m not in spike_months]
        regular = len(active) / n >= 0.8
        spread = (max(normal) - min(normal)) / usual if normal and usual else 0.0
        variation = pstdev(normal) / mean(normal) if len(normal) > 1 and mean(normal) else 0.0
        extras = sum(s['extra'] for s in spikes) / n

        before = now = change = None
        if regular and recent_n:
            # Medians, so one big month does not read as a trend
            before, now = median(series[:-recent_n]), median(series[-recent_n:])
            if before:
                change = (now - before) / before * 100
        moved = change is not None and abs(change) >= 15 and abs(now - before) >= material / 2

        share = avg / avg_in * 100 if avg_in else 0.0
        spike_txt = ", ".join(f"{s['month'][:3]} ₱{s['amount']:,.0f}" for s in spikes)
        if regular and spread <= 0.10 and not spikes:
            kind, action, label = 'Fixed', 'hold', 'Hold'
            suggested = active[-1]
            reason = f"Same amount every month (₱{suggested:,.0f}). Budget it as is — it only changes if the arrangement itself is renegotiated."
        elif not regular or variation > 0.5:
            kind, suggested = 'Irregular', avg
            if len(active) == 1:
                pattern = f"Only once so far (₱{active[0]:,.0f})"
            elif regular:
                pattern = f"Paid most months, but the amount swings from ₱{min(active):,.0f} to ₱{max(active):,.0f}"
            else:
                pattern = f"Comes and goes: {len(active)} of {n} months, from ₱{min(active):,.0f} to ₱{max(active):,.0f}"
            if avg < material:
                action, label = 'minor', 'Keep as is'
                reason = f"{pattern}. Small — setting aside ₱{avg:,.0f} a month covers it; no decision needed."
            else:
                action, label = 'envelope', 'Set a yearly budget'
                reason = (
                    f"{pattern}. Give it one yearly budget of about ₱{avg * 12:,.0f} (₱{avg:,.0f} set aside each month) "
                    f"and approve requests against that, so big months stop being a surprise."
                )
        else:
            kind = 'Recurring'
            base = now if moved else (mean(normal) if normal else avg)
            suggested = base + extras
            if moved and change > 0:
                action, label = 'review', 'Review — rising'
                reason = (
                    f"The usual month went from ₱{before:,.0f} to ₱{now:,.0f} in the last {recent_n} months ({change:+.0f}%). "
                    f"Confirm what changed before it is carried into {next_year} — at the new level it costs ₱{(now - before) * 12:,.0f} more a year."
                )
            elif moved:
                action, label = 'lower', 'Budget lower'
                reason = (
                    f"The usual month dropped from ₱{before:,.0f} to ₱{now:,.0f} in the last {recent_n} months ({change:+.0f}%). "
                    f"Budget {next_year} at the new level — that frees about ₱{(avg - suggested) * 12:,.0f} a year against this year's average."
                )
            elif purpose in SENSITIVE_PURPOSES:
                action, label = 'care', 'Hold — handle with care'
                reason = (
                    f"Takes {share:.0f}% of General income and has stayed level. Each 1% change is ₱{avg * 0.01:,.0f} a month, "
                    f"but this is people's support — phase any change and discuss it first. Add new recipients only within the monthly headroom."
                )
            else:
                action, label = 'hold', 'Hold'
                reason = f"Steady at about ₱{suggested:,.0f} a month. No change needed."
            if spikes:
                if action == 'hold':
                    action, label = 'spikes', 'Plan for the big months'
                    reason = f"Usually ₱{usual:,.0f} a month."
                reason += (
                    f" Bigger months: {spike_txt} — ₱{sum(s['extra'] for s in spikes):,.0f} extra over the year. "
                    f"The suggested budget sets aside ₱{extras:,.0f} a month for them."
                )
        suggested = round(suggested, -1)
        rows.append({
            'purpose': purpose, 'kind': kind, 'action': action, 'label': label, 'reason': reason,
            'avg': avg, 'total': total, 'share': share, 'months_active': len(active),
            'before': before, 'now': now, 'change': change if moved else None,
            'suggested': suggested, 'delta': suggested - avg,
            'overdue': overdue_by_purpose.get(purpose, 0.0),
            'sensitive': purpose in SENSITIVE_PURPOSES,
        })
    rows.sort(key=lambda r: -r['avg'])

    avg_out = sum(r['avg'] for r in rows)
    headroom = avg_in - avg_out
    headroom_pct = headroom / avg_in * 100 if avg_in else 0.0
    status = 'deficit' if headroom < 0 else ('tight' if headroom_pct < 5 else 'healthy')
    suggested_total = sum(r['suggested'] for r in rows)
    return {
        'months': n,
        'period': months[0] if n == 1 else f"{months[0]}–{months[-1]}",
        'next_year': next_year,
        'avg_in': avg_in, 'typical_in': typical_in, 'avg_out': avg_out,
        'headroom': headroom, 'headroom_pct': headroom_pct, 'status': status,
        'used_pct': avg_out / avg_in * 100 if avg_in else 0.0,
        'short_months': [m for m, v in zip(months, incomes) if v < sum(r_by.get(m, 0.0) for r_by in purpose_by_month.values())],
        'rows': rows,
        'suggested_total': suggested_total,
        'suggested_headroom': avg_in - suggested_total,
        'flexible': sum(r['avg'] for r in rows if r['kind'] != 'Fixed' and not r['sensitive']),
    }


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
        'plan': None,
        'plan_json': 'null',
        'insights': []
    }

    try:
        settings = frappe.get_single("Church Management Settings")
        
        cols_query = frappe.get_all('Collection',
            fields=['name', 'date', 'grand_total', 'grand_total_cls', 'tithes_total', 'mission_total', 'offering_total', 'benevolence_collection', 'loose_collection', 'sunday_school_collection',
                    'tithes_total_cls', 'mission_total_cls', 'offering_total_cls', 'benevolence_collection_cls', 'loose_collection_cls'],
            # `date` is a Datetime: use "< next Jan 1" so Dec 31 evening services count
            filters=[['Collection', 'date', '>=', f'{selected_year}-01-01'], ['Collection', 'date', '<', f'{int(selected_year) + 1}-01-01'], ['Collection', 'docstatus', '=', 1]])
        
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
        gen_overdue_by_purpose = {}  # unclaimed General items from months already past
        gen_service_days = set()
        # Planning guide inputs: General commitments per purpose per month,
        # 5th-week General items, and the set-aside funds' monthly flows
        gen_purpose_month = {}
        gen_week5 = {}
        side_in = {'Mission': {}, 'Benevolence': {}}
        side_out = {'Mission': {}, 'Benevolence': {}}

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
            mission_in = (c.mission_total or 0) + (c.mission_total_cls or 0)
            benev_in = (c.benevolence_collection or 0) + (c.benevolence_collection_cls or 0)
            fs['funds']['Mission']['collected'] += mission_in
            fs['funds']['Benevolence']['collected'] += benev_in
            if c.date:
                side_in['Mission'][c_month] = side_in['Mission'].get(c_month, 0.0) + mission_in
                side_in['Benevolence'][c_month] = side_in['Benevolence'].get(c_month, 0.0) + benev_in
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
                mapped_fund = fund_for_source(src)

                purp_key = purp or 'No Purpose'
                if mapped_fund == 'General':
                    by_m = gen_purpose_month.setdefault(purp_key, {})
                    by_m[d.month_recorded] = by_m.get(d.month_recorded, 0.0) + amt
                    if field.endswith('_week_5'):
                        gen_week5[d.month_recorded] = gen_week5.get(d.month_recorded, 0.0) + amt
                elif mapped_fund in side_out:
                    side_out[mapped_fund][d.month_recorded] = side_out[mapped_fund].get(d.month_recorded, 0.0) + amt
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
                            if d_month_idx and year_int == today.year and d_month_idx < today.month:
                                gen_overdue_by_purpose[purp_key] = gen_overdue_by_purpose.get(purp_key, 0.0) + amt
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

        # Averages use completed months only: the current month has all its
        # commitments on record but only part of its collections, which would
        # make every average look worse than it is.
        full = [t for t in res['trend'] if not (year_int == today.year and month_names.index(t['month']) + 1 >= today.month)]
        full = full or res['trend']
        full_months = [t['month'] for t in full]

        # Rule-based planning insights — deterministic advice from this
        # year's numbers, recomputed on every load.
        insights = []
        if purpose_rows and year_int != today.year:
            # Past years have no due-date outlook, so point at the backlog directly
            backlog = max(purpose_rows, key=lambda r: r['unclaimed'])
            if backlog['unclaimed'] > 0:
                insights.append(_tip('watch', f"{backlog['purpose']} has the largest unclaimed amount",
                    f"₱{backlog['unclaimed']:,.0f} is scheduled but was never claimed. Have it claimed — or release what is no longer needed."
                ))
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
                    # For the Excel export's ledger sheet
                    'ledgers': [a for a in ledger_accounts if a],
                    'cumulative': cumulative,
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
        n_months = len(full)
        g_avg_in = sum(t['g_collections'] for t in full) / n_months if n_months else 0.0
        g_avg_out = sum(t['g_claimed'] + t['g_unclaimed'] for t in full) / n_months if n_months else 0.0
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
            'avg_months': n_months,
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

        # Planning guide: per-allotment budget suggestions for the General fund
        plan = _build_plan(full_months, gen_in_by_month, gen_purpose_month, gen_overdue_by_purpose, year_int + 1)
        res['plan'] = plan

        # Position insights go first — they're about money on hand today.
        tips = []
        verb = "are" if sum(1 for f in spend['restricted'] if f['available']) > 1 else "is"
        restricted_txt = " and ".join(f"{f['name']} ₱{f['available']:,.0f}" for f in spend['restricted'] if f['available'])
        ol = outlook
        if ol and spend['free'] < 0:
            tips.append(_tip('watch' if ol['end_of_month'] >= 0 else 'action',
                f"Today's ₱{abs(spend['free']):,.0f} shortfall is a timing gap" if ol['end_of_month'] >= 0
                else f"The General fund is expected to end {ol['month']} short",
                f"The shortfall assumes every General commitment is paid today. "
                f"Only ₱{ol['due_now']:,.0f} is due now, and Usable Funds (₱{spend['usable']:,.0f}) cover it with ₱{ol['after_due_now']:,.0f} left. "
                f"The other ₱{ol['due_later_this_month']:,.0f} falls due over the next {ol['sundays_left']} Sunday{'s' if ol['sundays_left'] != 1 else ''}, "
                f"when about ₱{ol['exp_in_this_month']:,.0f} more is expected — ending {ol['month']} near ₱{ol['end_of_month']:,.0f}"
                f" and the year near ₱{ol['year_end']:,.0f}."
                + (f" {restricted_txt} {verb} set aside and should not be used to bridge the gap." if restricted_txt else "")
            ))
        elif spend['free'] >= 0:
            tips.append(_tip('good', f"₱{spend['free']:,.0f} is free to spend",
                f"Usable money is the General fund only: ₱{spend['usable']:,.0f}, less ₱{spend['pending']:,.0f} of pending claims."
                + (f" {restricted_txt} {verb} set aside and not part of this." if restricted_txt else "")
            ))
        else:
            tips.append(_tip('action', "No free money right now — hold new commitments",
                f"The General fund (₱{spend['usable']:,.0f}) is ₱{abs(spend['free']):,.0f} short "
                f"of its own ₱{spend['pending']:,.0f} in pending claims. Hold new commitments until collections catch up."
                + (f" {restricted_txt} {verb} set aside for {'their' if verb == 'are' else 'its'} purpose and should not cover this gap." if restricted_txt else "")
            ))
        if ol:
            roomy = ol['comfortable'] > 0
            tips.append(_tip('info' if roomy else 'watch',
                f"Comfortable new spending for the rest of {selected_year}: ₱{ol['comfortable']:,.0f}" if roomy
                else f"No room for extra spending in the rest of {selected_year}",
                f"The comfortable amount is the lower of the end-of-{ol['month']} and year-end outlooks, minus a {RESERVE_WEEKS}-week reserve (₱{reserve:,.0f}). "
                f"The outlook assumes about ₱{ol['per_sunday']:,.0f} of General income per Sunday and ₱{g_avg_out:,.0f} of General commitments "
                f"a month for months not yet scheduled."
            ))
        if ol and ol['overdue_past'] >= 1:
            worst = sorted(gen_overdue_by_purpose.items(), key=lambda kv: -kv[1])[:3]
            tips.append(_tip('action', f"₱{ol['overdue_past']:,.0f} from past months is still unclaimed",
                (f"Mostly {', '.join(f'{k} ₱{v:,.0f}' for k, v in worst)}. " if worst else "")
                + "These General commitments are past their month. If they will still be paid, have them claimed; "
                "if not, release them — each one released raises the free-to-spend balance."
            ))

        if plan:
            p = plan
            span = f"{p['period']} ({p['months']} completed month{'s' if p['months'] != 1 else ''})"
            if p['status'] == 'deficit':
                gap = -p['headroom']
                flex_txt = (
                    f"The flexible allotments (everything except fixed costs and allowances) total ₱{p['flexible']:,.0f} a month, "
                    + (f"so trimming them by {gap / p['flexible'] * 100:.0f}% closes the gap without touching allowances."
                       if p['flexible'] and gap <= p['flexible'] * 0.3
                       else "so they cannot close the gap alone — the larger recurring allotments need a phased review too.")
                )
                tips.append(_tip('action', f"Recurring spending is ₱{gap:,.0f} a month above income",
                    f"Over {span}, General income averaged ₱{p['avg_in']:,.0f} a month against ₱{p['avg_out']:,.0f} of commitments. "
                    f"Usable Funds shrink by that gap every month until allotments come down or giving rises. {flex_txt}"
                ))
            elif p['status'] == 'tight':
                tips.append(_tip('watch', f"Only ₱{p['headroom']:,.0f} a month of headroom",
                    f"Over {span}, General income averaged ₱{p['avg_in']:,.0f} a month and ₱{p['avg_out']:,.0f} was committed — "
                    f"{p['used_pct']:.0f}% of income. That is the most new recurring spending the budget can take; "
                    f"anything above it has to come from trimming another allotment."
                ))
            else:
                tips.append(_tip('good', f"₱{p['headroom']:,.0f} a month of headroom",
                    f"Over {span}, General income averaged ₱{p['avg_in']:,.0f} a month and ₱{p['avg_out']:,.0f} was committed — "
                    f"{p['used_pct']:.0f}% of income. New recurring spending up to the headroom does not eat into savings."
                ))
            if p['typical_in'] < p['avg_out'] <= p['avg_in'] and p['short_months']:
                tips.append(_tip('watch', "A typical month does not cover its own commitments",
                    f"The middle month brought in ₱{p['typical_in']:,.0f}, below the ₱{p['avg_out']:,.0f} committed. "
                    f"The surplus comes from a few strong months; {len(p['short_months'])} of {p['months']} "
                    f"({', '.join(m[:3] for m in p['short_months'])}) fell short. Plan {p['next_year']} on the typical month, not the best ones."
                ))
            # Income direction: last three completed months vs the months before
            if p['months'] >= 6:
                ins = [gen_in_by_month.get(m, 0.0) for m in full_months]
                early, late = mean(ins[:-3]), mean(ins[-3:])
                if early and abs(late - early) / early >= 0.1:
                    up = late > early
                    tips.append(_tip('info' if up else 'watch',
                        f"General income is {'up' if up else 'down'} {abs(late - early) / early * 100:.0f}% in the last 3 months",
                        f"₱{late:,.0f} a month in {full_months[-3]}–{full_months[-1]} against ₱{early:,.0f} before. "
                        + ("Good news, but wait for it to hold before committing it to recurring allotments."
                           if up else "If this holds, the monthly headroom shrinks by the same amount — delay new recurring commitments.")
                    ))
            # Weekly items make 5-Sunday months cost more
            w5 = [gen_week5[m] for m in full_months if gen_week5.get(m)]
            if w5:
                ny = p['next_year']
                five = [month_names[i - 1] for i in range(1, 13) if len(_sundays(ny, i)) == 5]
                tips.append(_tip('info', f"A fifth Sunday costs about ₱{mean(w5):,.0f} extra",
                    f"{len(w5)} month{'s' if len(w5) != 1 else ''} so far had a week-5 tab of weekly General items. "
                    f"In {ny} the five-Sunday months are {', '.join(five)} — budget that much more for each."
                ))
            movers = [r for r in p['rows'] if r['action'] in ('review', 'lower', 'spikes', 'envelope')]
            tips.append(_tip('info', f"Suggested {p['next_year']} budget: ₱{p['suggested_total']:,.0f} a month",
                f"Built allotment by allotment in the table above — ₱{abs(p['suggested_headroom']):,.0f} a month "
                f"{'under' if p['suggested_headroom'] >= 0 else 'over'} this year's average income. "
                + (f"Worth a decision: {', '.join(r['purpose'] for r in movers[:5])}." if movers else "Every allotment can simply be held.")
            ))

        # Set-aside funds: does each one's own collection cover what it pays out?
        n_full = len(full_months)
        for f in spend['restricted']:
            f_in = sum(side_in[f['name']].get(m, 0.0) for m in full_months) / n_full if n_full else 0.0
            f_out = sum(side_out[f['name']].get(m, 0.0) for m in full_months) / n_full if n_full else 0.0
            if f['projected'] < 0:
                tips.append(_tip('action', f"The {f['name']} Fund cannot cover its pending claims",
                    f"₱{f['available']:,.0f} available against ₱{f['pending']:,.0f} pending leaves it ₱{abs(f['projected']):,.0f} short."
                ))
            elif f_out > f_in and f_out:
                left = f['projected'] / (f_out - f_in)
                tips.append(_tip('watch', f"{f['name']} pays out more than it collects",
                    f"About ₱{f_out:,.0f} a month goes out against ₱{f_in:,.0f} collected. "
                    f"Its ₱{f['projected']:,.0f} balance covers the difference for about {left:.0f} more month{'s' if round(left) != 1 else ''}."
                ))
            elif f_out:
                tips.append(_tip('good', f"{f['name']} collections cover its payouts",
                    f"About ₱{f_in:,.0f} a month comes in against ₱{f_out:,.0f} going out, so the fund grows by ₱{f_in - f_out:,.0f} a month. "
                    f"It stays set aside — not available for General spending."
                ))
        for a in res['account_balances']:
            if a.get('fund') and a['effective_balance'] < 0:
                tips.append(_tip('action', f"{a['name']} is overdrawn by ₱{abs(a['effective_balance']):,.0f}",
                    f"₱{a['pending_deductions']:,.0f} was claimed from it but only ₱{a['ledger_balance']:,.0f} came in. "
                    f"Re-source those claims to the account that actually paid, or record the missing deposit."
                ))
        stray = sum(f['other_postings'] for f in fund_cards if f['name'] in ('General', 'Benevolence'))
        if abs(stray) >= 1:
            tips.append(_tip('watch', f"₱{stray:,.2f} in the ledgers did not come from a collection",
                "The General/Benevolence ledgers hold postings with no submitted collection behind them. "
                "Check for journal entries left behind by deleted or cancelled collections — they inflate the usable balance."
            ))
        wg = next(f for f in fund_cards if f['name'] == 'White Gift')
        if wg['received']:
            tips.append(_tip('info', f"White Gift has ₱{wg['available']:,.0f} left",
                f"That is {wg['available'] / wg['received'] * 100:.0f}% of the ₱{wg['received']:,.0f} received. "
                f"It is kept separate, so spending it does not affect operations."
            ))
        # Sort is stable: within a level, position tips stay ahead of allotment tips
        res['insights'] = sorted(tips + res['insights'], key=lambda t: LEVEL_ORDER[t['level']])
        if plan:
            res['plan_json'] = json.dumps({
                'year': selected_year, 'next_year': plan['next_year'],
                'avg_in': plan['avg_in'], 'typical_in': plan['typical_in'],
                'rows': [{'purpose': r['purpose'], 'avg': round(r['avg'], 2), 'suggested': r['suggested']} for r in plan['rows']],
            })
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Financial Statement Error")
    
    context.update(res)
    return context

@frappe.whitelist()
def download_disbursements_excel(year, month=None):
    """Statement workbook for the accountant: summary, monthly cash flow,
    every collection and disbursement item (drafts included, with status)
    and the ledger postings behind the account balances."""
    if "System Manager" not in frappe.get_roles():
        frappe.throw(
            frappe._("You are not permitted to download the financial statement."),
            frappe.PermissionError,
        )
    from church_management.church_management.financial_statement_export import build_workbook

    content, filename = build_workbook(year, month)
    frappe.response['filename'] = filename
    frappe.response['filecontent'] = content
    frappe.response['type'] = 'binary'
