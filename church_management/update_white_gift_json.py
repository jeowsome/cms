import json
import os

file_path = "/workspace/development/frappe-bench/apps/church_management/church_management/church_management/doctype/white_gift/white_gift.json"

with open(file_path, "r") as f:
    data = json.load(f)

# Update field_order
if "journal_entry" not in data["field_order"]:
    data["field_order"].append("journal_entry")

# Update fields
field_exists = False
for existing_field in data["fields"]:
    if existing_field["fieldname"] == "journal_entry":
        field_exists = True
        break

if not field_exists:
    new_field = {
        "fieldname": "journal_entry",
        "fieldtype": "Link",
        "label": "Journal Entry",
        "options": "Journal Entry",
        "read_only": 1
    }
    # Insert after year_recorded
    data["fields"].insert(1, new_field)

with open(file_path, "w") as f:
    json.dump(data, f, indent=1) # Frappe uses 1 space indent usually? Or Tab? Let's try 1 space as per view_file. 
    # Actually wait, view_file showed 1 space indent. Let's stick to standard indentation.
    # checking file again... 
    # 2:  "actions": [],
    # seems like 1 space indent.
