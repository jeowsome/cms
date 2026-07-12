"""Admin endpoints for assigning church-management roles to Frappe Users via the SPA."""
import json

import frappe

from church_management.api import permissions as perms


# Roles the SPA is allowed to grant or revoke. Anything else on a User
# document (Frappe built-ins, ERPNext modules, etc.) is left untouched.
MANAGED_ROLES = (
	"Finance Team",
	"Music Team Leader",
	"Music Team Member",
	"Worship Leader",
)
# Subset that a Music Team Leader (without admin) is allowed to manage.
# Admin can manage all MANAGED_ROLES.
LEADER_GRANTABLE = ("Music Team Member", "Worship Leader")


def _grantable():
	if perms.is_admin():
		return set(MANAGED_ROLES)
	if perms.is_music_leader():
		return set(LEADER_GRANTABLE)
	return set()


def _require_role_admin():
	if not (perms.is_admin() or perms.is_music_leader()):
		frappe.throw("Music Team Leader or Administrator access required.", frappe.PermissionError)


@frappe.whitelist()
def list_grantable_roles():
	"""Roles the current user is allowed to grant/revoke."""
	_require_role_admin()
	return sorted(_grantable())


@frappe.whitelist()
def list_assignable_users(search=None):
	"""Return non-Guest users with their managed-role assignments and any linked
	Church Member. Music Team Leader sees Website Users only; Admin sees every
	enabled user."""
	_require_role_admin()

	# Base filter — always exclude Guest and Administrator.
	filters = [
		["enabled", "=", 1],
		["name", "not in", ["Guest", "Administrator"]],
	]
	# Non-admins should only see Website Users (typical music team accounts) so
	# they don't accidentally edit staff/system accounts.
	if not perms.is_admin():
		filters.append(["user_type", "=", "Website User"])
	if search:
		# Frappe `or_filters` would be nicer; for simplicity just match full_name.
		filters.append(["full_name", "like", f"%{search}%"])

	users = frappe.get_all(
		"User", filters=filters,
		fields=["name", "email", "full_name", "enabled", "user_image", "user_type"],
		order_by="full_name asc",
		limit_page_length=500,
	)
	if not users:
		return []

	user_names = [u.name for u in users]
	# Bulk-fetch managed role assignments
	role_rows = frappe.db.sql(
		"""
		SELECT parent, role FROM `tabHas Role`
		WHERE parent IN %(users)s
		  AND role IN %(roles)s
		  AND parenttype = 'User'
		""",
		{"users": tuple(user_names), "roles": tuple(MANAGED_ROLES)},
		as_dict=True,
	)
	by_user = {}
	for r in role_rows:
		by_user.setdefault(r["parent"], []).append(r["role"])

	# Bulk-detect admin-bypass users (System Manager / Administrator). Admins
	# implicitly satisfy every MANAGED_ROLE via permissions.FINANCE_ROLES etc.,
	# so the UI surfaces this so operators don't think the user lacks access.
	admin_rows = frappe.db.sql(
		"""
		SELECT parent FROM `tabHas Role`
		WHERE parent IN %(users)s
		  AND role IN %(admin_roles)s
		  AND parenttype = 'User'
		""",
		{"users": tuple(user_names), "admin_roles": tuple(perms.ADMIN_ROLES)},
		as_dict=True,
	)
	admin_users = {r["parent"] for r in admin_rows}

	# Linked Church Member by email (so the UI can show who's a real church member)
	member_by_email = {}
	emails = [u.email for u in users if u.email]
	if emails:
		members = frappe.get_all(
			"Church Member",
			filters={"email_address": ["in", emails]},
			fields=["name", "email_address", "firstname", "lastname"],
		)
		for m in members:
			member_by_email[m.email_address] = m

	out = []
	for u in users:
		member = member_by_email.get(u.email)
		out.append({
			"name": u.name,
			"email": u.email,
			"full_name": u.full_name or u.email,
			"user_type": u.user_type,
			"enabled": bool(u.enabled),
			"user_image": u.user_image,
			"roles": sorted(by_user.get(u.name, [])),
			"is_admin": u.name in admin_users,
			"church_member": member.name if member else None,
			"church_member_name": (
				((member.firstname or "") + " " + (member.lastname or "")).strip()
				if member else None
			),
		})
	return out


@frappe.whitelist()
def set_user_roles(user, roles):
	"""Set the user's managed-role assignments to exactly `roles` (within the
	caller's grantable set). Roles outside that set are silently ignored.
	Unmanaged roles on the User document are never touched.
	"""
	_require_role_admin()
	if user in ("Administrator", "Guest"):
		frappe.throw("Cannot modify the Administrator or Guest user.", frappe.PermissionError)
	if isinstance(roles, str):
		roles = json.loads(roles)
	grantable = _grantable()
	target = {r for r in (roles or []) if r in grantable}

	# Reject any attempt to grant an unknown role.
	bad = set(roles or []) - set(MANAGED_ROLES)
	if bad:
		frappe.throw(
			f"These roles are not managed by this app: {', '.join(sorted(bad))}",
			frappe.PermissionError,
		)
	# Reject non-grantable (e.g. music leader trying to grant Finance Team).
	out_of_scope = set(roles or []) - grantable - set()
	if out_of_scope:
		frappe.throw(
			f"You are not allowed to grant: {', '.join(sorted(out_of_scope))}",
			frappe.PermissionError,
		)

	user_doc = frappe.get_doc("User", user)
	current_managed = {r.role for r in (user_doc.roles or []) if r.role in grantable}
	to_remove = current_managed - target
	to_add = target - {r.role for r in (user_doc.roles or [])}

	if to_remove:
		user_doc.roles = [r for r in (user_doc.roles or []) if r.role not in to_remove]
	for r in to_add:
		user_doc.append("roles", {"role": r})

	user_doc.flags.ignore_permissions = True
	user_doc.save()
	frappe.db.commit()
	return {
		"ok": True,
		"user": user,
		"roles": sorted(r.role for r in user_doc.roles if r.role in MANAGED_ROLES),
	}
