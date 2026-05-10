"""Music team API — lineup, roles, unavailability, declines, notifications.

All write endpoints emit `music_team_event` over socket.io so other connected
clients refresh their views in real time.
"""
import frappe
from frappe.utils import getdate, now_datetime
import json
from datetime import timedelta


MUSIC_MINISTRY = "Music Team"


def _emit(action, payload=None):
	frappe.publish_realtime(
		"music_team_event",
		{"action": action, "payload": payload or {}},
		after_commit=True,
	)


def _full_name(member):
	if not member:
		return ""
	first = frappe.db.get_value("Church Member", member, "firstname") or ""
	last = frappe.db.get_value("Church Member", member, "lastname") or ""
	return (first + " " + last).strip() or member


@frappe.whitelist(allow_guest=True)
def get_roles():
	"""All Music Team Tag entries — used as the role catalogue."""
	return frappe.get_all(
		"Music Team Tag",
		fields=["name", "tag_label"],
		order_by="creation asc",
	)


@frappe.whitelist()
def get_members():
	"""Music team roster — anyone with at least one music_role_preference row."""
	rows = frappe.db.sql(
		"""
		SELECT DISTINCT cm.name, cm.firstname, cm.lastname, cm.email_address, cm.contact_number
		FROM `tabChurch Member` cm
		JOIN `tabMusic Role Preference` mrp ON mrp.parent = cm.name
		ORDER BY cm.firstname ASC
		""",
		as_dict=True,
	)
	for m in rows:
		prefs = frappe.get_all(
			"Music Role Preference",
			filters={"parent": m["name"]},
			fields=["music_team_tag", "skill_level", "preferred"],
		)
		m["full_name"] = (m["firstname"] or "") + " " + (m["lastname"] or "")
		m["full_name"] = m["full_name"].strip()
		m["roles"] = [p.music_team_tag for p in prefs]
		preferred = next((p for p in prefs if p.preferred), None)
		if not preferred and prefs:
			# fall back to highest skill if nothing is explicitly preferred
			preferred = max(prefs, key=lambda p: int(p.skill_level or 0))
		m["preferred_role"] = preferred.music_team_tag if preferred else None
		m["preferences"] = [dict(p) for p in prefs]
	return rows


@frappe.whitelist()
def set_member_roles(member, roles, preferred=None):
	"""Replace a member's music role preferences. `roles` is a list of tag names
	(or list of {tag, skill_level} dicts). `preferred` is the tag to flag as preferred."""
	if isinstance(roles, str):
		roles = json.loads(roles)
	doc = frappe.get_doc("Church Member", member)
	doc.set("music_role_preference", [])
	for r in roles or []:
		tag = r if isinstance(r, str) else r.get("tag") or r.get("music_team_tag")
		skill = "1" if isinstance(r, str) else str(r.get("skill_level") or "1")
		doc.append(
			"music_role_preference",
			{
				"music_team_tag": tag,
				"skill_level": skill,
				"preferred": 1 if preferred and tag == preferred else 0,
			},
		)
	doc.save(ignore_permissions=False)
	_emit("roles_updated", {"member": member})
	return {"ok": True}


