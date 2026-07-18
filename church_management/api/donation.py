"""SPA endpoints for department donation records.

Visibility model: each Donation doc belongs to a department and is
`assigned_to` one user. A user sees the departments they are assigned to;
users assigned to the Pasig Admin department — and Administrator / System
Manager — see every department. Records before 2026 are historical and never
listed or edited here.
"""
import json

import frappe
from frappe import _

from church_management.api import permissions as perms
from church_management.church_management.doctype.donation_purpose.donation_purpose import (
    find_similar,
)

MIN_YEAR = 2026

ITEM_FIELDS = (
    "date_donated",
    "amount_donated",
    "donation_type",
    "purpose",
    "description",
)

EXPENSE_FIELDS = (
    "date_spent",
    "amount_spent",
    "description",
)


def _visible_filters(year=None, department=None):
    """List filters for the current user; None means nothing is visible."""
    if year:
        year = int(year)
        if year < MIN_YEAR:
            return None
        filters = {"year": year}
    else:
        filters = {"year": [">=", MIN_YEAR]}

    if perms.is_donation_admin():
        if department:
            filters["department"] = department
    else:
        # Record-level visibility: a user sees exactly the records they were
        # invited to (assigned_to or assignees), nothing else.
        names = perms.donation_record_names()
        if not names:
            return None
        filters["name"] = ["in", names]
        if department:
            filters["department"] = department
    return filters


def _is_recorder(doc, user=None):
    user = user or frappe.session.user
    return doc.assigned_to == user or user in {a.user for a in doc.get("assignees")}


def _require_can_view(doc):
    if doc.year and int(doc.year) < MIN_YEAR:
        frappe.throw(_("Donations before {0} are read-only history.").format(MIN_YEAR))
    if perms.is_donation_admin():
        return
    if not _is_recorder(doc):
        frappe.throw(
            _("You can only view donation records you have been invited to."),
            frappe.PermissionError,
        )


@frappe.whitelist()
def get_list(year=None, department=None):
    """Donation records for the SPA — 2026 onwards, department-scoped."""
    perms.require_donation_access()
    filters = _visible_filters(year, department)
    if filters is None:
        return []
    rows = frappe.get_all(
        "Donation",
        filters=filters,
        fields=[
            "name",
            "department",
            "year",
            "assigned_to",
            "total_donated_cash_amount",
            "total_donated_cashless_amount",
            "total_donated_amount",
            "total_mission_amount",
            "total_expenses",
            "modified",
        ],
        order_by="year desc, department asc",
        ignore_permissions=True,
    )
    # Attach every recorder (assigned_to + invited assignees) for display.
    assignee_map = {}
    if rows:
        for a in frappe.get_all(
            "Donation Assignee",
            filters={"parent": ["in", [r.name for r in rows]], "parenttype": "Donation"},
            fields=["parent", "user"],
        ):
            assignee_map.setdefault(a.parent, []).append(a.user)
    for r in rows:
        extra = [u for u in assignee_map.get(r.name, []) if u != r.assigned_to]
        r["recorders"] = ([r.assigned_to] if r.assigned_to else []) + extra
    return rows


@frappe.whitelist()
def get_detail(name):
    """Full donation document with items."""
    perms.require_donation_access()
    doc = frappe.get_doc("Donation", name)
    _require_can_view(doc)
    return doc.as_dict()


def _apply_items(doc, payload):
    """Rebuild the child table from the payload. Approved rows are posted to
    the ledger, so they are immutable here: edits to them are ignored and
    rows missing from the payload are put back."""
    if "donated_amounts" not in payload:
        return

    existing = {r.name: r for r in doc.get("donated_amounts")}
    children = []
    kept = set()
    for row in payload.get("donated_amounts") or []:
        orig = existing.get(row.get("name"))
        if orig is not None:
            kept.add(orig.name)
            if orig.approval_status != "Approved":
                for field in ITEM_FIELDS:
                    orig.set(field, row.get(field))
            children.append(orig)
        else:
            clean = {field: row.get(field) for field in ITEM_FIELDS}
            clean["doctype"] = "Donation Item"
            children.append(clean)

    for r in doc.get("donated_amounts"):
        if r.approval_status == "Approved" and r.name not in kept:
            children.append(r)

    doc.set("donated_amounts", [])
    for child in children:
        doc.append("donated_amounts", child)


def _apply_expenses(doc, payload):
    """Rebuild the expenses child table from the payload. Expenses never post
    to the ledger, so unlike donation items there are no locked rows."""
    if "expenses" not in payload:
        return
    doc.set("expenses", [])
    for row in payload.get("expenses") or []:
        clean = {field: row.get(field) for field in EXPENSE_FIELDS}
        clean["doctype"] = "Donation Expense Item"
        doc.append("expenses", clean)


