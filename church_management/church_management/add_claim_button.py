
import frappe

def run():
    dt = "Disbursement Week Item"
    doc = frappe.get_doc("DocType", dt)
    
    # Check if claim button exists
    if not any(f.fieldname == "claim_btn" for f in doc.fields):
        new_field = frappe.new_doc("DocField")
        new_field.fieldname = "claim_btn"
        new_field.label = "Claim"
        new_field.fieldtype = "Button"
        # Hide if Claimed? standard depends_on support in grid varies, but let's try
        new_field.depends_on = "eval:doc.status == 'Unclaimed'"
        new_field.insert_after = "remarks"
        new_field.in_list_view = 1
        new_field.width = 100 
        
        doc.append("fields", new_field)
        doc.save()
        print(f"Added claim_btn field to {dt}")
    else:
        print(f"claim_btn field already exists in {dt}")

    frappe.db.commit()
