import json

import frappe
from frappe import _

from church_management.api import permissions as perms

# Records before this year are stale historical data kept for reference only —
# the SPA never lists or edits them.
MIN_YEAR = 2026

CHILD_TABLES = {
    "tithes_collection": "Tithes Collection",
    "offering_collection": "Offering Collection",
    "mission_collection": "Mission Collection",
    "collection_tally": "Collection Tally",
}

# Doc-level fields the SPA is allowed to write. Totals are recomputed by
# Collection.validate() server-side, so they are deliberately excluded.
WRITABLE_FIELDS = (
    "date",
    "cost_center",
    "attendees",
    "benevolence_collection",
    "benevolence_collection_cls",
    "loose_collection",
    "loose_collection_cls",
    "sunday_school_collection",
)


@frappe.whitelist()
def get_list(year=None):
    """List collections for the SPA — 2026 onwards only."""
    perms.require_finance()

    year = int(year) if year else None
    if year and year >= MIN_YEAR:
        start, end = f"{year}-01-01", f"{year}-12-31 23:59:59"
    else:
        start, end = f"{MIN_YEAR}-01-01", "9999-12-31"

    return frappe.get_all(
        "Collection",
        filters={"date": ["between", [start, end]]},
        fields=[
            "name",
            "date",
            "docstatus",
            "all_tithes_total",
            "all_offering_total",
            "all_mission_total",
            "all_grand_total",
            "journal_entry",
            "modified",
        ],
        order_by="date desc",
    )


@frappe.whitelist()
def get_detail(name):
    """Full collection document with child tables."""
    perms.require_finance()
    frappe.has_permission("Collection", doc=name, throw=True)
    return frappe.get_doc("Collection", name).as_dict()


@frappe.whitelist()
def get_ytd_summary(year=None):
    """Year-to-date totals of submitted collections, by category."""
    perms.require_finance()

    year = int(year) if year else frappe.utils.now_datetime().year
    rows = frappe.get_all(
        "Collection",
        filters={
            "date": ["between", [f"{year}-01-01", f"{year}-12-31 23:59:59"]],
            "docstatus": 1,
        },
        fields=[
            "all_tithes_total",
            "all_offering_total",
            "all_mission_total",
            "all_grand_total",
        ],
    )
    return {
        "tithes": sum(r.all_tithes_total or 0 for r in rows),
        "offering": sum(r.all_offering_total or 0 for r in rows),
        "mission": sum(r.all_mission_total or 0 for r in rows),
        "grand_total": sum(r.all_grand_total or 0 for r in rows),
        "count": len(rows),
        "year": year,
    }


@frappe.whitelist()
def get_members():
    """All church members for the envelope-number lookup cache."""
    perms.require_finance()
    return frappe.get_all(
        "Church Member",
        fields=["name", "envelope_number", "firstname", "lastname"],
        order_by="name asc",
        limit_page_length=0,
    )


@frappe.whitelist()
def get_new_defaults():
    """Defaults for a new collection: denomination tally rows + cost center."""
    perms.require_finance()
    settings = frappe.get_single("Church Management Settings")
    denominations = frappe.get_all(
        "Denomination",
        fields=["name", "denomination", "denum_name"],
        order_by="denomination desc",
        limit_page_length=0,
    )
    return {
        "denominations": denominations,
        "default_cost_center": settings.default_cost_center,
    }


def _apply_payload(doc, payload):
    for field in WRITABLE_FIELDS:
        if field in payload:
            doc.set(field, payload.get(field))

    for fieldname, child_doctype in CHILD_TABLES.items():
        if fieldname not in payload:
            continue
        doc.set(fieldname, [])
        for row in payload.get(fieldname) or []:
            row = dict(row)
            row.pop("name", None)
            row["doctype"] = child_doctype
            doc.append(fieldname, row)


@frappe.whitelist()
def save_collection(doc):
    """Create or update a draft collection. Totals are recomputed in validate()."""
    perms.require_finance()
    payload = json.loads(doc) if isinstance(doc, str) else doc

    name = payload.get("name")
    if name:
        existing = frappe.get_doc("Collection", name)
        if existing.docstatus != 0:
            frappe.throw(_("Only draft collections can be edited."))
        frappe.has_permission("Collection", doc=name, ptype="write", throw=True)
        _apply_payload(existing, payload)
        existing.save()
        return existing.as_dict()

    new_doc = frappe.new_doc("Collection")
    _apply_payload(new_doc, payload)
    new_doc.insert()
    return new_doc.as_dict()


@frappe.whitelist()
def submit_collection(name, client_id=None):
    """Submit a draft collection — this posts the Journal Entry."""
    perms.require_finance()
    frappe.has_permission("Collection", doc=name, ptype="submit", throw=True)
    doc = frappe.get_doc("Collection", name, for_update=True)
    if doc.docstatus != 0:
        frappe.throw(_("Collection {0} is already submitted.").format(name))
    doc.submit()
    _broadcast(name, "reload", client_id)
    return doc.as_dict()


@frappe.whitelist()
def delete_collection(name, client_id=None):
    """Delete a draft collection."""
    perms.require_finance()
    frappe.has_permission("Collection", doc=name, ptype="delete", throw=True)
    doc = frappe.get_doc("Collection", name)
    if doc.docstatus != 0:
        frappe.throw(_("Only draft collections can be deleted."))
    doc.delete()
    _broadcast(name, "deleted", client_id)
    return {"deleted": name}


