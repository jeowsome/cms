import frappe

def execute():
    purposes = [
        "Allowance",
        "Regular Activity",
        "Transportation",
        "Mission Support",
        "Rent",
        "Unplanned",
        "Digital",
        "Maintenance",
        "Government",
        "Special Event",
        "Benevolence"
    ]
    
    for p in purposes:
        if not frappe.db.exists("Disbursement Purpose", p):
            doc = frappe.new_doc("Disbursement Purpose")
            doc.purpose = p
            doc.active = 1
            # Current logic uses Department -> Cost Center, so we leave this blank to avoid confusion.
            # doc.cost_center = ... 
            doc.insert()
            print(f"Created Disbursement Purpose: {p}")
        else:
            print(f"Disbursement Purpose {p} already exists.")
            
    frappe.db.commit()

if __name__ == "__main__":
    execute()
