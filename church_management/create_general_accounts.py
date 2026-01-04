import frappe

def execute():
    companies = frappe.get_all("Company", fields=["name", "abbr"])
    
    for comp in companies:
        company_name = comp.name
        abbr = comp.abbr
        
        # 1. Identify Parent for Cash
        # Try to find "Cash In Hand - {abbr}" or any "Cash" group
        cash_parent = frappe.db.get_value("Account", {"account_name": "Cash In Hand", "company": company_name, "is_group": 1}, "name")
        if not cash_parent:
             # Fallback check by name construction
             check_name = f"Cash In Hand - {abbr}"
             if frappe.db.exists("Account", check_name):
                 cash_parent = check_name
        
        # 2. Identify Parent for Bank
        # Try to find "Bank Accounts - {abbr}" or any "Bank" group
        bank_parent = frappe.db.get_value("Account", {"account_name": "Bank Accounts", "company": company_name, "is_group": 1}, "name")
        if not bank_parent:
             check_name = f"Bank Accounts - {abbr}"
             if frappe.db.exists("Account", check_name):
                 bank_parent = check_name

        # Create Accounts if Parent Exists
        
        # General Cash
        if cash_parent:
            acc_name = f"General Cash - {abbr}"
            if not frappe.db.exists("Account", acc_name):
                try:
                    doc = frappe.new_doc("Account")
                    doc.account_name = "General Cash"
                    doc.parent_account = cash_parent
                    doc.company = company_name
                    doc.is_group = 0
                    doc.account_type = "Cash"
                    doc.insert(ignore_permissions=True)
                    print(f"Created: {acc_name}")
                except Exception as e:
                    print(f"Error creating {acc_name}: {e}")
            else:
                pass # Exists
        else:
            print(f"Skipping General Cash for {company_name}: Parent 'Cash In Hand' not found.")

        # General Cashless
        if bank_parent:
            acc_name = f"General Cashless - {abbr}"
            if not frappe.db.exists("Account", acc_name):
                try:
                    doc = frappe.new_doc("Account")
                    doc.account_name = "General Cashless"
                    doc.parent_account = bank_parent
                    doc.company = company_name
                    doc.is_group = 0
                    doc.account_type = "Bank"
                    doc.insert(ignore_permissions=True)
                    print(f"Created: {acc_name}")
                except Exception as e:
                     print(f"Error creating {acc_name}: {e}")
            else:
                pass # Exists
        else:
            print(f"Skipping General Cashless for {company_name}: Parent 'Bank Accounts' not found.")
            
    frappe.db.commit()

if __name__ == "__main__":
    execute()
