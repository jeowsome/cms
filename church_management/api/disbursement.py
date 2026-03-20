import frappe
from frappe import _


@frappe.whitelist()
def get_list(year=None):
    """Get list of disbursements with summary fields."""
    filters = {"year_recorded": [">=", 2026]}
    if year:
        filters["year_recorded"] = year

    disbursements = frappe.get_all(
        "Disbursement",
        filters=filters,
        fields=[
            "name",
            "docstatus",
            "month_recorded",
            "year_recorded",
            "total_disbursed",
            "total_amount_disbursed",
            "creation",
            "modified",
        ],
        order_by="creation desc",
    )

    for d in disbursements:
        doc = frappe.get_doc("Disbursement", d.name)
        unclaimed_count = 0
        unclaimed_amount = 0.0

        for table_field in _all_child_fields():
            for item in doc.get(table_field) or []:
                if item.get("status") != "Claimed":
                    unclaimed_count += 1
                    unclaimed_amount += (item.get("amount") or 0.0)

        d.unclaimed_count = unclaimed_count
        d.unclaimed_amount = unclaimed_amount
        d.planned_items = d.total_disbursed
        d.planned_amount = d.total_amount_disbursed

    return disbursements


@frappe.whitelist()
def get_detail(name):
    """Get full disbursement document with all child tables."""
    frappe.has_permission("Disbursement", doc=name, throw=True)
    doc = frappe.get_doc("Disbursement", name)
    return doc.as_dict()


@frappe.whitelist()
def get_summary(name):
    """Get disbursement summary broken down by purpose."""
    frappe.has_permission("Disbursement", doc=name, throw=True)

    doc = frappe.get_doc("Disbursement", name)
    summary = {}

    for week_num in range(1, 6):
        items = doc.get(f"disbursement_item_week_{week_num}") or []
        expenses = doc.get(f"expense_item_week_{week_num}") or []

        for item in items:
            purpose = item.get("purpose") or "Uncategorized"
            summary.setdefault(purpose, {"total": 0, "claimed": 0, "unclaimed": 0})
            amount = item.get("amount") or 0
            summary[purpose]["total"] += amount
            if item.get("status") == "Claimed":
                summary[purpose]["claimed"] += amount
            else:
                summary[purpose]["unclaimed"] += amount

        for exp in expenses:
            purpose = exp.get("purpose") or "Uncategorized"
            summary.setdefault(purpose, {"total": 0, "claimed": 0, "unclaimed": 0})
            amount = exp.get("amount") or 0
            summary[purpose]["total"] += amount
            if exp.get("status") == "Claimed":
                summary[purpose]["claimed"] += amount
            else:
                summary[purpose]["unclaimed"] += amount

    return summary


@frappe.whitelist()
def claim_item(disbursement_name, child_doctype, child_name, received_by, received_date, source=None, remarks=None):
    """Mark a disbursement item as claimed."""
    if not source:
        frappe.throw(_("Source is mandatory when claiming an item"))

    frappe.has_permission("Disbursement", doc=disbursement_name, ptype="write", throw=True)

    doc = frappe.get_doc("Disbursement", disbursement_name)

    # Find the child row
    found = False
    for table_field in _all_child_fields():
        for row in doc.get(table_field) or []:
            if row.name == child_name:
                row.status = "Claimed"
                row.received_by = received_by
                row.received_date = received_date
                row.source = source
                if remarks is not None:
                    row.remarks = remarks
                found = True
                break
        if found:
            break

    if not found:
        frappe.throw(_("Item not found in disbursement"))

    doc.save()
    return {"success": True}


@frappe.whitelist()
def get_workers():
    """Get list of active church workers for claim modal."""
    return frappe.get_all(
        "Church Worker",
        filters={"active": 1},
        fields=["name", "full_name"],
        order_by="full_name asc",
        limit_page_length=0,
    )

@frappe.whitelist()
def update_item(disbursement_name, child_doctype, child_name, updates):
    """Update editable fields on a sub-item."""
    if isinstance(updates, str):
        import json
        updates = json.loads(updates)
        
    frappe.has_permission("Disbursement", doc=disbursement_name, ptype="write", throw=True)
    doc = frappe.get_doc("Disbursement", disbursement_name)

    found = False
    for table_field in _all_child_fields():
        for row in doc.get(table_field) or []:
            if row.name == child_name:
                if row.status == "Claimed":
                    frappe.throw(_("Cannot edit a claimed item"))
                # Allowed fields to update
                if "worker" in updates and hasattr(row, 'worker'):
                    row.worker = updates["worker"]
                if "purpose" in updates:
                    row.purpose = updates["purpose"]
                if "source" in updates:
                    row.source = updates["source"]
                if "is_planned" in updates and hasattr(row, 'is_planned'):
                    row.is_planned = int(updates["is_planned"])
                found = True
                break
        if found:
            break

    if not found:
        frappe.throw(_("Item not found in disbursement"))

    doc.save()
    return {"success": True}

@frappe.whitelist()
def add_item(disbursement_name, table_field, item_data):
    """Add a new item to a specific child table."""
    if isinstance(item_data, str):
        import json
        item_data = json.loads(item_data)
        
    frappe.has_permission("Disbursement", doc=disbursement_name, ptype="write", throw=True)
    doc = frappe.get_doc("Disbursement", disbursement_name)
    
    if table_field not in _all_child_fields():
        frappe.throw(_("Invalid table field"))

    doc.append(table_field, item_data)
    doc.save()
    return {"success": True}

@frappe.whitelist()
def delete_item(disbursement_name, child_name):
    """Delete an item from a child table."""
    frappe.has_permission("Disbursement", doc=disbursement_name, ptype="write", throw=True)
    doc = frappe.get_doc("Disbursement", disbursement_name)
    
    found = False
    for table_field in _all_child_fields():
        rows = doc.get(table_field) or []
        new_rows = []
        for row in rows:
            if row.name == child_name:
                if row.status == "Claimed":
                    frappe.throw(_("Cannot delete a claimed item"))
                found = True
                continue
            new_rows.append(row)
            
        if found:
            doc.set(table_field, new_rows)
            break
            
    if not found:
        frappe.throw(_("Item not found or already deleted"))
        
    doc.save()
    return {"success": True}

@frappe.whitelist()
def get_purposes():
    """Get active disbursement purposes."""
    return frappe.get_all("Disbursement Purpose", filters={"active": 1}, fields=["name"], order_by="name asc")

@frappe.whitelist()
def get_source_accounts():
    """Get Source Accounts (Bank/Cash)."""
    return frappe.get_all(
        "Account", 
        filters={"is_group": 0, "account_type": ["in", ["Bank", "Cash"]]}, 
        fields=["name", "account_name"], 
        order_by="account_name asc"
    )

@frappe.whitelist()
def get_available_months():
    """Get months that don't have a disbursement yet for generating new ones."""
    import calendar

    existing = frappe.get_all("Disbursement", pluck="name")
    current_year = frappe.utils.now_datetime().year

    available = []
    for month_num in range(1, 13):
        month_name = calendar.month_name[month_num]
        doc_name = f"{month_name}-{current_year}"
        if doc_name not in existing:
            available.append({"month": month_name, "year": current_year, "name": doc_name})

    return available


def _all_child_fields():
    """Return all child table fieldnames on Disbursement."""
    fields = []
    for i in range(1, 6):
        fields.append(f"disbursement_item_week_{i}")
        fields.append(f"expense_item_week_{i}")
    fields.append("monthly_disbursement_items")
    fields.append("monthly_expense_items")
    return fields
