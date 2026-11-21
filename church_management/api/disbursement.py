import frappe
from frappe import _

from frappe.utils import getdate, nowdate

from church_management.api import permissions as perms
from church_management.church_management import disbursement_audit as audit
from church_management.church_management import finance as fin


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
                if fin.state(item) == fin.UNCLAIMED:
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
    for _f, _l, item in fin.iter_lines(doc):
        st = fin.state(item)
        if st == fin.VOIDED:
            continue
        purpose = item.get("purpose") or "Uncategorized"
        summary.setdefault(purpose, {"total": 0, "claimed": 0, "unclaimed": 0})
        amount = item.get("amount") or 0
        summary[purpose]["total"] += amount
        summary[purpose]["claimed" if st == fin.CLAIMED else "unclaimed"] += amount
    return summary


@frappe.whitelist()
def claim_item(disbursement_name, child_doctype, child_name, received_by=None, received_date=None, source=None,
               remarks=None, paid_by=None, creditor=None, creditor_paid_date=None, creditor_reference=None):
    """Mark a disbursement item as claimed — paid with church money, or paid
    by a creditor on the church's behalf (which records a payable)."""
    perms.require_finance()
    if not source:
        frappe.throw(_("Source is mandatory when claiming an item"))

    frappe.has_permission("Disbursement", doc=disbursement_name, ptype="write", throw=True)
    doc = frappe.get_doc("Disbursement", disbursement_name)
    _field, _label, row = fin.find_line(doc, child_name)
    if fin.state(row) == fin.CLAIMED:
        frappe.throw(_("This item is already claimed."))
    if fin.state(row) == fin.VOIDED:
        frappe.throw(_("This item is voided. Restore it before claiming."))
    _apply_claim(row, received_by, received_date, source, remarks, paid_by, creditor, creditor_paid_date, creditor_reference)
    doc.flags.line_actions = {row.name: {"action": "Claim"}}
    doc.save()
    return _result(doc)


def _apply_claim(row, received_by, received_date, source, remarks, paid_by, creditor, creditor_paid_date, creditor_reference):
    row.status = fin.CLAIMED
    row.source = source
    row.paid_by = paid_by or fin.CHURCH
    if row.paid_by == fin.CREDITOR:
        row.creditor = creditor
        row.creditor_paid_date = creditor_paid_date
        row.creditor_reference = creditor_reference
        row.received_by = received_by or None
        row.received_date = received_date or creditor_paid_date
    else:
        row.creditor = row.creditor_paid_date = row.creditor_reference = None
        row.received_by = received_by
        row.received_date = received_date
    if remarks is not None:
        row.remarks = remarks


def _result(doc, **extra):
    return {"success": True, "warnings": doc.flags.audit_warnings or [], **extra}


@frappe.whitelist()
def claim_items_bulk(disbursement_name, child_names, received_by=None, received_date=None, source=None, remarks=None,
                     paid_by=None, creditor=None, creditor_paid_date=None, creditor_reference=None):
    """Mark multiple disbursement items as claimed in one save."""
    perms.require_finance()
    child_names = frappe.parse_json(child_names) if isinstance(child_names, str) else child_names
    if not source:
        frappe.throw(_("Source is mandatory when claiming items"))
    if not child_names:
        frappe.throw(_("No items selected"))

    frappe.has_permission("Disbursement", doc=disbursement_name, ptype="write", throw=True)
    doc = frappe.get_doc("Disbursement", disbursement_name)

    target = set(child_names)
    matched = set()
    for _f, _l, row in fin.iter_lines(doc):
        if row.name in target and fin.state(row) == fin.UNCLAIMED:
            _apply_claim(row, received_by, received_date, source, remarks, paid_by, creditor, creditor_paid_date, creditor_reference)
            matched.add(row.name)

    missing = target - matched
    if missing:
        frappe.throw(_("Some items not found, voided or already claimed: {0}").format(", ".join(missing)))

    doc.flags.line_actions = {n: {"action": "Claim"} for n in matched}
    doc.save()
    return _result(doc, claimed=list(matched))


