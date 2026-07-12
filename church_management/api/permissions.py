"""Role-based access helpers used by every SPA endpoint.

The SPA serves three audiences from the same Vue app:

  - Finance Team / Administrator → Disbursements
  - Music Team Leader / Worship Leader / Administrator → full Music tooling
  - Music Team Member → slim profile + own schedule + swap requests

Every server-side route that mutates state should call the matching
`require_*` helper before doing anything. Read endpoints typically rely on
`@frappe.whitelist()` (logged-in only) and then filter by role.
"""
import frappe


ADMIN_ROLES = {"System Manager", "Administrator"}
FINANCE_ROLES = {"Finance Team"} | ADMIN_ROLES
MUSIC_LEADER_ROLES = {"Music Team Leader"} | ADMIN_ROLES
WORSHIP_LEADER_ROLES = {"Worship Leader"} | MUSIC_LEADER_ROLES
MUSIC_MEMBER_ROLES = {"Music Team Member"} | WORSHIP_LEADER_ROLES
MUSIC_ANY_ROLES = MUSIC_MEMBER_ROLES  # any music role grants music-area access


def _roles(user=None):
	user = user or frappe.session.user
	if user == "Guest":
		return set()
	return set(frappe.get_roles(user))


def is_admin(user=None):
	return bool(_roles(user) & ADMIN_ROLES)


def is_finance(user=None):
	return bool(_roles(user) & FINANCE_ROLES)


def is_music_leader(user=None):
	return bool(_roles(user) & MUSIC_LEADER_ROLES)


def is_worship_leader(user=None):
	return bool(_roles(user) & WORSHIP_LEADER_ROLES)


def is_music_member(user=None):
	return bool(_roles(user) & MUSIC_MEMBER_ROLES)


def has_music_access(user=None):
	return bool(_roles(user) & MUSIC_ANY_ROLES)


def has_finance_access(user=None):
	return is_finance(user)


def require_finance():
	if not has_finance_access():
		frappe.throw("Finance Team access required.", frappe.PermissionError)


def require_music_access():
	if not has_music_access():
		frappe.throw("Music Team access required.", frappe.PermissionError)


def require_music_leader():
	if not is_music_leader():
		frappe.throw("Only Music Team Leader can perform this action.", frappe.PermissionError)


def require_worship_leader():
	"""Worship Leader can edit songs/practice/lineup; Music Team Leader and Admin
	implicitly satisfy this."""
	if not is_worship_leader():
		frappe.throw("Only Worship Leader can perform this action.", frappe.PermissionError)


def role_flags(user=None):
	"""Single dict of every role flag — used by whoami() so the SPA can route
	without re-querying."""
	user = user or frappe.session.user
	if user == "Guest":
		return {
			"is_admin": False,
			"is_finance": False,
			"is_music_leader": False,
			"is_worship_leader": False,
			"is_music_member": False,
			"has_music_access": False,
			"has_finance_access": False,
		}
	roles = _roles(user)
	return {
		"is_admin": bool(roles & ADMIN_ROLES),
		"is_finance": bool(roles & FINANCE_ROLES),
		"is_music_leader": bool(roles & MUSIC_LEADER_ROLES),
		"is_worship_leader": bool(roles & WORSHIP_LEADER_ROLES),
		"is_music_member": bool(roles & MUSIC_MEMBER_ROLES),
		"has_music_access": bool(roles & MUSIC_ANY_ROLES),
		"has_finance_access": bool(roles & FINANCE_ROLES),
	}
