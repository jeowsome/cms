
import frappe

def run():
    doc = frappe.get_doc("DocType", "Disbursement Week Item")
    
    # Check if field exists
    exists = any(f.fieldname == "status" for f in doc.fields)
    
    if not exists:
        new_field = frappe.new_doc("DocField")
        new_field.fieldname = "status"
        new_field.fieldtype = "Select"
        new_field.label = "Status"
        new_field.options = "Unclaimed\nClaimed"
        new_field.default = "Unclaimed"
        new_field.insert_after = "remarks" # Insert at end or after remarks
        
        doc.fields.append(new_field)
        doc.save()
        print("Added status field to Disbursement Week Item")
    else:
        print("Field status already exists")

    frappe.db.commit()
