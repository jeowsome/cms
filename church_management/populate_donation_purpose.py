import frappe


def execute():
    """Idempotently seed the Donation Purpose dropdown.

    "Mission" is flagged is_mission: its donation items need admin approval
    and post to the mission ledger accounts on approval.
    """
    purposes = [
        ("Mission", 1),
        ("Fund Raising", 0),
        ("Planned Event", 0),
    ]

    for name, is_mission in purposes:
        if frappe.db.exists("Donation Purpose", name):
            print(f"Donation Purpose {name} already exists.")
            continue
        doc = frappe.new_doc("Donation Purpose")
        doc.purpose_name = name
        doc.is_mission = is_mission
        doc.insert(ignore_permissions=True)
        print(f"Created Donation Purpose: {name}")

    frappe.db.commit()