@frappe.whitelist()
def get_lineup(month, year):
	"""Return all music-team assignments for a given Ministry Schedule, grouped by
	{date: {service_time: {role: assignment}}}."""
	year = int(year)
	sched = frappe.db.get_value(
		"Ministry Schedule", {"month": month, "year": year}, "name"
	)
	if not sched:
		return {"schedule": None, "sundays": [], "wednesdays": [], "lineup": {}, "open_declines": []}

	doc = frappe.get_doc("Ministry Schedule", sched)
	lineup = {}
	for a in doc.assignments:
		if not a.music_role:
			continue
		key = str(a.sunday_date)
		svc = (a.service_time or "Morning").lower()
		svc = "am" if svc == "morning" else "pm" if svc == "evening" else "am"
		lineup.setdefault(key, {}).setdefault(svc, {})[a.music_role] = {
			"row_name": a.name,
			"member": a.member,
			"member_name": a.member_name,
		}

	sundays = [
		{"sunday_date": str(s.sunday_date), "theme": s.theme, "sermon_title": s.sermon_title}
		for s in (doc.sundays or [])
	]
	wednesdays = [
		{"sunday_date": str(s.sunday_date), "theme": s.theme}
		for s in (doc.wednesdays or [])
	]

	dates = [s["sunday_date"] for s in sundays]
	declines = []
	if dates:
		declines = frappe.get_all(
			"Schedule Decline",
			filters={"sunday_date": ["in", dates], "status": "open"},
			fields=["name", "sunday_date", "service_time", "music_role", "member", "member_name", "reason", "declined_at"],
		)
		for d in declines:
			d["sunday_date"] = str(d["sunday_date"])

	return {
		"schedule": {"name": doc.name, "month": doc.month, "year": doc.year, "status": doc.status},
		"sundays": sundays,
		"wednesdays": wednesdays,
		"lineup": lineup,
		"open_declines": declines,
	}


@frappe.whitelist()
def set_assignment(month, year, sunday_date, service_time, music_role, member, member_name=None):
	"""Create or update one music-team assignment row. Pass empty member to clear."""
	year = int(year)
	sched_name = frappe.db.get_value(
		"Ministry Schedule", {"month": month, "year": year}, "name"
	)
	if not sched_name:
		sched = frappe.new_doc("Ministry Schedule")
		sched.month = month
		sched.year = year
		sched.status = "Draft"
		sched.insert()
		sched_name = sched.name

	doc = frappe.get_doc("Ministry Schedule", sched_name)
	svc = "Morning" if (service_time or "").lower() in ("am", "morning") else "Evening"

	target = None
	for row in doc.assignments:
		if (
			str(row.sunday_date) == str(sunday_date)
			and (row.service_time or "") == svc
			and (row.music_role or "") == music_role
		):
			target = row
			break

	if not member:
		if target:
			doc.remove(target)
			doc.save()
			_emit("assignment_cleared", {"schedule": sched_name, "sunday_date": str(sunday_date), "service_time": svc, "music_role": music_role})
		return {"ok": True, "schedule": sched_name}

	name = member_name or _full_name(member)
	if target:
		target.member = member
		target.member_name = name
	else:
		doc.append(
			"assignments",
			{
				"sunday_date": sunday_date,
				"ministry": MUSIC_MINISTRY,
				"service_time": svc,
				"music_role": music_role,
				"member": member,
				"member_name": name,
			},
		)
	doc.save()
	_emit("assignment_set", {
		"schedule": sched_name, "sunday_date": str(sunday_date),
		"service_time": svc, "music_role": music_role, "member": member,
	})
	return {"ok": True, "schedule": sched_name}


@frappe.whitelist()
def publish_schedule(month, year):
	year = int(year)
	sched_name = frappe.db.get_value("Ministry Schedule", {"month": month, "year": year}, "name")
	if not sched_name:
		frappe.throw("Schedule does not exist yet.")
	doc = frappe.get_doc("Ministry Schedule", sched_name)
	doc.status = "Published"
	doc.published_on = now_datetime()
	doc.save()
	_emit("schedule_published", {"schedule": sched_name, "month": month, "year": year})
	return {"ok": True}


@frappe.whitelist()
def list_unavailability(from_date=None, to_date=None):
	filters = {}
	if from_date and to_date:
		filters = [["to_date", ">=", from_date], ["from_date", "<=", to_date]]
	rows = frappe.get_all(
		"Member Unavailability",
		filters=filters,
		fields=["name", "member", "member_name", "from_date", "to_date", "kind", "reason"],
		order_by="from_date desc",
	)
	for r in rows:
		r["from_date"] = str(r["from_date"])
		r["to_date"] = str(r["to_date"])
	return rows


@frappe.whitelist()
def create_unavailability(member, from_date, to_date, kind="vacation", reason=""):
	doc = frappe.new_doc("Member Unavailability")
	doc.member = member
	doc.member_name = _full_name(member)
	doc.from_date = from_date
	doc.to_date = to_date
	doc.kind = kind
	doc.reason = reason
	doc.insert()
	_emit("unavailability_added", {"name": doc.name, "member": member})
	return {"ok": True, "name": doc.name}