# ---------------------------------------------------------------- corrections

def _load_line(disbursement_name, child_name):
    perms.require_finance()
    frappe.has_permission("Disbursement", doc=disbursement_name, ptype="write", throw=True)
    doc = frappe.get_doc("Disbursement", disbursement_name)
    field, label, row = fin.find_line(doc, child_name)
    return doc, row


@frappe.whitelist()
def reverse_claim(disbursement_name, child_name, reason):
    """Set a claimed line back to Unclaimed and clear Received By/Date."""
    doc, row = _load_line(disbursement_name, child_name)
    if fin.state(row) != fin.CLAIMED:
        frappe.throw(_("Only a claimed line can be reversed."))
    audit.require_reason(reason, _("reversing a claim"))
    row.status = fin.UNCLAIMED
    row.received_by = None
    row.received_date = None
    doc.flags.line_actions = {row.name: {"action": "Reverse Claim", "reason": reason}}
    doc.save()
    return _result(doc)


EDIT_CLAIM_FIELDS = ("amount", "received_by", "received_date", "source")


@frappe.whitelist()
def edit_claim(disbursement_name, child_name, changes, reason):
    """Correct a claimed line: Amount, Received By, Received Date or Source Account."""
    doc, row = _load_line(disbursement_name, child_name)
    if fin.state(row) != fin.CLAIMED:
        frappe.throw(_("Only a claimed line can be edited this way."))
    changes = frappe.parse_json(changes) if isinstance(changes, str) else (changes or {})
    bad = set(changes) - set(EDIT_CLAIM_FIELDS)
    if bad:
        frappe.throw(_("Edit claim can only change {0}.").format(", ".join(EDIT_CLAIM_FIELDS)))
    audit.require_reason(reason, _("editing a claim"))
    for f, v in changes.items():
        row.set(f, float(v or 0) if f == "amount" else (v or None))
    doc.flags.line_actions = {row.name: {"action": "Edit Claim", "reason": reason}}
    doc.save()
    return _result(doc)


@frappe.whitelist()
def void_line(disbursement_name, child_name, reason):
    """Discontinue an unclaimed line: it stays visible but is counted nowhere."""
    doc, row = _load_line(disbursement_name, child_name)
    if fin.state(row) != fin.UNCLAIMED:
        frappe.throw(_("Only an unclaimed line can be voided."))
    audit.require_reason(reason, _("voiding a line"))
    row.status = fin.VOIDED
    row.void_reason = reason.strip()
    doc.flags.line_actions = {row.name: {"action": "Void", "reason": reason}}
    doc.save()
    return _result(doc)


@frappe.whitelist()
def unvoid_line(disbursement_name, child_name, reason):
    """Restore a voided line to Unclaimed."""
    doc, row = _load_line(disbursement_name, child_name)
    if fin.state(row) != fin.VOIDED:
        frappe.throw(_("This line is not voided."))
    audit.require_reason(reason, _("restoring a voided line"))
    row.status = fin.UNCLAIMED
    doc.flags.line_actions = {row.name: {"action": "Unvoid", "reason": reason}}
    doc.save()
    return _result(doc)


@frappe.whitelist()
def get_history(disbursement_name, child_name=None):
    """Audit trail for a monthly document, or for one of its lines."""
    perms.require_finance()
    frappe.has_permission("Disbursement", doc=disbursement_name, throw=True)
    return audit.history(disbursement=None if child_name else disbursement_name, row_name=child_name)


