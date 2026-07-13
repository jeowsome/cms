import json

import frappe
from frappe import _

from church_management.api import permissions as perms

# Fields the SPA may read and write on Church Member.
FIELDS = (
    "envelope_number",
    "firstname",
    "lastname",
    "birthday",
    "address",
    "contact_number",
    "email_address",
    "member_since",
)


@frappe.whitelist()
def get_list():
    """All church members with contact details for the Members page."""
    perms.require_finance()
    return frappe.get_all(
        "Church Member",
        fields=["name", *FIELDS],
        order_by="lastname asc, firstname asc",
        limit_page_length=0,
    )


@frappe.whitelist()
def save_member(doc):
    """Create or update a church member.

    Church Member is autonamed from envelope_number, so changing the envelope
    on an existing member renames the document — Frappe rewrites every link
    (collection rows included) automatically.
    """
    perms.require_finance()
    payload = json.loads(doc) if isinstance(doc, str) else doc

    envelope = str(payload.get("envelope_number") or "").strip()
    if not envelope:
        frappe.throw(_("Envelope number is required."))
    if not (payload.get("firstname") or "").strip():
        frappe.throw(_("First name is required."))

    name = payload.get("name")
    duplicate = frappe.db.exists("Church Member", {"envelope_number": envelope})
    if duplicate and duplicate != name:
        frappe.throw(_("Envelope number {0} already belongs to another member.").format(envelope))

    if name:
        member = frappe.get_doc("Church Member", name)
        for field in FIELDS:
            if field in payload:
                member.set(field, payload.get(field) or None)
        member.envelope_number = envelope
        member.save()
        if member.name != envelope:
            frappe.rename_doc("Church Member", member.name, envelope)
            member = frappe.get_doc("Church Member", envelope)
    else:
        member = frappe.new_doc("Church Member")
        for field in FIELDS:
            member.set(field, payload.get(field) or None)
        member.envelope_number = envelope
        member.insert()

    return {f: member.get(f) for f in ("name", *FIELDS)}