@frappe.whitelist()
def delete_unavailability(name):
	frappe.delete_doc("Member Unavailability", name)
	_emit("unavailability_removed", {"name": name})
	return {"ok": True}


@frappe.whitelist()
def list_declines(status=None, limit=50):
	filters = {}
	if status:
		filters["status"] = status
	rows = frappe.get_all(
		"Schedule Decline",
		filters=filters,
		fields=["name", "schedule", "sunday_date", "service_time", "music_role", "member", "member_name", "reason", "status", "declined_at"],
		order_by="declined_at desc",
		limit_page_length=int(limit),
	)
	for r in rows:
		r["sunday_date"] = str(r["sunday_date"])
		r["declined_at"] = str(r["declined_at"]) if r.get("declined_at") else None
	return rows


@frappe.whitelist()
def decline_assignment(sunday_date, service_time, music_role, member, reason=""):
	svc = "Morning" if (service_time or "").lower() in ("am", "morning") else "Evening"
	sched_name = None
	row = frappe.db.get_value(
		"Ministry Schedule Assignment",
		{
			"sunday_date": sunday_date,
			"service_time": svc,
			"music_role": music_role,
			"member": member,
		},
		["name", "parent"],
	)
	if row:
		sched_name = row[1]

	doc = frappe.new_doc("Schedule Decline")
	doc.schedule = sched_name
	doc.sunday_date = sunday_date
	doc.service_time = svc
	doc.music_role = music_role
	doc.member = member
	doc.member_name = _full_name(member)
	doc.reason = reason
	doc.status = "open"
	doc.declined_at = now_datetime()
	doc.insert(ignore_permissions=True)
	_emit("decline_created", {
		"name": doc.name, "sunday_date": str(sunday_date),
		"service_time": svc, "music_role": music_role, "member": member,
	})
	return {"ok": True, "name": doc.name}


@frappe.whitelist()
def resolve_decline(name, status="filled"):
	doc = frappe.get_doc("Schedule Decline", name)
	doc.status = status
	doc.save()
	_emit("decline_resolved", {"name": name, "status": status})
	return {"ok": True}


@frappe.whitelist()
def send_notification(notification_type, title, body, sunday_date=None, service_time=None, send_sms=0, recipients=None):
	if isinstance(recipients, str):
		recipients = json.loads(recipients)

	doc = frappe.new_doc("Music Team Notification")
	doc.notification_type = notification_type
	doc.title = title
	doc.body = body
	doc.sunday_date = sunday_date or None
	doc.service_time = service_time or None
	doc.send_sms = 1 if int(send_sms or 0) else 0
	doc.sent_at = now_datetime()

	for r in recipients or []:
		doc.append("recipients", {
			"member": r.get("member"),
			"member_name": r.get("member_name") or _full_name(r.get("member")),
			"music_role": r.get("music_role"),
		})
	doc.insert(ignore_permissions=True)
	# realtime fan-out happens in the doctype's after_insert
	return {"ok": True, "name": doc.name}


@frappe.whitelist()
def list_notifications(limit=20):
	rows = frappe.get_all(
		"Music Team Notification",
		fields=["name", "title", "notification_type", "sunday_date", "service_time", "body", "sender", "sent_at"],
		order_by="sent_at desc",
		limit_page_length=int(limit),
	)
	for r in rows:
		r["sunday_date"] = str(r["sunday_date"]) if r.get("sunday_date") else None
		r["sent_at"] = str(r["sent_at"]) if r.get("sent_at") else None
		r["recipient_count"] = frappe.db.count(
			"Music Team Notification Recipient", {"parent": r["name"]}
		)
	return rows