@frappe.whitelist()
def get_overdue_lines(year=None):
    """Unclaimed lines whose due date has passed, oldest first, for review."""
    perms.require_finance()
    today = getdate(nowdate())
    out = []
    for ln in fin.collect_lines(year=int(year) if year else None, include_cancelled=False):
        if ln.kind != "line" or not ln.pending or not ln.due or ln.due >= today:
            continue
        out.append({
            "disbursement": ln.disbursement, "month": ln.month, "year": ln.year, "section": ln.section,
            "row_name": ln.row_name, "label": ln.payee or ln.description or ln.remarks or ln.purpose,
            "description": ln.description, "payee": ln.payee, "purpose": ln.purpose, "department": ln.department,
            "fund": ln.fund, "source": ln.source, "amount": ln.amount, "due": str(ln.due),
            "days_overdue": (today - ln.due).days, "received_by": ln.received_by,
            "child_doctype": fin.CHILD_DOCTYPE[ln.field],
        })
    out.sort(key=lambda r: (-r["days_overdue"], r["disbursement"]))
    return out


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
def update_item(disbursement_name, child_doctype, child_name, updates, reason=None):
    """Update editable fields on a line. Claimed lines may only change their
    purpose or department here; use edit_claim for amount, receiver, date or source."""
    perms.require_finance()
    updates = frappe.parse_json(updates) if isinstance(updates, str) else updates

    frappe.has_permission("Disbursement", doc=disbursement_name, ptype="write", throw=True)
    doc = frappe.get_doc("Disbursement", disbursement_name)
    _f, _l, row = fin.find_line(doc, child_name)
    st = fin.state(row)
    if st == fin.VOIDED:
        frappe.throw(_("This line is voided. Restore it before editing."))
    allowed = ("purpose", "department", "description", "remarks") if st == fin.CLAIMED else (
        "worker", "purpose", "department", "source", "is_planned", "amount", "description", "remarks")
    blocked = [k for k in updates if k not in allowed and k in ("worker", "source", "amount", "is_planned")]
    if blocked:
        frappe.throw(_("This line is claimed. Use Edit claim to change {0}.").format(", ".join(blocked)))
    columns = set(row.meta.get_valid_columns())
    for k in allowed:
        if k not in updates or k not in columns:
            continue
        v = updates[k]
        if k == "amount":
            v = float(v or 0)
        elif k == "is_planned":
            v = int(v or 0)
        row.set(k, v)
    if reason:
        doc.flags.audit_reason = reason
    doc.save()
    return _result(doc)

@frappe.whitelist()
def add_item(disbursement_name, table_field, item_data, reason=None):
    """Add a new item to a specific child table."""
    perms.require_finance()
    if isinstance(item_data, str):
        import json
        item_data = json.loads(item_data)

    frappe.has_permission("Disbursement", doc=disbursement_name, ptype="write", throw=True)
    doc = frappe.get_doc("Disbursement", disbursement_name)
    
    if table_field not in _all_child_fields():
        frappe.throw(_("Invalid table field"))

    item_data = {k: v for k, v in (item_data or {}).items() if k not in ("status", "payable", "name")}
    doc.append(table_field, item_data)
    doc.flags.audit_reason = reason
    doc.save()
    return _result(doc)

@frappe.whitelist()
def delete_item(disbursement_name, child_name, reason=None):
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

    doc.flags.audit_reason = reason
    doc.save()
    return _result(doc)

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
TEMPLATE_ROW_FIELDS = ("worker", "description", "purpose", "amount", "source", "department")


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
            {"name": row.name, **{f: row.get(f) for f in TEMPLATE_ROW_FIELDS if f in row.as_dict()}}
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
            meta_fields = set(frappe.get_meta(doc.meta.get_field(table).options).get_valid_columns())
            doc.append(
                table,
                {
                    **{f: row.get(f) for f in TEMPLATE_ROW_FIELDS if f in meta_fields and row.get(f) not in (None, "")},
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


@frappe.whitelist()
def get_departments():
    """Departments for line pickers."""
    perms.require_finance()
    return frappe.get_all("Department Name", fields=["name"], order_by="name asc", limit_page_length=0)


@frappe.whitelist()
def get_creditors():
    """Active creditors for the Paid by picker."""
    perms.require_finance()
    return frappe.get_all("Creditor", filters={"active": 1}, fields=["name"], order_by="name asc")