# ---------------------------------------------------------------------------
# Live, multi-device editing
#
# Instead of saving the whole document at once, the SPA autosaves one change
# at a time (a single entry row, a tally row, or a few header fields). Each
# change locks the Collection row (SELECT ... FOR UPDATE) so concurrent edits
# from several devices serialize instead of failing the modified-timestamp
# check, then broadcasts the change to everyone viewing the same collection.
# client_id identifies the browser tab that made the change so it can ignore
# its own echo.
# ---------------------------------------------------------------------------

SYNC_EVENT = "collection_sync"
ENTRY_TABLES = ("tithes_collection", "offering_collection", "mission_collection")
ROW_FIELDS = ("number", "amount", "account_type")


def _broadcast(name, op, client_id, **data):
    frappe.publish_realtime(
        SYNC_EVENT,
        {"op": op, "name": name, "client_id": client_id, "by": frappe.session.user, **data},
        doctype="Collection",
        docname=name,
        after_commit=True,
    )


def _locked_draft(name):
    perms.require_finance()
    frappe.has_permission("Collection", doc=name, ptype="write", throw=True)
    doc = frappe.get_doc("Collection", name, for_update=True)
    if doc.docstatus != 0:
        frappe.throw(_("Collection {0} is already submitted.").format(name))
    return doc


def _entry_row(row):
    return {
        "name": row.name,
        "idx": row.idx,
        "number": row.number or "",
        "first_name": row.first_name or "",
        "last_name": row.last_name or "",
        "amount": row.amount,
        "account_type": row.account_type or "Cash",
    }


@frappe.whitelist()
def create_draft(doc, client_id=None):
    """Create the draft on the first keystroke of a new collection.

    Two devices starting the same service (same date + MORNING/EVENING) get
    the same document: the second call returns the existing draft and the
    device merges into it instead of failing on a duplicate name.
    """
    perms.require_finance()
    payload = json.loads(doc) if isinstance(doc, str) else doc

    probe = frappe.new_doc("Collection")
    probe.date = payload.get("date")
    probe.autoname()
    if frappe.db.exists("Collection", probe.name):
        existing = frappe.get_doc("Collection", probe.name)
        if existing.docstatus != 0:
            frappe.throw(_("Collection {0} is already submitted.").format(probe.name))
        frappe.has_permission("Collection", doc=existing.name, ptype="write", throw=True)
        return existing.as_dict()

    new_doc = frappe.new_doc("Collection")
    _apply_payload(new_doc, payload)
    new_doc.insert()
    return new_doc.as_dict()


@frappe.whitelist()
def upsert_row(name, table, row, client_id=None):
    """Insert or update one tithes/offering/mission row."""
    if table not in ENTRY_TABLES:
        frappe.throw(_("Invalid table {0}").format(table))
    row = json.loads(row) if isinstance(row, str) else row
    doc = _locked_draft(name)

    values = {k: row.get(k) for k in ROW_FIELDS if k in row}
    values["amount"] = values.get("amount") or 0
    member = values.get("number") or None
    values["number"] = member
    names = frappe.db.get_value("Church Member", member, ["firstname", "lastname"]) if member else None
    if member and not names:
        frappe.throw(_("No church member with envelope {0}").format(member))
    values["first_name"], values["last_name"] = names or ("", "")

    target = None
    if row.get("name"):
        target = next((r for r in doc.get(table) if r.name == row["name"]), None)
    if target:
        target.update(values)
    else:
        # New row, or one another device deleted while this one was typing
        target = doc.append(table, values)
    doc.save()

    out = _entry_row(target)
    _broadcast(name, "row", client_id, table=table, row=out)
    return out


@frappe.whitelist()
def delete_row(name, table, row_name, client_id=None):
    if table not in ENTRY_TABLES:
        frappe.throw(_("Invalid table {0}").format(table))
    doc = _locked_draft(name)
    rows = doc.get(table)
    remaining = [r for r in rows if r.name != row_name]
    if len(remaining) != len(rows):
        doc.set(table, remaining)
        doc.save()
    _broadcast(name, "row_delete", client_id, table=table, row_name=row_name)
    return {"deleted": row_name}


@frappe.whitelist()
def set_fields(name, values, client_id=None):
    """Update header fields (date, benevolence, loose, sunday school, attendees...)."""
    values = json.loads(values) if isinstance(values, str) else values
    values = {k: v for k, v in values.items() if k in WRITABLE_FIELDS}
    doc = _locked_draft(name)
    doc.update(values)
    doc.save()
    _broadcast(name, "fields", client_id, values=values)
    return {k: doc.get(k) for k in values}


@frappe.whitelist()
def set_tally(name, denum_name, quantity=0, quantity_coins=0, client_id=None):
    doc = _locked_draft(name)
    denomination = frappe.db.get_value("Denomination", denum_name, "denomination")
    if denomination is None:
        frappe.throw(_("Unknown denomination {0}").format(denum_name))
    row = next((r for r in doc.get("collection_tally") if r.denum_name == denum_name), None)
    if not row:
        row = doc.append("collection_tally", {"denum_name": denum_name})
    row.denomination = denomination
    row.quantity = frappe.utils.cint(quantity)
    row.quantity_coins = frappe.utils.cint(quantity_coins)
    coins = row.quantity_coins if denum_name == "20" else 0
    row.total = (row.denomination or 0) * (row.quantity + coins)
    doc.save()

    out = {
        "denum_name": row.denum_name,
        "denomination": row.denomination,
        "quantity": row.quantity,
        "quantity_coins": row.quantity_coins,
        "total": row.total,
    }
    _broadcast(name, "tally", client_id, row=out)
    return out