def _pending_rows(doc):
    return {r.name for r in doc.get("donated_amounts") if r.approval_status == "Pending"}


def _donation_admin_users():
    """Users who should receive mission-approval notifications."""
    admins = set(
        frappe.get_all(
            "Has Role",
            filters={"role": "System Manager", "parenttype": "User"},
            pluck="parent",
            distinct=True,
        )
    )
    admins.add("Administrator")
    admin_donations = frappe.get_all(
        "Donation",
        filters={"department": perms.DONATION_ADMIN_DEPARTMENT},
        fields=["name", "assigned_to"],
    )
    admins |= {d.assigned_to for d in admin_donations}
    if admin_donations:
        admins |= set(
            frappe.get_all(
                "Donation Assignee",
                filters={
                    "parent": ["in", [d.name for d in admin_donations]],
                    "parenttype": "Donation",
                },
                pluck="user",
            )
        )
    return {a for a in admins if a}


def _notify_admins(action, payload):
    for user in _donation_admin_users():
        frappe.publish_realtime(
            "donation_event",
            {"action": action, "payload": payload},
            user=user,
            after_commit=True,
        )


def _emit_new_pending(doc, before_names):
    """Realtime-notify admins when a save introduced new mission items that
    await approval."""
    new_rows = [
        r
        for r in doc.get("donated_amounts")
        if r.approval_status == "Pending" and r.name not in before_names
    ]
    if not new_rows:
        return
    _notify_admins(
        "mission_pending",
        {
            "donation": doc.name,
            "department": doc.department,
            "year": doc.year,
            "count": len(new_rows),
            "total": sum(r.amount_donated or 0 for r in new_rows),
            "by": frappe.session.user,
        },
    )


@frappe.whitelist()
def save_donation(doc):
    """Create (admin only) or update a donation. Totals are recomputed in
    before_save(); purpose links are validated by the framework, so an item
    can never reference a purpose that does not exist."""
    perms.require_donation_access()
    payload = json.loads(doc) if isinstance(doc, str) else doc

    name = payload.get("name")
    if name:
        existing = frappe.get_doc("Donation", name)
        _require_can_view(existing)
        pending_before = _pending_rows(existing)
        _apply_items(existing, payload)
        _apply_expenses(existing, payload)
        if perms.is_donation_admin() and "assigned_to" in payload:
            existing.assigned_to = payload.get("assigned_to") or None
        existing.save(ignore_permissions=True)
        _emit_new_pending(existing, pending_before)
        return existing.as_dict()

    perms.require_donation_admin()
    department = (payload.get("department") or "").strip()
    year = int(payload.get("year") or 0)
    if not department:
        frappe.throw(_("Department is required."))
    if year < MIN_YEAR:
        frappe.throw(_("Year must be {0} or later.").format(MIN_YEAR))
    if frappe.db.exists("Donation", {"department": department, "year": year}):
        frappe.throw(
            _("A donation record for {0} {1} already exists.").format(department, year)
        )

    new_doc = frappe.new_doc("Donation")
    new_doc.department = department
    new_doc.year = year
    new_doc.assigned_to = payload.get("assigned_to") or None
    _apply_items(new_doc, payload)
    _apply_expenses(new_doc, payload)
    new_doc.insert(ignore_permissions=True)
    _emit_new_pending(new_doc, set())
    return new_doc.as_dict()


@frappe.whitelist()
def delete_donation(name):
    perms.require_donation_admin()
    doc = frappe.get_doc("Donation", name)
    if doc.year and int(doc.year) < MIN_YEAR:
        frappe.throw(_("Donations before {0} are read-only history.").format(MIN_YEAR))
    if any(r.approval_status == "Approved" for r in doc.get("donated_amounts")):
        frappe.throw(
            _(
                "This record has approved mission entries posted to the ledger "
                "and cannot be deleted. Cancel the Journal Entries in Frappe Desk first."
            )
        )
    doc.delete(ignore_permissions=True)
    return {"deleted": name}


