import frappe


def execute():
    tags = [
        "Acoustic Guitar",
        "Bass Guitar",
        "Beatbox",
        "Back Up Singer",
        "Worship Lead",
        "Laptop",
        "Devotion",
    ]

    for tag in tags:
        if not frappe.db.exists("Music Team Tag", tag):
            doc = frappe.new_doc("Music Team Tag")
            doc.tag_label = tag
            doc.insert()
            print(f"Created Music Team Tag: {tag}")
        else:
            print(f"Music Team Tag {tag} already exists.")

    frappe.db.commit()


if __name__ == "__main__":
    execute()