@frappe.whitelist()
def my_assignments(member=None):
	"""All upcoming music-team assignments for a member (used by member-view)."""
	if not member:
		# resolve from session user → linked church member
		email = frappe.session.user
		member = frappe.db.get_value("Church Member", {"email_address": email}, "name")
	if not member:
		return []
	today = getdate()
	rows = frappe.db.sql(
		"""
		SELECT a.name as row_name, a.sunday_date, a.service_time, a.music_role, a.member,
		       a.member_name, ms.month, ms.year, ms.status, ms.name as schedule
		FROM `tabMinistry Schedule Assignment` a
		JOIN `tabMinistry Schedule` ms ON a.parent = ms.name
		WHERE a.member = %(m)s
		  AND a.music_role IS NOT NULL AND a.music_role != ''
		  AND a.sunday_date >= %(t)s
		ORDER BY a.sunday_date ASC, a.service_time ASC
		""",
		{"m": member, "t": today},
		as_dict=True,
	)
	for r in rows:
		r["sunday_date"] = str(r["sunday_date"])
	return rows


# =====================================================================
# Registration + Profile + Auth endpoints
# =====================================================================

import secrets
import string


def _is_leader():
	roles = frappe.get_roles()
	return "Music Team Leader" in roles or "System Manager" in roles


def _require_leader():
	if not _is_leader():
		frappe.throw("Only Music Team Leader can perform this action.", frappe.PermissionError)


def _gen_temp_password(length=12):
	alphabet = string.ascii_letters + string.digits
	return "".join(secrets.choice(alphabet) for _ in range(length))


