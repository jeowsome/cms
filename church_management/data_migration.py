
import frappe
import json
import os
from frappe.model.document import Document
from frappe.utils import get_site_path

def get_data_path(module_name):
    # Path: /workspace/development/frappe-bench/apps/church_management/church_management/data
    app_path = frappe.get_app_path("church_management")
    data_path = os.path.join(app_path, "data", module_name)
    if not os.path.exists(data_path):
        os.makedirs(data_path)
    return data_path

def export_module_data(module_name):
    """
    Exports all documents for all DocTypes in the specified module to JSON files.
    """
    data_path = get_data_path(module_name)
    print(f"Exporting data for module '{module_name}' to {data_path}...")

    # Get all DocTypes in the module, excluding Single doctypes and Child Tables (istable=1)
    # Child tables are exported within their parent documents.
    doctypes = frappe.get_all("DocType", filters={"module": module_name, "issingle": 0, "istable": 0}, pluck="name")

    if not doctypes:
        print(f"No DocTypes found for module: {module_name}")
        return

    for doctype in doctypes:
        try:
            # Check if table exists to avoid errors on virtual doctypes or similar issues
            if not frappe.db.table_exists(doctype):
                continue
            
            # Fetch all record names
            names = frappe.get_all(doctype, pluck="name")
            docs = []
            for name in names:
                # get_doc returns the full document with child tables
                docs.append(frappe.get_doc(doctype, name).as_dict())

            if not docs:
                continue

            # Handle datetime serialization
            json_data = json.dumps(docs, default=str, indent=4)
            
            file_path = os.path.join(data_path, f"{doctype}.json")
            with open(file_path, "w") as f:
                f.write(json_data)
            
            print(f"Exported {len(docs)} records for {doctype}")
            
        except Exception as e:
            print(f"Error exporting {doctype}: {e}")

    print("Export completed.")

def import_module_data(module_name):
    """
    Imports data from JSON files for the specified module.
    """
    data_path = get_data_path(module_name)
    print(f"Importing data for module '{module_name}' from {data_path}...")

    if not os.path.exists(data_path):
        print("Data directory not found.")
        return

    files = [f for f in os.listdir(data_path) if f.endswith(".json")]
    
    if not files:
        print("No JSON files found to import.")
        return

    for filename in files:
        doctype = filename.replace(".json", "")
        file_path = os.path.join(data_path, filename)
        
        try:
            # Skip if doctype is a child table or doesn't exist
            if not frappe.db.table_exists(doctype):
                continue
                
            if frappe.get_meta(doctype).istable:
                print(f"Skipping child table {doctype}")
                continue

            with open(file_path, "r") as f:
                data = json.load(f)
            
            if not data:
                continue

            print(f"Importing {len(data)} records for {doctype}...")
            
            for doc_data in data:
                try:
                    doc_data["doctype"] = doctype
                    name = doc_data.get("name")
                    
                    # Remove metadata fields to avoid version and permission errors
                    for field in ["modified", "creation", "modified_by", "owner", "idx"]:
                        if field in doc_data:
                            del doc_data[field]
                        
                    # Check if exists
                    if frappe.db.exists(doctype, name):
                        doc = frappe.get_doc(doctype, name)
                        doc.update(doc_data)
                        doc.flags.ignore_version = True
                        doc.flags.ignore_links = True
                        doc.flags.ignore_validate_update_after_submit = True
                        doc.save(ignore_permissions=True)
                    else:
                        doc = frappe.get_doc(doc_data)
                        doc.flags.ignore_version = True
                        doc.flags.ignore_links = True
                        doc.flags.ignore_validate_update_after_submit = True
                        doc.insert(ignore_permissions=True, set_name=name, set_child_names=False)
                except Exception as e:
                    print(f"Error importing {doctype} {doc_data.get('name')}: {e}")
            
        except Exception as e:
            print(f"Error importing {doctype}: {e}")

    print("Import completed.")
