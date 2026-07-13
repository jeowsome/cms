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
def submit_collection(name):
    """Submit a draft collection — this posts the Journal Entry."""
    perms.require_finance()
    frappe.has_permission("Collection", doc=name, ptype="submit", throw=True)
    doc = frappe.get_doc("Collection", name)
    if doc.docstatus != 0:
        frappe.throw(_("Collection {0} is already submitted.").format(name))
    doc.submit()
    return doc.as_dict()


@frappe.whitelist()
def delete_collection(name):
    """Delete a draft collection."""
    perms.require_finance()
    frappe.has_permission("Collection", doc=name, ptype="delete", throw=True)
    doc = frappe.get_doc("Collection", name)
    if doc.docstatus != 0:
        frappe.throw(_("Only draft collections can be deleted."))
    doc.delete()
    return {"deleted": name}
