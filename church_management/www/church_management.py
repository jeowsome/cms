import os

import frappe


def get_context(context):
    # SPA handles its own auth-gating (login, register, forgot-password are public routes).
    context.no_cache = 1
    context.show_sidebar = False
    try:
        context.csrf_token = frappe.sessions.get_csrf_token()
    except Exception:
        context.csrf_token = ""

    # Version assets by build mtime: browsers cache the bundle between deploys
    # and bust exactly when a new `npm run build` lands.
    try:
        dist = frappe.get_app_path("church_management", "public", "dist", "assets")
        context.build_ver = int(
            max(
                os.path.getmtime(os.path.join(dist, "index.js")),
                os.path.getmtime(os.path.join(dist, "main.css")),
            )
        )
    except OSError:
        context.build_ver = int(frappe.utils.now_datetime().timestamp())
