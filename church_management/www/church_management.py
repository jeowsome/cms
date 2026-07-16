import json
import os

import frappe


def get_spa_assets():
    """Resolve the SPA entry JS/CSS URLs from Vite's build manifest.

    Filenames carry a per-build salt (see frontend/vite.config.js) so every
    deploy is a fresh URL — no ?v= query strings. A query on the module entry
    is unsafe: lazy chunks import the entry by its bare filename, and the two
    URLs would load as two separate module instances.
    """
    dist = frappe.get_app_path("church_management", "public", "dist")
    base = "/assets/church_management/dist/"
    try:
        with open(os.path.join(dist, ".vite", "manifest.json")) as f:
            manifest = json.load(f)
        entry = manifest["src/main.js"]
        return {
            "spa_js": base + entry["file"],
            "spa_css": base + entry["css"][0] if entry.get("css") else "",
        }
    except (OSError, KeyError, ValueError, IndexError):
        # Manifest missing (old build) — fall back to globbing dist/assets.
        try:
            names = os.listdir(os.path.join(dist, "assets"))
        except OSError:
            names = []
        js = next((n for n in sorted(names) if n.startswith("index") and n.endswith(".js")), "")
        css = next((n for n in sorted(names) if n.startswith("main") and n.endswith(".css")), "")
        return {
            "spa_js": base + "assets/" + js if js else "",
            "spa_css": base + "assets/" + css if css else "",
        }


def get_context(context):
    # SPA handles its own auth-gating (login, register, forgot-password are public routes).
    context.no_cache = 1
    context.show_sidebar = False
    try:
        context.csrf_token = frappe.sessions.get_csrf_token()
    except Exception:
        context.csrf_token = ""
    context.update(get_spa_assets())
