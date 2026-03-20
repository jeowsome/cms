import frappe
from frappe.utils import getdate

def execute():
    # Only target specific company mentioned, or all? Safe to add all.
    companies = frappe.get_all("Company", pluck="name")
    
    if not frappe.db.exists("Fiscal Year", "2026"):
        doc = frappe.new_doc("Fiscal Year")
        doc.year = "2026"
        doc.year_start_date = getdate("2026-01-01")
        doc.year_end_date = getdate("2026-12-31")
        
        for company in companies:
            doc.append("companies", {"company": company})
            
        doc.insert()
        frappe.db.commit()
        print("Created Fiscal Year 2026")
    else:
        print("Fiscal Year 2026 already exists")
