import frappe


def execute():
    ministries = [
        "Music Team",
        "Social Media",
        "Ushering",
        "Worship Leading",
        "Scripture Reading",
        "Discipleship Boys",
        "Discipleship Girls",
        "Technical",
        "Gate Ushers",
        "Child-Care",
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
