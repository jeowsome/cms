import frappe

def execute():
    # Set the value for the Single DocType
    frappe.db.set_single_value("Church Management Settings", "white_gift_cashless_account", "White Gift Cashless - NTC")
    
    # Verify
    val = frappe.db.get_single_value("Church Management Settings", "white_gift_cashless_account")
    print(f"Set white_gift_cashless_account to: {val}")
    
    frappe.db.commit()

if __name__ == "__main__":
    execute()
