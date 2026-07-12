import frappe
from frappe import _

from church_management.api import permissions as perms


@frappe.whitelist()
def get_list(year=None):
    perms.require_finance()
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

        active_weeks = _active_week_count(doc.month_recorded, doc.year_recorded)
        active_fields = []
        for i in range(1, active_weeks + 1):
            active_fields.append(f"disbursement_item_week_{i}")
            active_fields.append(f"expense_item_week_{i}")
        active_fields.append("monthly_disbursement_items")
        active_fields.append("monthly_expense_items")

        for table_field in active_fields:
            for item in doc.get(table_field) or []:
                claimed = item.get("status") == "Claimed" or (
                    item.get("received_by") and item.get("received_date")
                )
                if not claimed:
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
    perms.require_finance()
    frappe.has_permission("Disbursement", doc=name, throw=True)
    doc = frappe.get_doc("Disbursement", name)
    return doc.as_dict()


@frappe.whitelist()
def get_summary(name):
    """Get disbursement summary broken down by purpose."""
    perms.require_finance()
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
    perms.require_finance()
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
def claim_items_bulk(disbursement_name, child_names, received_by, received_date, source, remarks=None):
    """Mark multiple disbursement items as claimed in one save."""
    perms.require_finance()
    import json as _json
    if isinstance(child_names, str):
        child_names = _json.loads(child_names)
    if not source:
        frappe.throw(_("Source is mandatory when claiming items"))
    if not child_names:
        frappe.throw(_("No items selected"))

    frappe.has_permission("Disbursement", doc=disbursement_name, ptype="write", throw=True)
    doc = frappe.get_doc("Disbursement", disbursement_name)

    target = set(child_names)
    matched = set()
    for table_field in _all_child_fields():
        for row in doc.get(table_field) or []:
            if row.name in target and row.get("status") != "Claimed":
                row.status = "Claimed"
                row.received_by = received_by
                row.received_date = received_date
                row.source = source
                if remarks is not None:
                    row.remarks = remarks
                matched.add(row.name)

    missing = target - matched
    if missing:
        frappe.throw(_("Some items not found or already claimed: {0}").format(", ".join(missing)))

    doc.save()
    return {"success": True, "claimed": list(matched)}


@frappe.whitelist()
def get_workers():
    """Get list of active church workers for claim modal."""
    perms.require_finance()
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
    perms.require_finance()
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
                if "amount" in updates:
                    new_amount = float(updates["amount"] or 0)
                    if new_amount != (row.amount or 0):
                        if not row.get("amount_edited"):
                            row.original_amount = row.amount
                            row.amount_edited = 1
                        row.amount = new_amount
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
    perms.require_finance()
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
    perms.require_finance()
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
    perms.require_finance()
    return frappe.get_all("Disbursement Purpose", filters={"active": 1}, fields=["name"], order_by="name asc")

@frappe.whitelist()
def get_source_accounts():
    """Get Source Accounts (Bank/Cash)."""
    perms.require_finance()
    return frappe.get_all(
        "Account",
        filters={"is_group": 0, "account_type": ["in", ["Bank", "Cash"]]},
        fields=["name", "account_name"],
        order_by="account_name asc"
    )

@frappe.whitelist()
def get_available_months(year=None):
    """Get months that don't have a disbursement yet for generating new ones."""
    perms.require_finance()
    import calendar

    existing = frappe.get_all("Disbursement", pluck="name")
    year = int(year) if year else frappe.utils.now_datetime().year

    available = []
    for month_num in range(1, 13):
        month_name = calendar.month_name[month_num]
        doc_name = f"{month_name}-{year}"
        if doc_name not in existing:
            available.append({"month": month_name, "year": year, "name": doc_name})

    return available


@frappe.whitelist()
def get_templates():
    """List Disbursement Templates with stats for the create-from-template preview.

    Weekly rows are replicated into every week of the generated month, so the
    frontend multiplies weekly_amount by the month's Sunday count for estimates.
    """
    perms.require_finance()
    # Templates pointing at a company that no longer exists (old test data)
    # can never generate; flag them so pickers can filter and the management
    # page can still show them for cleanup.
    valid_companies = set(frappe.get_all("Company", pluck="name"))
    templates = frappe.get_all(
        "Disbursement Template", fields=["name", "company"], order_by="name asc"
    )
    for t in templates:
        t.company_valid = t.company in valid_companies
        doc = frappe.get_doc("Disbursement Template", t.name)
        weekly_rows = list(doc.weekly_allowances or []) + list(doc.weekly_activity or [])
        # Matches generate_disbursements: monthly_disbursement is intentionally
        # not generated; only mission_support + monthly_expenses land monthly.
        monthly_rows = list(doc.mission_support or []) + list(doc.monthly_expenses or [])
        t.weekly_item_count = len(weekly_rows)
        t.weekly_amount = sum((r.amount or 0) for r in weekly_rows)
        t.monthly_item_count = len(monthly_rows)
        t.monthly_amount = sum((r.amount or 0) for r in monthly_rows)
    return templates


