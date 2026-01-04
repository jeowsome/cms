
import frappe

def run():
    dt = "Disbursement Week Expense Item"
    doc = frappe.get_doc("DocType", dt)
    
    # Check if purpose exists
    if not any(f.fieldname == "purpose" for f in doc.fields):
        # Add purpose field
        # Place it after 'amount' or 'department'? 
        # Checking likely fields: description, amount, department, received_by...
        
        new_field = frappe.new_doc("DocField")
        new_field.fieldname = "purpose"
        new_field.label = "Purpose"
        new_field.fieldtype = "Link"
        new_field.options = "Disbursement Purpose"
        new_field.insert_after = "amount"
        new_field.in_list_view = 1
        new_field.reqd = 0 # Optional
        
        doc.append("fields", new_field)
        doc.save()
        print(f"Added purpose field to {dt}")
    else:
        print(f"Purpose field already exists in {dt}")

    frappe.db.commit()
