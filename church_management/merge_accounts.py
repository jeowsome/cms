import frappe
from frappe.model.rename_doc import rename_doc

def execute():
    # Map Old -> New
    abbr = "NTC"
    
    # 1. Merge Cash Accounts
    target_cash = f"General Cash - {abbr}"
    sources_cash = [
        f"Tithes Cash - {abbr}",
        f"Offering Cash - {abbr}",
        f"Loose Cash - {abbr}",
        f"Sunday School Cash - {abbr}"
    ]
    
    # Verify Target Exists
    if not frappe.db.exists("Account", target_cash):
        print(f"Target Account {target_cash} not found. Aborting.")
        return

    for source in sources_cash:
        if frappe.db.exists("Account", source):
            print(f"Merging {source} -> {target_cash}...")
            try:
                rename_doc("Account", source, target_cash, merge=True, ignore_permissions=True)
                print(f"Success: {source} merged and deleted.")
            except Exception as e:
                print(f"Error merging {source}: {e}")
        else:
            print(f"Source {source} not found, skipping.")

    # 2. Merge Cashless Accounts
    target_cashless = f"General Cashless - {abbr}"
    sources_cashless = [
        f"Tithes Cashless - {abbr}",
        f"Offering Cashless - {abbr}",
        f"Loose Cashless - {abbr}",
        # f"Sunday School Cashless - {abbr}" # If it existed
    ]
    
    if not frappe.db.exists("Account", target_cashless):
        print(f"Target Account {target_cashless} not found. Aborting.")
        return

    for source in sources_cashless:
        if frappe.db.exists("Account", source):
            print(f"Merging {source} -> {target_cashless}...")
            try:
                rename_doc("Account", source, target_cashless, merge=True, ignore_permissions=True)
                print(f"Success: {source} merged and deleted.")
            except Exception as e:
                print(f"Error merging {source}: {e}")
        else:
            print(f"Source {source} not found, skipping.")

    frappe.db.commit()

if __name__ == "__main__":
    execute()