@frappe.whitelist()
def approve_mission_item(donation, row_name):
    """Admin approval of a pending mission entry: posts a Journal Entry
    (debit mission cash/cashless asset, credit mission income — the same
    mapping Collections use) and locks the row."""
    perms.require_donation_admin()

    doc = frappe.get_doc("Donation", donation)
    row = next((r for r in doc.get("donated_amounts") if r.name == row_name), None)
    if row is None:
        frappe.throw(_("Entry not found — save the record before approving."))
    if row.approval_status == "Approved":
        frappe.throw(_("This entry is already approved."))
    if row.approval_status != "Pending":
        frappe.throw(_("Only mission entries need approval."))
    if not row.amount_donated or row.amount_donated <= 0:
        frappe.throw(_("The entry needs an amount before it can be approved."))

    settings = frappe.get_single("Church Management Settings")
    asset_account = (
        settings.mission_cashless_account
        if row.donation_type == "GCash"
        else settings.mission_cash_account
    )
    income_account = settings.mission_income_account or settings.default_income_account
    if not asset_account or not income_account:
        frappe.throw(_("Mission accounts are not configured in Church Management Settings."))

    cost_center = settings.default_cost_center
    je = frappe.new_doc("Journal Entry")
    je.posting_date = row.date_donated or frappe.utils.today()
    je.voucher_type = "Journal Entry"
    je.company = frappe.db.get_single_value("Global Defaults", "default_company")
    je.user_remark = _("Mission donation — {0} · {1}").format(doc.department, doc.year)
    je.set(
        "accounts",
        [
            {
                "account": asset_account,
                "debit_in_account_currency": row.amount_donated,
                "cost_center": cost_center,
            },
            {
                "account": income_account,
                "credit_in_account_currency": row.amount_donated,
                "cost_center": cost_center,
            },
        ],
    )
    # Donation admins have no ERPNext Accounts role; the JE is a system-
    # generated side effect of an authorized approval (same as Collections).
    je.flags.ignore_permissions = True
    je.save(ignore_permissions=True)
    je.submit()

    row.approval_status = "Approved"
    row.approved_by = frappe.session.user
    row.approved_on = frappe.utils.now_datetime()
    row.journal_entry = je.name
    doc.save(ignore_permissions=True)

    _notify_admins(
        "mission_approved",
        {
            "donation": doc.name,
            "department": doc.department,
            "row": row_name,
            "journal_entry": je.name,
            "by": frappe.session.user,
        },
    )
    return doc.as_dict()


@frappe.whitelist()
def get_departments():
    """Departments the current user may filter the list by."""
    perms.require_donation_access()
    if perms.is_donation_admin():
        return frappe.get_all("Department Name", pluck="name", order_by="name asc")
    return sorted(perms.donation_departments())


@frappe.whitelist()
def get_new_donation_options():
    """Departments + assignable users for the admin create modal."""
    perms.require_donation_admin()
    departments = frappe.get_all("Department Name", pluck="name", order_by="name asc")
    donation_users = frappe.get_all(
        "Has Role",
        filters={
            "role": ["in", ["Donation Editor", "Donation Creator"]],
            "parenttype": "User",
        },
        pluck="parent",
        distinct=True,
    )
    users = frappe.get_all(
        "User",
        filters={"name": ["in", donation_users], "enabled": 1},
        fields=["name", "full_name"],
        order_by="name asc",
    )
    return {"departments": departments, "users": users, "min_year": MIN_YEAR}


# ---------------------------------------------------------------------------
# Invitations
# ---------------------------------------------------------------------------


def _gen_temp_password(length=12):
    import secrets
    import string

    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


