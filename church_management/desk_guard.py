"""Restrict the Frappe desk (/app) to church administrators.

Only Administrator / System Manager, or users on a Pasig General department
Donation record, may open the desk. Everyone else is sent to the SPA — their
tooling lives there, and the desk exposes raw doctypes they shouldn't browse.
"""
import frappe

from church_management.api import permissions as perms


def check_desk_access():
    request = getattr(frappe.local, "request", None)
    if request is None:
        return
    path = request.path or ""
    if path != "/app" and not path.startswith("/app/"):
        return

    user = frappe.session.user if frappe.session else "Guest"
    if user == "Guest":
        # Let frappe's own login redirect handle guests.
        return
    if perms.has_desk_access(user):
        return

    frappe.local.flags.redirect_location = "/church_management"
    raise frappe.Redirect
