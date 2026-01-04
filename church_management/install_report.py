import frappe
from frappe import _

def execute():
    reports = [
        {"name": "Collection vs Disbursement", "ref_doctype": "Journal Entry"},
        {"name": "Financial Summary GL", "ref_doctype": "Journal Entry"}
    ]
    module = "Church Management"
    
    for report in reports:
        report_name = report["name"]
        if frappe.db.exists("Report", report_name):
            frappe.delete_doc("Report", report_name)
            
        doc = frappe.get_doc({
            "doctype": "Report",
            "report_name": report_name,
            "report_type": "Script Report",
            "is_standard": "Yes",
            "module": module,
            "ref_doctype": report["ref_doctype"], 
        })
        doc.insert(ignore_permissions=True)
        print(f"Report '{report_name}' installed successfully.")
        
    frappe.db.commit()