@frappe.whitelist(allow_guest=True)
def submit_registration(payload):
	"""Public endpoint — accepts a registration submission and queues a confirmation email."""
	if isinstance(payload, str):
		payload = json.loads(payload)
	required = ["email", "first_name", "last_name", "gender", "birthday", "contact_number"]
	for f in required:
		if not (payload.get(f) or "").strip() if isinstance(payload.get(f), str) else not payload.get(f):
			frappe.throw(f"Missing required field: {f}")
	skills = payload.get("skills") or []
	if not skills:
		frappe.throw("Please select at least one skill.")

	# Reject duplicate pending registrations for the same email
	existing = frappe.db.get_value(
		"Music Team Registration",
		{"email": payload["email"], "status": "Pending"},
		"name",
	)
	if existing:
		return {"ok": True, "name": existing, "duplicate": True}

	doc = frappe.get_doc({
		"doctype": "Music Team Registration",
		"first_name": payload["first_name"].strip(),
		"last_name": payload["last_name"].strip(),
		"gender": payload["gender"],
		"email": payload["email"].strip().lower(),
		"contact_number": payload["contact_number"].strip(),
		"birthday": payload["birthday"],
		"member_since": (payload.get("member_since") or "").strip(),
		"envelope_number": (payload.get("envelope_number") or "").strip(),
		"status": "Pending",
		"submitted_on": now_datetime(),
	})
	# Soft match by envelope first, fallback to email
	doc.matched_church_member = (
		frappe.db.get_value("Church Member", {"envelope_number": doc.envelope_number}, "name")
		if doc.envelope_number else None
	) or frappe.db.get_value("Church Member", {"email_address": doc.email}, "name")

	for tag in skills:
		doc.append("skills", {"music_team_tag": tag})
	doc.insert(ignore_permissions=True)
	frappe.db.commit()

	try:
		frappe.sendmail(
			recipients=[doc.email],
			subject="Music Team registration received",
			template="music_registration_received",
			args={"first_name": doc.first_name, "registration_id": doc.name},
			now=True,
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Music registration receipt email failed")

	_emit("registration_submitted", {"name": doc.name})
	return {"ok": True, "name": doc.name}


@frappe.whitelist()
def list_registrations(status=None):
	_require_leader()
	filters = {}
	if status:
		filters["status"] = status
	rows = frappe.get_all(
		"Music Team Registration",
		filters=filters,
		fields=[
			"name", "status", "submitted_on", "first_name", "last_name", "gender", "email",
			"contact_number", "birthday", "member_since", "envelope_number",
			"matched_church_member", "linked_music_member", "reviewed_on", "reviewed_by",
			"rejection_reason",
		],
		order_by="submitted_on desc",
		limit_page_length=500,
	)
	for r in rows:
		r["submitted_on"] = str(r["submitted_on"]) if r.get("submitted_on") else None
		r["reviewed_on"] = str(r["reviewed_on"]) if r.get("reviewed_on") else None
		r["birthday"] = str(r["birthday"]) if r.get("birthday") else None
		skills = frappe.get_all(
			"Church Member Music Tag",
			filters={"parent": r["name"], "parenttype": "Music Team Registration"},
			fields=["music_team_tag"],
		)
		r["skills"] = [s["music_team_tag"] for s in skills]
		# Re-compute soft match preview if absent
		if r["envelope_number"] and not r["matched_church_member"]:
			r["matched_church_member"] = frappe.db.get_value(
				"Church Member", {"envelope_number": r["envelope_number"]}, "name"
			)
		if r["matched_church_member"]:
			cm = frappe.db.get_value(
				"Church Member",
				r["matched_church_member"],
				["firstname", "lastname", "email_address", "envelope_number", "contact_number", "birthday"],
				as_dict=True,
			)
			if cm:
				cm["birthday"] = str(cm["birthday"]) if cm.get("birthday") else None
				r["matched_church_member_data"] = cm
	return rows


@frappe.whitelist()
def update_registration(name, patch):
	_require_leader()
	if isinstance(patch, str):
		patch = json.loads(patch)
	doc = frappe.get_doc("Music Team Registration", name)
	if doc.status != "Pending":
		frappe.throw("Only pending registrations can be edited.")
	editable = {
		"first_name", "last_name", "gender", "email", "contact_number", "birthday",
		"member_since", "envelope_number", "matched_church_member",
	}
	for k, v in (patch or {}).items():
		if k in editable:
			doc.set(k, v)
	if "skills" in (patch or {}):
		doc.set("skills", [])
		for tag in patch["skills"] or []:
			doc.append("skills", {"music_team_tag": tag})
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	_emit("registration_updated", {"name": doc.name})
	return {"ok": True}


@frappe.whitelist()
def accept_registration(name):
	_require_leader()
	doc = frappe.get_doc("Music Team Registration", name)
	if doc.status == "Accepted":
		return {"ok": True, "already": True}

	# Resolve / create Church Member
	church_member = doc.matched_church_member
	if not church_member:
		# Last-chance match by envelope number
		if doc.envelope_number:
			church_member = frappe.db.get_value(
				"Church Member", {"envelope_number": doc.envelope_number}, "name"
			)
	if not church_member:
		frappe.throw("Cannot accept — no matched Church Member. Edit the registration to set one.")

	# Update Church Member contact info if missing
	cm = frappe.get_doc("Church Member", church_member)
	updates = {}
	if not cm.email_address:
		updates["email_address"] = doc.email
	if not cm.contact_number:
		updates["contact_number"] = doc.contact_number
	for k, v in updates.items():
		setattr(cm, k, v)
	# Sync skills onto Church Member's music_team_tag child
	existing_tags = {t.music_team_tag for t in (cm.get("music_team_tag") or [])}
	for s in doc.skills or []:
		if s.music_team_tag not in existing_tags:
			cm.append("music_team_tag", {"music_team_tag": s.music_team_tag})
	# Ensure at least one Music Role Preference row so they appear on the roster
	existing_prefs = {p.music_team_tag for p in (cm.get("music_role_preference") or [])}
	for s in doc.skills or []:
		if s.music_team_tag not in existing_prefs:
			cm.append("music_role_preference", {
				"music_team_tag": s.music_team_tag,
				"skill_level": 3,
				"preferred": 0,
			})
	cm.save(ignore_permissions=True)

	# Create / update User
	temp_password = _gen_temp_password()
	if frappe.db.exists("User", doc.email):
		user = frappe.get_doc("User", doc.email)
	else:
		user = frappe.get_doc({
			"doctype": "User",
			"email": doc.email,
			"first_name": doc.first_name,
			"last_name": doc.last_name,
			"send_welcome_email": 0,
			"user_type": "Website User",
			"enabled": 1,
		})
	if {"role": "Music Team Member"} not in [{"role": r.role} for r in user.get("roles") or []]:
		user.append("roles", {"role": "Music Team Member"})
	user.flags.ignore_permissions = True
	if user.is_new():
		user.insert(ignore_permissions=True)
	else:
		user.save(ignore_permissions=True)

	from frappe.utils.password import update_password
	update_password(user.name, temp_password)
	# Force password change on first login
	frappe.db.set_value("User", user.name, "reset_password_key", "")

	# Mark registration accepted + link
	doc.status = "Accepted"
	doc.linked_music_member = church_member
	doc.reviewed_on = now_datetime()
	doc.reviewed_by = frappe.session.user
	doc.save(ignore_permissions=True)

	# Cache flag drives the SPA's "force change password on next login" gate
	frappe.cache().set_value(f"music_temp_pw:{user.name}", "1")

	frappe.db.commit()

	site_url = frappe.utils.get_url()
	try:
		frappe.sendmail(
			recipients=[doc.email],
			subject="You're in — Music Team account",
			template="music_registration_accepted",
			args={
				"first_name": doc.first_name,
				"email": doc.email,
				"temp_password": temp_password,
				"login_url": f"{site_url}/church_management#/login",
			},
			now=True,
		)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Music registration acceptance email failed")

	_emit("registration_accepted", {"name": doc.name})
	return {"ok": True, "user": user.name}


REG_TO_CM_FIELDS = {
	"email": "email_address",
	"contact_number": "contact_number",
	"birthday": "birthday",
	"first_name": "firstname",
	"last_name": "lastname",
}


@frappe.whitelist()
def apply_match_field(name, field, source):
	"""Sync a single field between the registration and the matched Church Member.
	source = 'submitted' → push registration value to church member.
	source = 'record'    → pull church member value into registration."""
	_require_leader()
	if field not in REG_TO_CM_FIELDS:
		frappe.throw(f"Field '{field}' cannot be synced.")
	doc = frappe.get_doc("Music Team Registration", name)
	if not doc.matched_church_member:
		frappe.throw("No matched Church Member set.")
	cm = frappe.get_doc("Church Member", doc.matched_church_member)
	cm_field = REG_TO_CM_FIELDS[field]
	if source == "submitted":
		setattr(cm, cm_field, getattr(doc, field))
		cm.save(ignore_permissions=True)
	elif source == "record":
		setattr(doc, field, getattr(cm, cm_field))
		doc.save(ignore_permissions=True)
	else:
		frappe.throw("source must be 'submitted' or 'record'.")
	frappe.db.commit()
	_emit("registration_updated", {"name": name})
	return {"ok": True}


@frappe.whitelist()
def reject_registration(name, reason=None):
	_require_leader()
	doc = frappe.get_doc("Music Team Registration", name)
	if doc.status == "Accepted":
		frappe.throw("Already accepted — cannot reject.")
	doc.status = "Rejected"
	doc.rejection_reason = reason or ""
	doc.reviewed_on = now_datetime()
	doc.reviewed_by = frappe.session.user
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	_emit("registration_rejected", {"name": doc.name})
	return {"ok": True}


# ---------------------------------------------------------------------
# Profile (logged-in Music Team Member)
# ---------------------------------------------------------------------


def _resolve_my_member():
	user = frappe.session.user
	if user == "Guest":
		frappe.throw("Login required.", frappe.AuthenticationError)
	# Linked Church Member (by email)
	member = frappe.db.get_value("Church Member", {"email_address": user}, "name")
	return user, member


@frappe.whitelist()
def get_my_music_profile():
	user_name, member = _resolve_my_member()
	user = frappe.get_doc("User", user_name)
	temp_pw_pending = bool(frappe.cache().get_value(f"music_temp_pw:{user_name}"))
	out = {
		"user": user_name,
		"first_name": user.first_name,
		"last_name": user.last_name,
		"profile_image": user.user_image,
		"roles": [r.role for r in user.roles],
		"church_member": member,
		"temp_password_pending": temp_pw_pending,
	}
	if member:
		cm = frappe.get_doc("Church Member", member)
		prefs = [
			{"music_team_tag": p.music_team_tag, "skill_level": p.skill_level, "preferred": p.preferred}
			for p in (cm.music_role_preference or [])
		]
		out["envelope_number"] = cm.envelope_number
		out["preferences"] = prefs
		out["skills"] = [t.music_team_tag for t in (cm.music_team_tag or [])]
	return out


@frappe.whitelist()
def update_my_music_profile(patch):
	user_name, member = _resolve_my_member()
	if isinstance(patch, str):
		patch = json.loads(patch)
	user = frappe.get_doc("User", user_name)
	if "first_name" in patch:
		user.first_name = patch["first_name"]
	if "last_name" in patch:
		user.last_name = patch["last_name"]
	if "profile_image" in patch:
		user.user_image = patch["profile_image"]
	user.save(ignore_permissions=True)

	if member and ("skills" in patch or "preferred" in patch):
		cm = frappe.get_doc("Church Member", member)
		if "skills" in patch:
			cm.set("music_team_tag", [])
			for tag in patch["skills"] or []:
				cm.append("music_team_tag", {"music_team_tag": tag})
			# Mirror into preferences if missing
			existing = {p.music_team_tag for p in cm.music_role_preference or []}
			for tag in patch["skills"] or []:
				if tag not in existing:
					cm.append("music_role_preference", {
						"music_team_tag": tag, "skill_level": 3, "preferred": 0,
					})
		if "preferred" in patch:
			for p in cm.music_role_preference or []:
				p.preferred = 1 if p.music_team_tag == patch["preferred"] else 0
		cm.save(ignore_permissions=True)
	frappe.db.commit()
	return {"ok": True}


@frappe.whitelist()
def change_password(current_password, new_password):
	user_name = frappe.session.user
	if user_name == "Guest":
		frappe.throw("Login required.", frappe.AuthenticationError)
	from frappe.utils.password import check_password, update_password
	try:
		check_password(user_name, current_password)
	except frappe.AuthenticationError:
		frappe.throw("Current password is incorrect.")
	if not new_password or len(new_password) < 8:
		frappe.throw("New password must be at least 8 characters.")
	update_password(user_name, new_password)
	frappe.cache().delete_value(f"music_temp_pw:{user_name}")
	frappe.db.commit()
	return {"ok": True}


@frappe.whitelist(allow_guest=True)
def request_password_reset(email):
	"""Send a password-reset link if the user exists. Always returns ok to avoid user enumeration."""
	if not email:
		return {"ok": True}
	email = email.strip().lower()
	if frappe.db.exists("User", email):
		try:
			user = frappe.get_doc("User", email)
			user.flags.ignore_permissions = True
			key = user.reset_password()
			# reset_password sends an email by default in newer Frappe; ensure mail goes out
			frappe.db.commit()
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Music password reset failed")
	return {"ok": True}


@frappe.whitelist(allow_guest=True)
def login(email, password):
	"""Login via the SPA. Returns role hints so the SPA can route correctly."""
	from frappe.auth import LoginManager
	try:
		lm = LoginManager()
		lm.authenticate(user=email, pwd=password)
		lm.post_login()
	except frappe.AuthenticationError:
		frappe.throw("Invalid email or password.", frappe.AuthenticationError)
	roles = frappe.get_roles(frappe.session.user)
	temp_pw_pending = bool(frappe.cache().get_value(f"music_temp_pw:{frappe.session.user}"))
	return {
		"ok": True,
		"user": frappe.session.user,
		"roles": roles,
		"temp_password_pending": temp_pw_pending,
	}


@frappe.whitelist(allow_guest=True)
def logout():
	frappe.local.login_manager.logout()
	frappe.db.commit()
	return {"ok": True}


@frappe.whitelist(allow_guest=True)
def whoami():
	user = frappe.session.user
	roles = frappe.get_roles(user) if user != "Guest" else []
	temp_pw_pending = bool(frappe.cache().get_value(f"music_temp_pw:{user}")) if user != "Guest" else False
	return {"user": user, "roles": roles, "temp_password_pending": temp_pw_pending}