@frappe.whitelist()
def invite_user(email, department, first_name=None, last_name=None, year=None):
    """Invite someone by email to record donations for one department.

    Creates (or reuses) a Website User holding only the Donation Editor role —
    that role gates exactly the /donations pages — assigns them to the
    department's Donation record for the year (created if missing), and emails
    them credentials. New users get a temporary password and must set their
    own on first login (same gate as music-team onboarding)."""
    perms.require_donation_admin()

    email = (email or "").strip().lower()
    frappe.utils.validate_email_address(email, throw=True)
    if not frappe.db.exists("Department Name", department):
        frappe.throw(_("Department {0} does not exist.").format(department))
    year = int(year or 0) or max(frappe.utils.now_datetime().year, MIN_YEAR)
    if year < MIN_YEAR:
        frappe.throw(_("Year must be {0} or later.").format(MIN_YEAR))

    temp_password = None
    if frappe.db.exists("User", email):
        user = frappe.get_doc("User", email)
        if not user.enabled:
            frappe.throw(
                _("User {0} exists but is disabled. Re-enable them in Frappe Desk first.").format(email)
            )
        if "Donation Editor" not in {r.role for r in user.get("roles") or []}:
            user.append("roles", {"role": "Donation Editor"})
            user.save(ignore_permissions=True)
    else:
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": (first_name or "").strip() or email.split("@")[0],
                "last_name": (last_name or "").strip(),
                "send_welcome_email": 0,
                "user_type": "Website User",
                "enabled": 1,
                "roles": [{"role": "Donation Editor"}],
            }
        )
        user.insert(ignore_permissions=True)

        from frappe.utils.password import update_password

        temp_password = _gen_temp_password()
        update_password(user.name, temp_password)
        frappe.db.set_value("User", user.name, "reset_password_key", "")
        # Same cache flag the music-team flow uses: whoami() reads it and the
        # SPA forces a password change before anything else.
        frappe.cache().set_value(f"music_temp_pw:{user.name}", "1")

    # Add them to the department's record, creating it on first use. Invites
    # accumulate: the first invitee becomes `assigned_to`, later ones join the
    # `assignees` table — everyone on the record sees and edits it together.
    donation_name = frappe.db.get_value(
        "Donation", {"department": department, "year": year}
    )
    if donation_name:
        doc = frappe.get_doc("Donation", donation_name)
        if not doc.assigned_to:
            doc.assigned_to = user.name
        elif user.name != doc.assigned_to and user.name not in {
            a.user for a in doc.get("assignees")
        }:
            doc.append("assignees", {"user": user.name})
        doc.save(ignore_permissions=True)
    else:
        doc = frappe.new_doc("Donation")
        doc.department = department
        doc.year = year
        doc.assigned_to = user.name
        doc.insert(ignore_permissions=True)

    recorders = ([doc.assigned_to] if doc.assigned_to else []) + [
        a.user for a in doc.get("assignees")
    ]

    frappe.db.commit()

    email_sent = True
    try:
        frappe.sendmail(
            recipients=[email],
            subject=f"Donation records access — {department}",
            template="donation_invitation",
            args={
                "first_name": user.first_name or email,
                "email": email,
                "temp_password": temp_password,
                "department": department,
                "year": year,
                "login_url": f"{frappe.utils.get_url()}/church_management#/login",
            },
            now=True,
        )
    except Exception:
        email_sent = False
        frappe.log_error(frappe.get_traceback(), "Donation invitation email failed")

    return {
        "user": user.name,
        "new_user": bool(temp_password),
        "department": department,
        "year": year,
        "donation": doc.name,
        "recorders": recorders,
        "email_sent": email_sent,
    }


@frappe.whitelist()
def remove_recorder(donation, user):
    """Admin removal of a recorder: they immediately stop seeing this record.
    If the primary (assigned_to) is removed, the first remaining assignee is
    promoted so the record keeps a primary recorder."""
    perms.require_donation_admin()

    doc = frappe.get_doc("Donation", donation)
    if doc.year and int(doc.year) < MIN_YEAR:
        frappe.throw(_("Donations before {0} are read-only history.").format(MIN_YEAR))
    if not _is_recorder(doc, user):
        frappe.throw(_("{0} is not a recorder on this record.").format(user))

    keep = [a.user for a in doc.get("assignees") if a.user != user]
    if doc.assigned_to == user:
        doc.assigned_to = keep.pop(0) if keep else None
    doc.set("assignees", [])
    for u in keep:
        doc.append("assignees", {"user": u})
    doc.save(ignore_permissions=True)
    return doc.as_dict()


# ---------------------------------------------------------------------------
# Purposes
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_purposes():
    perms.require_donation_access()
    return frappe.get_all(
        "Donation Purpose",
        fields=["name", "is_mission"],
        order_by="name asc",
    )


@frappe.whitelist()
def create_purpose(purpose_name, force=0):
    """Add a purpose to the dropdown. Any donation user may add one — the
    guardrail is the dedup check, not the role: same-word duplicates
    (trim/lower) are always rejected; near-matches (plurals, misspellings)
    are flagged back to the UI and only created on explicit force=1."""
    perms.require_donation_access()

    purpose_name = " ".join((purpose_name or "").strip().split())
    if not purpose_name:
        frappe.throw(_("Purpose name is required."))

    similar = find_similar(purpose_name)
    normalized = purpose_name.strip().lower()
    exact = [s for s in similar if s.strip().lower() == normalized]
    if exact:
        frappe.throw(_("Purpose already exists as \"{0}\".").format(exact[0]))
    if similar and not int(force or 0):
        return {"created": False, "similar": similar}

    doc = frappe.new_doc("Donation Purpose")
    doc.purpose_name = purpose_name
    # "Mission" is special: its items need admin approval and post to the
    # mission ledger accounts. Flag it automatically so nobody forgets.
    doc.is_mission = 1 if normalized == "mission" else 0
    doc.insert(ignore_permissions=True)
    return {"created": True, "name": doc.name, "is_mission": doc.is_mission}
