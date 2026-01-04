import frappe

def execute():
    company = "nxtech test company"
    abbr = "NTC"
    
    # Create White Gift Cashless
    acc_name = f"White Gift Cashless - {abbr}"
    if not frappe.db.exists("Account", acc_name):
        doc = frappe.new_doc("Account")
        doc.account_name = "White Gift Cashless"
        doc.parent_account = f"Bank Accounts - {abbr}"
        doc.company = company
        doc.is_group = 0
        doc.account_type = "Bank"
        doc.insert()
        print(f"Created: {acc_name}")
    else:
        print(f"Exists: {acc_name}")
        
    frappe.db.commit()

if __name__ == "__main__":
    execute()
