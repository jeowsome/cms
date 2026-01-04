import frappe
import json
import os

def execute():
    workspace_name = "JBC CMS"
    
    # Path to the JSON file
    file_path = frappe.get_app_path("church_management", "church_management", "workspace", "jbc_cms", "jbc_cms.json")
    
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, "r") as f:
        data = json.load(f)
        
    if not frappe.db.exists("Workspace", workspace_name):
        print(f"Workspace {workspace_name} does not exist in DB.")
        return

    doc = frappe.get_doc("Workspace", workspace_name)
    
    # Force update fields
    doc.content = data.get("content")
    doc.shortcuts = [] # Clear existing
    
    for shortcut in data.get("shortcuts", []):
        doc.append("shortcuts", shortcut)
        
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    print(f"Workspace {workspace_name} forced updated from JSON.")
