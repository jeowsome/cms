
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field

def run():
    # 1. Create 'Disbursement Week Item' Child DocType
    if not frappe.db.exists("DocType", "Disbursement Week Item"):
        doc = frappe.get_doc({
            "doctype": "DocType",
            "module": "Church Management",
            "name": "Disbursement Week Item",
            "istable": 1,
            "editable_grid": 1,
            "fields": [
                {
                    "fieldname": "worker",
                    "fieldtype": "Link",
                    "label": "Worker",
                    "options": "Church Worker",
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
                }
            ]
        })
        doc.insert(ignore_permissions=True)
        print("Created DocType: Disbursement Week Item")
    else:
        print("DocType 'Disbursement Week Item' already exists")

    # 2. Update 'Disbursement' DocType to add weekly tables
    # We will modify the json directly to ensure it propagates strictly as desired, 
    # but since we are in dev mode, adding via get_doc is safer for now, checking fields first.
    
    disbursement = frappe.get_doc("DocType", "Disbursement")
    
    # Check if fields exist, if not add them
    fields_to_add = [
        {"fieldname": "disbursement_item_week_1", "fieldtype": "Table", "label": "Week 1", "options": "Disbursement Week Item", "insert_after": "weekly_tab"},
        {"fieldname": "disbursement_item_week_2", "fieldtype": "Table", "label": "Week 2", "options": "Disbursement Week Item", "insert_after": "disbursement_item_week_1"},
        {"fieldname": "disbursement_item_week_3", "fieldtype": "Table", "label": "Week 3", "options": "Disbursement Week Item", "insert_after": "disbursement_item_week_2"},
        {"fieldname": "disbursement_item_week_4", "fieldtype": "Table", "label": "Week 4", "options": "Disbursement Week Item", "insert_after": "disbursement_item_week_3"},
        {"fieldname": "disbursement_item_week_5", "fieldtype": "Table", "label": "Week 5", "options": "Disbursement Week Item", "insert_after": "disbursement_item_week_4"},
    ]
    
    existing_fields = [f.fieldname for f in disbursement.fields]
    modified = False
    
    last_field = "weekly_tab"
    for field_def in fields_to_add:
        if field_def["fieldname"] not in existing_fields:
            # We need to calculate insert_after dynamically if we want them ordered
            # But appending is easier with 'insert_after' property if supported by get_doc update?
            # Actually proper way is manipulating the fields list.
            
            new_field = frappe.new_doc("DocField")
            new_field.update(field_def)
            # Find index of last_field
            idx = -1
            for i, f in enumerate(disbursement.fields):
                if f.fieldname == last_field:
                    idx = i
                    break
            
            if idx != -1:
                disbursement.fields.insert(idx + 1, new_field)
            else:
                disbursement.fields.append(new_field)
                
            modified = True
            print(f"Added field: {field_def['fieldname']}")
        
        last_field = field_def["fieldname"]

    if modified:
        disbursement.save()
        print("Updated Disbursement DocType")
    else:
        print("Disbursement DocType already up to date")

    frappe.db.commit()
