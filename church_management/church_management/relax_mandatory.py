
import frappe

def run():
    doctypes_to_update = [
        "Disbursement Week Item",
        "Disbursement Week Expense Item"
    ]
    
    for dt in doctypes_to_update:
        doc = frappe.get_doc("DocType", dt)
        updated = False
        for f in doc.fields:
            if f.fieldname in ["worker", "source"]:
                if f.reqd:
                    f.reqd = 0
                    updated = True
                    print(f"Made {f.fieldname} optional in {dt}")
        
        if updated:
            doc.save()
            print(f"Saved {dt}")
    
    frappe.db.commit()
