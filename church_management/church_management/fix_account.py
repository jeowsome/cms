
import frappe

def run():
    company = "nxtech test company"
    target_acc = "Cash In Hand - NTC"
    
    # Debug Companies
    companies = frappe.get_all("Company", fields=["name", "abbr"])
    print(f"Companies found: {companies}")
    
    if not frappe.db.exists("Company", company):
        print(f"Company {company} does not exist!")
        return

    # Check any account for this company
    any_acc = frappe.get_all("Account", filters={"company": company}, limit=5)
    print(f"Sample accounts for {company}: {any_acc}")

    # Identify a valid parent
    possible_parents = ["Current Assets - NTC", "Current Assets"]
    parent_acc = None
    
    for p in possible_parents:
        if frappe.db.exists("Account", {"name": p, "company": company}):
            parent_acc = p
            break
            
    if not parent_acc:
        # Fallback: Find ANY Asset group account
        assets = frappe.get_all("Account", filters={"company": company, "is_group": 1, "root_type": "Asset"}, limit=1)
        if assets:
            parent_acc = assets[0].name
            
    if not parent_acc:
        # Try finding root 'Application of Funds (Assets)' or similar
        roots = frappe.get_all("Account", filters={"company": company, "is_group": 1, "parent_account": ["is", "not set"]}, limit=5)
        # Note: parent_account uses 'is not set' usually means None check or empty string
        roots = frappe.db.sql(f"select name from `tabAccount` where company='{company}' and ifnull(parent_account, '')=''", as_dict=1)
        print(f"Root accounts: {roots}")
        # Maybe use root?
        if roots:
            parent_acc = roots[0].name
            
    if not parent_acc:
        print(f"Could not find a valid parent account in {company}")
        return

    if not frappe.db.exists("Account", target_acc):
        try:
            doc = frappe.new_doc("Account")
            doc.account_name = "Cash In Hand"
            doc.company = company
            doc.parent_account = parent_acc
            doc.is_group = 1
            doc.account_type = "Cash"
            doc.insert()
            frappe.db.commit()
            print(f"Created {target_acc} under {parent_acc}")
        except Exception as e:
            print(f"Failed to create account: {e}")
    else:
        print(f"{target_acc} already exists")
