import frappe
from frappe.utils import getdate

def get_context(context):
    context.no_cache = 1
    
    # 1. Filters Setup
    selected_year = frappe.form_dict.get('year', '2026')
    selected_month = frappe.form_dict.get('month', '')
    group_by = frappe.form_dict.get('group_by', 'Source')
    
    month_names = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    
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
            'funds': {
                'General': {'collected': 0.0, 'disbursed': 0.0},
                'Mission': {'collected': 0.0, 'disbursed': 0.0},
                'Benevolence': {'collected': 0.0, 'disbursed': 0.0},
                'White Gift': {'collected': 0.0, 'disbursed': 0.0}
            }
        },
        'monthly_data': [],
        'account_balances': [],
        'available_months': []
    }

    try:
        settings = frappe.get_single("Church Management Settings")
        
        cols_query = frappe.get_all('Collection', 
            fields=['name', 'date', 'grand_total', 'tithes_total', 'mission_total', 'offering_total', 'benevolence_collection', 'loose_collection', 'sunday_school_collection', 
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
        
        for c in cols_query:
            # General Fund = Tithes + Offering + Loose + Sunday School
            fs['funds']['General']['collected'] += (
                (c.tithes_total or 0) + (c.tithes_total_cls or 0) +
                (c.offering_total or 0) + (c.offering_total_cls or 0) +
                (c.loose_collection or 0) + (c.loose_collection_cls or 0) +
                (c.sunday_school_collection or 0)
            )
            fs['funds']['Mission']['collected'] += (c.mission_total or 0) + (c.mission_total_cls or 0)
            fs['funds']['Benevolence']['collected'] += (c.benevolence_collection or 0) + (c.benevolence_collection_cls or 0)
            fs['cash_collected'] += c.grand_total or 0.0
            fs['cashless_collected'] += sum([c.tithes_total_cls or 0.0, c.mission_total_cls or 0.0, c.offering_total_cls or 0.0, c.benevolence_collection_cls or 0.0, c.loose_collection_cls or 0.0])

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
            items = []
            for w in range(1, 6):
                items.extend(doc.get(f'disbursement_item_week_{w}') or [])
                items.extend(doc.get(f'expense_item_week_{w}') or [])
            items.extend(doc.get('monthly_expense_items') or [])
            items.extend(doc.get('monthly_disbursement_items') or [])

            for item in items:
                if item.get('status') != 'Claimed': continue
                amt = item.get('disbursed_amount') or item.get('amount') or 0.0
                purp, src = item.get('purpose'), item.get('source')
                if src: account_deductions[src] = account_deductions.get(src, 0.0) + amt
                # Map disbursed amounts to funds by source account
                mapped_fund = None
                if src:
                    src_lower = src.lower()
                    if 'white gift' in src_lower: mapped_fund = 'White Gift'
                    elif 'mission' in src_lower: mapped_fund = 'Mission'
                    elif 'benevolence' in src_lower: mapped_fund = 'Benevolence'
                    else: mapped_fund = 'General'
                if mapped_fund: fs['funds'][mapped_fund]['disbursed'] += amt
                fs['total_disbursed'] += amt
                # Store for monthly breakdown
                disb_items_by_month.setdefault(d.month_recorded, []).append({
                    'amount': amt, 'source': src, 'purpose': purp,
                    'description': item.get('description') or item.get('remarks') or purp or "No Description",
                    'received_date': item.get('received_date'),
                    'received_by': item.get('received_by'),
                    'department': item.get('department')
                })

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

        display_accounts = [
            ('General Cash', general_cash_ledger, ['General Cash - JBC'] + general_cash_ledger, False),
            ('General Cashless', general_cashless_ledger, ['General Cashless - JBC'] + general_cashless_ledger, False),
            ('Mission Cash', [settings.mission_cash_account], [settings.mission_cash_account], False),
            ('Mission Cashless', [settings.mission_cashless_account], [settings.mission_cashless_account], False),
            ('Benevolence Cash', [settings.benevolence_cash_account], [settings.benevolence_cash_account], False),
            ('Benevolence Cashless', [settings.benevolence_cashless_account], [settings.benevolence_cashless_account], False),
            ('White Gift Cash', [settings.white_gift_cash_account], [settings.white_gift_cash_account], True),
            ('White Gift Cashless', [settings.white_gift_cashless_account], [settings.white_gift_cashless_account], True),
        ]

        for label, ledger_accounts, deduction_sources, cumulative in display_accounts:
            ledger_balance = sum(get_gl_balance(a, cumulative=cumulative) for a in ledger_accounts if a)
            deduction = sum(account_deductions.get(s, 0.0) for s in deduction_sources if s)
            if ledger_balance != 0 or deduction != 0:
                res['account_balances'].append({
                    'name': label,
                    'ledger_balance': ledger_balance,
                    'pending_deductions': deduction,
                    'effective_balance': ledger_balance - deduction
                })
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Financial Statement Error")
    
    context.update(res)
    return context

@frappe.whitelist()
def download_disbursements_excel(year):
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
                amt = item.get('disbursed_amount') or item.get('amount') or 0.0
                data.append([d.month_recorded, item.get('received_date'), item.get('source'), item.get('purpose'), item.get('department'), item.get('description') or item.get('remarks') or item.get('purpose') or "", item.get('received_by'), amt])
    xlsx_file = make_xlsx(data, "Disbursements")
    frappe.response['filename'] = f"Disbursements_{year}.xlsx"
    frappe.response['filecontent'] = xlsx_file.getvalue()
    frappe.response['type'] = 'binary'
