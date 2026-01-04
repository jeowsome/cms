
import frappe

def run():
    default_company = frappe.db.get_single_value("Global Defaults", "default_company") or ""

    # 1. Add 'company' field to Parent DocTypes
    parents = ["Disbursement Template", "Disbursement"]
    for p in parents:
        doc = frappe.get_doc("DocType", p)
        if not any(f.fieldname == "company" for f in doc.fields):
            new_field = frappe.new_doc("DocField")
            new_field.fieldname = "company"
            new_field.fieldtype = "Link"
            new_field.label = "Company"
            new_field.options = "Company"
            new_field.default = default_company
            new_field.reqd = 1
            # Insert at top (after section break if present, or first)
            doc.fields.insert(0, new_field) 
            doc.save()
            print(f"Added company field to {p}")
        else:
            print(f"Company field already exists in {p}")

    # 2. Update 'source' filters in Child DocTypes and Purpose
    # Filter: is_group=0 AND account_type IN ['Cash', 'Bank']
    # Note: 'company' filter is usually implicit if parent has 'company' field.
    
    # We use a slight trick for JSON string list in filters if needed, but strict JSON is safe.
    # Frappe expects: [["DocType","field","op","value"], ...]
    account_filter = '[["Account","is_group","=",0],["Account","account_type","in",["Cash","Bank"]]]'
    
    targets = [
        "Monthly Disbursement Item", "Monthly Expense Item", 
        "Weekly Allowance Item", "Weekly Activity Item",
        "Disbursement Week Item", "Disbursement Week Expense Item"
    ]
    
    for t in targets:
        doc = frappe.get_doc("DocType", t)
        updated = False
        for f in doc.fields:
            if f.fieldname == "source":
                f.link_filters = account_filter
                updated = True
        if updated:
            doc.save()
            print(f"Updated source filter for {t}")
        else:
            print(f"No source field found in {t}")

    # 3. Update 'default_account' filter in Disbursement Purpose
    # Disbursement Purpose doesn't have a company field, so implicit company filtering WON'T work here properly 
    # unless we add company to Disbursement Purpose too.
    # But Disbursement Purpose is global settings usually? 
    # Let's add Company to Disbursement Purpose to be safe and support multi-company.
    
    dp = frappe.get_doc("DocType", "Disbursement Purpose")
    if not any(f.fieldname == "company" for f in dp.fields):
        new_field = frappe.new_doc("DocField")
        new_field.fieldname = "company"
        new_field.fieldtype = "Link"
        new_field.label = "Company"
        new_field.options = "Company"
        new_field.default = default_company
        dp.fields.insert(0, new_field)
        dp.save()
        print("Added company field to Disbursement Purpose")
        # Reload to get new field in 'dp' object for next step? safely re-get
        dp = frappe.get_doc("DocType", "Disbursement Purpose")

    for f in dp.fields:
        if f.fieldname == "default_account":
            f.link_filters = account_filter
    dp.save()
    print("Updated default_account filter for Disbursement Purpose")

    frappe.db.commit()
