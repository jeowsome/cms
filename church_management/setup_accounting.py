import frappe

def execute():
    # 1. Identify Target Company
    company = frappe.db.get_single_value("Global Defaults", "default_company")
    if not company:
        companies = frappe.get_all("Company", limit=1)
        if companies:
            company = companies[0].name
        else:
            print("No company found. Skipping account setup.")
            return

    print(f"Running Account Setup for Company: {company}")
    company_doc = frappe.get_doc("Company", company)
    abbr = company_doc.abbr
    
    # 2. Identify/Create Parent Accounts
    # We try to find existing group accounts for Cash, Bank, Income, Expense
    def get_or_find_parent(account_name_start, root_type, is_group=1):
        # Try finding by name pattern first
        acc = frappe.db.get_value("Account", 
            {"account_name": ["like", f"{account_name_start}%"], "company": company, "is_group": 1}, "name")
        if acc: return acc
        
        # Fallback: Find ANY match in root_type
        acc = frappe.db.get_value("Account", 
            {"root_type": root_type, "company": company, "is_group": 1}, "name")
        return acc

    cash_parent = get_or_find_parent("Cash", "Asset")
    bank_parent = get_or_find_parent("Bank", "Asset")
    income_parent = get_or_find_parent("Direct Income", "Income")
    expense_parent = get_or_find_parent("Direct Expenses", "Expense")
    
    # Hard fallback names if strict parents required for structure
    if not cash_parent: cash_parent = f"Cash In Hand - {abbr}"
    if not bank_parent: bank_parent = f"Bank Accounts - {abbr}"
    if not income_parent: income_parent = f"Direct Income - {abbr}"
    if not expense_parent: expense_parent = f"Direct Expenses - {abbr}"

    # 3. Define Accounts to Create
    acc_list = [
        # Income
        ("Tithes Income", income_parent, "Direct Income"),
        ("Offering Income", income_parent, "Direct Income"),
        ("Mission Income", income_parent, "Direct Income"),
        ("Benevolence Income", income_parent, "Direct Income"),
        ("Loose Income", income_parent, "Direct Income"),
        ("Sunday School Income", income_parent, "Direct Income"),
        ("White Gift Income", income_parent, "Direct Income"),
        ("Church Income", income_parent, "Direct Income"),

        # Cash Assets
        ("Tithes Cash", cash_parent, "Cash"),
        ("Offering Cash", cash_parent, "Cash"),
        ("Mission Cash", cash_parent, "Cash"),
        ("Benevolence Cash", cash_parent, "Cash"),
        ("Loose Cash", cash_parent, "Cash"),
        ("Sunday School Cash", cash_parent, "Cash"),
        ("White Gift Cash", cash_parent, "Cash"),
        ("General Cash", cash_parent, "Cash"), # Consolidated

        # Bank/Cashless Assets
        ("Tithes Cashless", bank_parent, "Bank"),
        ("Offering Cashless", bank_parent, "Bank"),
        ("Mission Cashless", bank_parent, "Bank"),
        ("Benevolence Cashless", bank_parent, "Bank"),
        ("Loose Cashless", bank_parent, "Bank"),
        ("Sunday School Cashless", bank_parent, "Bank"),
        ("White Gift Cashless", bank_parent, "Bank"), # Consolidated
        ("General Cashless", bank_parent, "Bank"), # Consolidated
    ]

    created_accounts = {}

    for name, parent, acc_type in acc_list:
        full_name = f"{name} - {abbr}"
        
        # IDEMPOTENCY CHECK
        if frappe.db.exists("Account", full_name):
            # print(f"Exists: {full_name}")
            created_accounts[name] = full_name
            continue
            
        # Parent Validation before creation
        if not frappe.db.exists("Account", parent):
            print(f"Skipping {full_name}: Parent {parent} does not exist.")
            continue

        try:
            doc = frappe.new_doc("Account")
            doc.account_name = name
            doc.parent_account = parent
            doc.company = company
            doc.account_type = acc_type
            doc.currency = company_doc.default_currency
            doc.insert(ignore_permissions=True)
            print(f"Created: {full_name}")
            created_accounts[name] = full_name
        except Exception as e:
            print(f"Failed to create {full_name}: {e}")

    # 4. Expenditure Purpose Mapping (Optional - idempotent)
    # ... (Keep existing mapping logic but wrapped nicely)
    purpose_account_map = {
        "Allowance": "Staff Allowances",
        "Regular Activity": "Ministry Program Expenses",
        "Transportation": "Transportation Expenses",
        "Mission Support": "Missionary Support",
        "Rent": "Rent",
        "Unplanned": "Miscellaneous Expenses",
        "Digital": "Digital & Software Expenses",
        "Maintenance": "Repairs & Maintenance",
        "Government": "Taxes & Licenses",
        "Special Event": "Special Event Expenses",
        "Benevolence": "Benevolence Payouts"
    }
    
    for purpose, acc_name in purpose_account_map.items():
        full_name = f"{acc_name} - {abbr}"
        if not frappe.db.exists("Account", full_name):
             if frappe.db.exists("Account", expense_parent):
                try:
                    doc = frappe.new_doc("Account")
                    doc.account_name = acc_name
                    doc.parent_account = expense_parent
                    doc.company = company
                    doc.account_type = "Expense Account"
                    doc.currency = company_doc.default_currency
                    doc.insert(ignore_permissions=True)
                    print(f"Created Expense: {full_name}")
                except Exception as e:
                    print(f"Error creating expense {full_name}: {e}")

    # 5. Cost Centers (Idempotent)
    departments = [
        "Pasig General", "Pasig Sunday School", "Pasig Music Team", 
        "Cainta Sunday School", "Pasig Ladies", "Pasig Discipleship - Boys", 
        "Pasig Discipleship - Girls", "Cainta General", "Missionary", 
        "Pasig Admin", "Pasig ColSPro", "Pasig Young People", 
        "Pasig Men", "Pasig Young Pro"
    ]
    
    root_cc = frappe.db.get_value("Cost Center", {"is_group": 1, "parent_cost_center": ["is", "not set"], "company": company}, "name")
    if not root_cc:
        root_cc = f"{company} - {abbr}" # fallback

    for dept in departments:
        group_name = dept.split(" ")[0]
        group_cc_name = f"{group_name} - {abbr}"
        leaf_cc_name = f"{dept} - {abbr}"
        
        # Ensure Group
        if not frappe.db.exists("Cost Center", group_cc_name) and frappe.db.exists("Cost Center", root_cc):
            try:
                cc = frappe.new_doc("Cost Center")
                cc.cost_center_name = group_name
                cc.parent_cost_center = root_cc
                cc.is_group = 1
                cc.company = company
                cc.insert(ignore_permissions=True)
            except: pass
            
        # Ensure Leaf
        if not frappe.db.exists("Cost Center", leaf_cc_name):
             parent_cc = group_cc_name if frappe.db.exists("Cost Center", group_cc_name) else root_cc
             if frappe.db.exists("Cost Center", parent_cc):
                try:
                    cc = frappe.new_doc("Cost Center")
                    cc.cost_center_name = dept
                    cc.parent_cost_center = parent_cc
                    cc.is_group = 0
                    cc.company = company
                    cc.insert(ignore_permissions=True)
                except: pass

    # 6. Update Settings (Consolidated)
    settings = frappe.get_doc("Church Management Settings")
    
    # Helpers
    def set_setting(field, key):
        if key in created_accounts:
            settings.set(field, created_accounts[key])
            
    # Income
    set_setting("tithes_income_account", "Tithes Income")
    set_setting("offering_income_account", "Offering Income")
    set_setting("mission_income_account", "Mission Income")
    set_setting("benevolence_income_account", "Benevolence Income")
    set_setting("loose_income_account", "Loose Income")
    set_setting("sunday_school_income_account", "Sunday School Income")
    set_setting("white_gift_income_account", "White Gift Income")
    set_setting("default_income_account", "Church Income")

    # Cash
    set_setting("tithes_cash_account", "Tithes Cash")
    set_setting("offering_cash_account", "Offering Cash")
    set_setting("mission_cash_account", "Mission Cash")
    set_setting("benevolence_cash_account", "Benevolence Cash")
    set_setting("loose_cash_account", "Loose Cash")
    set_setting("sunday_school_cash_account", "Sunday School Cash")
    set_setting("white_gift_cash_account", "White Gift Cash")

    # Cashless
    set_setting("tithes_cashless_account", "Tithes Cashless")
    set_setting("offering_cashless_account", "Offering Cashless")
    set_setting("mission_cashless_account", "Mission Cashless")
    set_setting("benevolence_cashless_account", "Benevolence Cashless")
    set_setting("loose_cashless_account", "Loose Cashless")
    # Setting White Gift Cashless (from set_wg_settings.py)
    set_setting("white_gift_cashless_account", "White Gift Cashless")

    # Defaults
    def_cc_name = f"Pasig General - {abbr}" 
    if not frappe.db.exists("Cost Center", def_cc_name):
        def_cc = frappe.db.get_value("Cost Center", {"is_group": 0, "company": company}, "name")
    else:
        def_cc = def_cc_name

    def_exp_name = f"Ministry Program Expenses - {abbr}"
    if not frappe.db.exists("Account", def_exp_name):
         def_exp = frappe.db.get_value("Account", {"account_type": "Expense", "is_group": 0, "company": company}, "name")
    else:
        def_exp = def_exp_name

    if def_cc: settings.default_cost_center = def_cc
    if def_exp: settings.default_expense_account = def_exp

    settings.save(ignore_permissions=True)
    frappe.db.commit()
    print("Church Management Settings & Accounts Synced.")
