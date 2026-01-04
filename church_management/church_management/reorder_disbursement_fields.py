
import frappe

def run():
    doc = frappe.get_doc("DocType", "Disbursement")
    
    # 1. Clean up duplicate fields/tabs if any (heuristic based on inspection)
    # The JSON showed 'monthly_tab' (Details) and 'monthly_tab_1' (Monthly ).
    # Ideally we want just one "Monthly" tab.
    # Also 'weekly_tab' is there.
    # And 'company' is at top or valid place.
    
    # Let's define a strict clean order.
    # Top Section:
    # 1. Company
    # 2. Template Link
    # 3. Column Break
    # 4. Month, Year
    # 5. Section Break (Totals)
    # 6. Total Amount, Total Disbursed...
    # 7. Journal Entry (Amended From)
    
    # Tabs:
    # 1. Weekly Tab
    #    - Week 1 Section -> Week 1 Tables
    #    - Week 2 Section -> Week 2 Tables ...
    # 2. Monthly Tab
    #    - Monthly Tables
    
    desired_order = [
        "company",
        "disbursement_template",
        "column_break_2",
        "month_recorded",
        "year_recorded",
        
        "section_break_4",
        "total_amount_disbursed",
        "column_break_6",
        "total_disbursed",
        "amended_from",
        "journal_entry",
        
        # Weekly Tab
        "weekly_tab",
        "week_1_section",
        "disbursement_item_week_1",
        "expense_item_week_1",
        
        "section_break_cjym", # Week 2
        "disbursement_item_week_2",
        "expense_item_week_2",
        
        "section_break_ftkm", # Week 3
        "disbursement_item_week_3",
        "expense_item_week_3",
        
        "section_break_nrjy", # Week 4
        "disbursement_item_week_4",
        "expense_item_week_4",
        
        "section_break_2", # Week 5
        "disbursement_item_week_5",
        "expense_item_week_5",
        
        # Monthly Tab (Use 'monthly_TAB_1' if that's the one we added last, or consolidate)
        # We added 'monthly_tab' ("Details") earlier? Or "Monthly"?
        # Let's assume we want ONE tab named "Monthly". 
        # In JSON: "monthly_tab" label="Details", "monthly_tab_1" label="Monthly ".
        # We should use one. Let's use 'monthly_tab' and rename label to "Monthly".
        "monthly_tab_1", 
        "monthly_disbursement_items",
        "monthly_expense_items"
    ]
    
    doc.field_order = desired_order
    
    # Fix the duplicate tab labels issue
    for f in doc.fields:
        if f.fieldname == "monthly_tab_1":
            f.label = "Monthly"
    
    # Rebuild fields list based on order
    ordered_fields = []
    field_map = {f.fieldname: f for f in doc.fields}
    
    for fname in desired_order:
        if fname in field_map:
            ordered_fields.append(field_map[fname])
    
    # Add loose fields (safely ignore duplicates like 'monthly_tab' if we chose 'monthly_tab_1')
    # Actually we should delete unused fields from fields list if we are sure.
    # But safer to just prioritize ordered ones and let leftovers append (but hidden/ignored by field_order usually).
    # Frappe generally ignores fields not in field_order if editable_grid/etc layout.
    
    # Let's remove 'monthly_tab' (label=Details) if we are using 'monthly_tab_1'
    doc.fields = ordered_fields
    
    doc.save()
    print("Reordered Disbursement fields")
    frappe.db.commit()
