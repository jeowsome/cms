import frappe


def execute():
	tags = [
		"Worship Lead",
		"Backup Vocals 1",
		"Backup Vocals 2",
		"Keyboard",
		"Acoustic Guitar",
		"Bass Guitar",
		"Beatbox",
		"Laptop",
		"Devotion",
		"Back Up Singer",
	]

	for tag in tags:
		if not frappe.db.exists("Music Team Tag", tag):
			doc = frappe.new_doc("Music Team Tag")
			doc.tag_label = tag
			doc.insert()
			print(f"Created Music Team Tag: {tag}")

	if not frappe.db.exists("Ministry", "Music Team"):
		doc = frappe.new_doc("Ministry")
		doc.ministry_name = "Music Team"
		doc.active = 1
		doc.insert()
		print("Created Ministry: Music Team")

	frappe.db.commit()


if __name__ == "__main__":
	execute()
