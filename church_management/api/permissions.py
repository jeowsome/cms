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
DONATION_ROLES = {"Donation Editor", "Donation Creator"} | ADMIN_ROLES

# Users assigned to this department's Donation records see every department.
DONATION_ADMIN_DEPARTMENT = "Pasig Admin"

# Users on this department's Donation records may open the Frappe desk (/app).
DESK_DEPARTMENT = "Pasig General"
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


def _user_donations(user, column, extra_where="", extra_args=None):
	"""Distinct `column` values of Donation docs the user is on — either as
	`assigned_to` or via the `assignees` child table."""
	args = {"user": user, **(extra_args or {})}
	return [
		r[0]
		for r in frappe.db.sql(
			f"""
			select distinct d.`{column}`
			from `tabDonation` d
			left join `tabDonation Assignee` a
				on a.parent = d.name and a.parenttype = 'Donation'
			where (d.assigned_to = %(user)s or a.user = %(user)s) {extra_where}
			""",
			args,
		)
	]


def donation_departments(user=None):
	"""Departments a user records donations for — derived from the Donation
	docs they are on. This is the only user↔department mapping."""
	user = user or frappe.session.user
	if user == "Guest":
		return []
	return _user_donations(user, "department")


def donation_record_names(user=None):
	"""Names of the Donation docs the user is on. Visibility is per record:
	an invite grants exactly that record, and removal takes it away."""
	user = user or frappe.session.user
	if user == "Guest":
		return []
	return _user_donations(user, "name")


def has_desk_access(user=None):
	"""Only Administrator / System Manager, or users on a Pasig General
	department Donation record, may open the Frappe desk (/app)."""
	user = user or frappe.session.user
	if user == "Guest":
		return False
	if user == "Administrator" or is_admin(user):
		return True
	return bool(
		_user_donations(
			user,
			"name",
			extra_where="and d.department = %(dept)s",
			extra_args={"dept": DESK_DEPARTMENT},
		)
	)


def is_donation_admin(user=None):
	"""Administrator / System Manager, or a donation-role holder on the
	Pasig Admin department's records — they see donations of every department."""
	user = user or frappe.session.user
	if is_admin(user):
		return True
	return (
		has_donation_access(user)
		and DONATION_ADMIN_DEPARTMENT in donation_departments(user)
	)


def has_donation_access(user=None):
	"""Access to the donation pages is purely role-gated so revoking the role
	on /admin/roles fully revokes access; Donation.assigned_to only scopes
	which departments a role-holder sees."""
	return bool(_roles(user) & DONATION_ROLES)


def require_donation_access():
	if not has_donation_access():
		frappe.throw("Donation access required.", frappe.PermissionError)


def require_donation_admin():
	if not is_donation_admin():
		frappe.throw(
			"Only Pasig Admin or Administrator can perform this action.",
			frappe.PermissionError,
		)


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
			"has_donation_access": False,
			"is_donation_admin": False,
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
		"has_donation_access": has_donation_access(user),
		"is_donation_admin": is_donation_admin(user),
	}
