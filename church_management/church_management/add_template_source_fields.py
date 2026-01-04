
import frappe

def run():
    doctypes = [
        "Monthly Disbursement Item",
        "Monthly Expense Item",
        "Weekly Allowance Item",
        "Weekly Activity Item"
    ]

    for dt_name in doctypes:
        if not frappe.db.exists("DocType", dt_name):
            print(f"Skipping {dt_name} (not found)")
            continue

        doc = frappe.get_doc("DocType", dt_name)
        exists = any(f.fieldname == "source" for f in doc.fields)
        
        if not exists:
            new_field = frappe.new_doc("DocField")
            new_field.fieldname = "source"
            new_field.fieldtype = "Link"
            new_field.label = "Source"
            new_field.options = "Account"
            new_field.link_filters = '[["Account","is_group","=",0]]'
            # Insert at likely end or specific place? 
            # Appending is safest for child tables usually
            doc.fields.append(new_field)
            doc.save()
            print(f"Added source field to {dt_name}")
        else:
            print(f"Source field already exists in {dt_name}")

    frappe.db.commit()