TEMPLATE_TABLES = ("weekly_allowances", "weekly_activity", "mission_support", "monthly_expenses")
TEMPLATE_ROW_FIELDS = ("worker", "description", "purpose", "amount", "source")


@frappe.whitelist()
def get_template(name):
    """Full Disbursement Template with its editable child tables."""
    perms.require_finance()
    frappe.has_permission("Disbursement Template", doc=name, throw=True)
    doc = frappe.get_doc("Disbursement Template", name)
    out = {
        "name": doc.name,
        "company": doc.company,
        "disbursement_year": doc.disbursement_year,
    }
    for table in TEMPLATE_TABLES:
        out[table] = [
            {"name": row.name, **{f: row.get(f) for f in TEMPLATE_ROW_FIELDS}}
            for row in (doc.get(table) or [])
        ]
    return out


@frappe.whitelist()
def save_template(payload):
    """Create or update a Disbursement Template (name auto-derives as DT - {year})."""
    perms.require_finance()
    payload = frappe.parse_json(payload)

    name = payload.get("name")
    if name:
        frappe.has_permission("Disbursement Template", doc=name, ptype="write", throw=True)
        doc = frappe.get_doc("Disbursement Template", name)
    else:
        frappe.has_permission("Disbursement Template", ptype="create", throw=True)
        doc = frappe.new_doc("Disbursement Template")

    if not payload.get("company"):
        frappe.throw(_("Company is mandatory"))
    if not payload.get("disbursement_year"):
        frappe.throw(_("Year is mandatory"))

    doc.company = payload["company"]
    doc.disbursement_year = int(payload["disbursement_year"])

    for table in TEMPLATE_TABLES:
        if table not in payload:
            continue
        doc.set(table, [])
        for row in payload[table] or []:
            doc.append(
                table,
                {
                    **{f: row.get(f) for f in TEMPLATE_ROW_FIELDS if row.get(f) not in (None, "")},
                    "is_planned": 1,
                },
            )

    doc.save()
    return {"name": doc.name}


@frappe.whitelist()
def delete_template(name):
    """Delete a Disbursement Template (blocked if disbursements link to it)."""
    perms.require_finance()
    frappe.has_permission("Disbursement Template", doc=name, ptype="delete", throw=True)
    frappe.delete_doc("Disbursement Template", name)
    return {"success": True}


@frappe.whitelist()
def get_companies():
    """Companies for the template editor select."""
    perms.require_finance()
    return frappe.get_all("Company", fields=["name"], order_by="name asc")


@frappe.whitelist()
def create_from_template(template_name, year, months):
    """Generate Disbursement docs from a Disbursement Template for the given months."""
    perms.require_finance()
    frappe.has_permission("Disbursement", ptype="create", throw=True)
    frappe.has_permission("Disbursement Template", doc=template_name, throw=True)

    months = frappe.parse_json(months)
    year = int(year)
    if not months:
        frappe.throw(_("Select at least one month"))

    existing = [m for m in months if frappe.db.exists("Disbursement", f"{m}-{year}")]
    if existing:
        frappe.throw(
            _("Disbursement already exists for: {0}").format(
                ", ".join(f"{m}-{year}" for m in existing)
            )
        )

    from church_management.church_management.doctype.disbursement_template.disbursement_template import (
        generate_disbursements,
    )

    created = generate_disbursements(template_name, months, year)
    return {"created": created}


def _all_child_fields():
    """Return all child table fieldnames on Disbursement."""
    fields = []
    for i in range(1, 6):
        fields.append(f"disbursement_item_week_{i}")
        fields.append(f"expense_item_week_{i}")
    fields.append("monthly_disbursement_items")
    fields.append("monthly_expense_items")
    return fields


def _active_week_count(month_recorded, year_recorded):
    """Number of Sundays in the disbursement's month (capped at 5)."""
    import calendar
    if not month_recorded or not year_recorded:
        return 5
    months = ["January","February","March","April","May","June",
             "July","August","September","October","November","December"]
    try:
        month_idx = months.index(month_recorded) + 1
        year = int(year_recorded)
    except (ValueError, TypeError):
        return 5
    sundays = 0
    days = calendar.monthrange(year, month_idx)[1]
    import datetime
    for day in range(1, days + 1):
        if datetime.date(year, month_idx, day).weekday() == 6:
            sundays += 1
    return min(sundays, 5)


def _claimable_child_fields():
    """Child tables that participate in the claim workflow (have a status field)."""
    fields = []
    for i in range(1, 6):
        fields.append(f"disbursement_item_week_{i}")
        fields.append(f"expense_item_week_{i}")
    return fields
