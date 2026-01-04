
import frappe

def run():
    doc = frappe.get_doc("DocType", "Disbursement Purpose")
    
    # Check if field exists
    exists = any(f.fieldname == "default_account" for f in doc.fields)
    
    if not exists:
        new_field = frappe.new_doc("DocField")
        new_field.fieldname = "default_account"
        new_field.fieldtype = "Link"
        new_field.label = "Default Account"
        new_field.options = "Account"
        new_field.insert_after = "purpose"
        new_field.link_filters = '[["Account","is_group","=",0]]'
        
        doc.fields.insert(1, new_field) # Insert after purpose
        doc.save()
        print("Added default_account to Disbursement Purpose")
    else:
        print("Field default_account already exists")

    frappe.db.commit()
