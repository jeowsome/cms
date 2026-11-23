import frappe

from church_management.www.church_management import get_spa_assets


def get_context(context):
	"""Public church calendar for members: guest-allowed mount of the SPA at
	the /church-calendar hash route (confirmed public activities only)."""
	context.no_cache = 1
	context.show_sidebar = False
	try:
		context.csrf_token = frappe.sessions.get_csrf_token()
	except Exception:
		context.csrf_token = ""
	context.update(get_spa_assets())
