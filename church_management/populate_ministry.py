import frappe


def execute():
    # Rename legacy ministries to the concise names. rename_doc cascades to all
    # linked fields (e.g. Ministry Schedule Assignment.ministry).
    renames = {
        "Ushering": "Usher",
        "Worship Leading": "Worship Leader",
        "Scripture Reading": "Scripture Reader",
    }
    for old, new in renames.items():
        if frappe.db.exists("Ministry", old) and not frappe.db.exists("Ministry", new):
            frappe.rename_doc("Ministry", old, new, force=True)
            print(f"Renamed Ministry: {old} -> {new}")

    ministries = [
        "Music Team",
        "Social Media",
        "Usher",
        "Worship Leader",
        "Scripture Reader",
        "Discipleship Boys",
        "Discipleship Girls",
        "Technical",
        "Gate Ushers",
        "Child-Care",
        "Prayer Meeting Leader",
        "Prayer Meeting Devotion",
    ]

    for name in ministries:
        if not frappe.db.exists("Ministry", name):
            doc = frappe.new_doc("Ministry")
            doc.ministry_name = name
            doc.active = 1
            doc.insert()
            print(f"Created Ministry: {name}")
        else:
            print(f"Ministry {name} already exists.")

    frappe.db.commit()


if __name__ == "__main__":
    execute()
