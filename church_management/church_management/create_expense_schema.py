
import frappe

def run():
    # 1. Create 'Disbursement Week Expense Item' Child DocType
    if not frappe.db.exists("DocType", "Disbursement Week Expense Item"):
        doc = frappe.get_doc({
            "doctype": "DocType",
            "module": "Church Management",
            "name": "Disbursement Week Expense Item",
            "istable": 1,
            "editable_grid": 1,
            "fields": [
                {
                    "fieldname": "description",
                    "fieldtype": "Data",
                    "label": "Description",
                    "reqd": 1,
                    "in_list_view": 1
                },
                {
                    "fieldname": "amount",
                    "fieldtype": "Currency",
                    "label": "Amount",
                    "reqd": 1,
                    "in_list_view": 1
                },
                {
                    "fieldname": "received_by",
                    "fieldtype": "Link",
                    "label": "Received By",
                    "options": "Church Worker"
                },
                {
                    "fieldname": "received_date",
                    "fieldtype": "Date",
                    "label": "Received Date"
                },
                {
                    "fieldname": "department",
                    "fieldtype": "Link",
                    "label": "Department",
                    "options": "Department Name"
                },
                {
                    "fieldname": "source",
                    "fieldtype": "Link",
                    "label": "Source",
                    "options": "Account",
                    "reqd": 1,
                    "link_filters": '[["Account","is_group","=",0]]'
                },
                {
                    "fieldname": "remarks",
                    "fieldtype": "Data",
                    "label": "Remarks"
                },
                {
                    "fieldname": "status",
                    "fieldtype": "Select",
                    "label": "Status",
                    "options": "Unclaimed\nClaimed",
                    "default": "Unclaimed"
                }
            ]
        })
        doc.insert(ignore_permissions=True)
        print("Created DocType: Disbursement Week Expense Item")
    else:
        print("DocType 'Disbursement Week Expense Item' already exists")

    # 2. Update 'Disbursement' DocType to add expense tables
    disbursement = frappe.get_doc("DocType", "Disbursement")
    
    # Check if fields exist, if not add them
    # We want to insert them immediately after the corresponding week item table check
    
    existing_fields = [f.fieldname for f in disbursement.fields]
    modified = False
    
    for i in range(1, 6):
        week_field = f"disbursement_item_week_{i}"
        expense_field = f"expense_item_week_{i}"
        
        if expense_field not in existing_fields:
            new_field = frappe.new_doc("DocField")
            new_field.fieldname = expense_field
            new_field.fieldtype = "Table"
            new_field.label = f"Week {i} Expenses"
            new_field.options = "Disbursement Week Expense Item"
            
            # Find index of week_field
            idx = -1
            for j, f in enumerate(disbursement.fields):
                if f.fieldname == week_field:
                    idx = j
                    break
            
            if idx != -1:
                disbursement.fields.insert(idx + 1, new_field)
                modified = True
                print(f"Added field: {expense_field} after {week_field}")
            else:
                print(f"Could not find {week_field} to insert after")

    if modified:
        disbursement.save()
        print("Updated Disbursement DocType with Expense tables")
    else:
        print("Disbursement DocType already up to date")

    frappe.db.commit()
