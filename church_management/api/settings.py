import frappe


@frappe.whitelist()
def get_settings():
    """Get Church Management Settings for the frontend."""
    settings = frappe.get_single("Church Management Settings")
    return {
        "company": settings.company,
        "company_abbr": settings.company_abbr,
        "default_cost_center": settings.default_cost_center,
        "fiscal_year": frappe.defaults.get_global_default("fiscal_year"),
    }


@frappe.whitelist()
def get_current_user():
    """Get current user info for the frontend."""
    user = frappe.session.user
    user_doc = frappe.get_doc("User", user)
    return {
        "email": user,
        "full_name": user_doc.full_name,
        "roles": frappe.get_roles(user),
    }
