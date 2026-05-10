import frappe


def get_context(context):
    """Public, guest-allowed mount of the SPA at the /register hash route."""
    context.no_cache = 1
    context.show_sidebar = False
    try:
        context.csrf_token = frappe.sessions.get_csrf_token()
    except Exception:
        context.csrf_token = ""
