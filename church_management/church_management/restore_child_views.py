
import frappe

def run():
    # Define the config: DocType -> Fields to show in list view with width (optional)
    config = {
        "Weekly Allowance Item": ["worker", "amount", "purpose", "source"],
        "Weekly Activity Item": ["description", "amount", "purpose", "source"],
        "Monthly Disbursement Item": ["default_receiver", "amount", "purpose", "source"],
        "Monthly Expense Item": ["description", "amount", "purpose", "source"],
        "Mission Support Item": ["worker", "amount", "purpose", "source"]
    }
    
    for dt, fields in config.items():
        doc = frappe.get_doc("DocType", dt)
        updated = False
        
        for f in doc.fields:
            if f.fieldname in fields:
                if not f.in_list_view:
                    f.in_list_view = 1
                    updated = True
                
                # Ensure appropriate column width roughly
                if f.fieldname in ["description", "purpose", "worker", "default_receiver"]:
                    if not f.columns: 
                        f.columns = 3 # Wider
                        updated = True
                elif f.fieldname == "amount":
                     if not f.columns: 
                        f.columns = 2
                        updated = True
            else:
                # Optionally hide others from list view to keep it clean, but let's just ensure the key ones are visible
                pass
                
        if updated:
            doc.save()
            print(f"Updated {dt} list view settings")
        else:
            print(f"No changes needed for {dt}")
            
    frappe.db.commit()
