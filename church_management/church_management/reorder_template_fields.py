
import frappe
import json

def run():
    doc = frappe.get_doc("DocType", "Disbursement Template")
    
    # Define desired order
    desired_order = [
         "company",
         "section_break_bzfk",
         "disbursement_year",
         "column_break_bbfv",
         
         # Weekly Tab
         "weekly_tab",
         "section_break_nhid",
         "weekly_allowances",
         "section_break_ljup",
         "weekly_activity",
         
         # Monthly Tab
         "monthly_tab",
         "monthly_disbursement",
         "monthly_expenses",
         "mission_support"
    ]
    
    # 1. Update field_order
    doc.field_order = desired_order
    
    # 2. Reorder 'fields' list to match field_order (optional but good for diffs)
    ordered_fields = []
    field_map = {f.fieldname: f for f in doc.fields}
    
    for fname in desired_order:
        if fname in field_map:
            ordered_fields.append(field_map[fname])
            
    # Add any fields not in desired_order (safety)
    for f in doc.fields:
        if f.fieldname not in desired_order:
            ordered_fields.append(f)
            
    doc.fields = ordered_fields
    
    doc.save()
    print("Reordered Disbursement Template fields")
    frappe.db.commit()
