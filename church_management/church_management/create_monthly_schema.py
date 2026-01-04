
import frappe

def run():
    disbursement = frappe.get_doc("DocType", "Disbursement")
    
    existing_fields = [f.fieldname for f in disbursement.fields]
    modified = False
    
    # 1. Add Monthly Tab
    if "monthly_tab" not in existing_fields:
        monthly_tab = frappe.new_doc("DocField")
        monthly_tab.fieldname = "monthly_tab"
        monthly_tab.fieldtype = "Tab Break"
        monthly_tab.label = "Monthly"
        
        # Insert before weekly_tab
        idx = -1
        for i, f in enumerate(disbursement.fields):
            if f.fieldname == "weekly_tab":
                idx = i
                break
        
        if idx != -1:
            disbursement.fields.insert(idx, monthly_tab)
            modified = True
            print("Added Monthly Tab")
        else:
            # If weekly_tab not found (unlikely), append
            disbursement.fields.append(monthly_tab)
            modified = True
            print("Added Monthly Tab (appended)")
    
    # 2. Add Monthly Disbursement Table
    if "monthly_disbursement_items" not in existing_fields:
        md_field = frappe.new_doc("DocField")
        md_field.fieldname = "monthly_disbursement_items"
        md_field.fieldtype = "Table"
        md_field.label = "Monthly Disbursement"
        md_field.options = "Disbursement Week Item" # Reusing the same item doctype
        
        # Insert after monthly_tab
        idx = -1
        for i, f in enumerate(disbursement.fields):
            if f.fieldname == "monthly_tab":
                idx = i
                break
        
        if idx != -1:
            disbursement.fields.insert(idx + 1, md_field)
            modified = True
            print("Added Monthly Disbursement Table")
            
    # 3. Add Monthly Expense Table
    if "monthly_expense_items" not in existing_fields:
        me_field = frappe.new_doc("DocField")
        me_field.fieldname = "monthly_expense_items"
        me_field.fieldtype = "Table"
        me_field.label = "Monthly Expenses"
        me_field.options = "Disbursement Week Expense Item" # Reusing the same expense item doctype
        
        # Insert after monthly_disbursement_items
        idx = -1
        for i, f in enumerate(disbursement.fields):
            if f.fieldname == "monthly_disbursement_items":
                idx = i
                break
        
        if idx != -1:
            disbursement.fields.insert(idx + 1, me_field)
            modified = True
            print("Added Monthly Expense Table")
            
    if modified:
        disbursement.save()
        print("Updated Disbursement DocType with Monthly Tab and Tables")
    else:
        print("Disbursement DocType already up to date")

    frappe.db.commit()
