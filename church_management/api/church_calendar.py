"""Church calendar endpoints.

`get_calendar` is open to guests for the public calendar page: guests (and
users without planning access) see only confirmed, public activities and no
budgets or notes. Planners also see proposed activities, conflicts and
budgets, and may add and change activities for their departments.
"""
import json

import frappe
from frappe import _
from frappe.utils import getdate, now_datetime

from church_management.api import permissions as perms
from church_management.api.gpoa import ACTIVITY_FIELDS, published_gpoas
from church_management.church_management import church_calendar as cal

PUBLIC_STATUSES = ("Confirmed", "Done")
PUBLIC_FIELDS = (
	"name", "title", "department", "status", "start_date", "end_date", "all_day",
	"start_time", "end_time", "venue", "location_details", "service_relation", "pastor_approval",
)
EDITABLE = (
	"title", "department", "status", "start_date", "end_date", "all_day", "start_time", "end_time",
	"venue", "location_details", "service_relation", "budget", "transport_needed", "headcount",
	"notes", "is_public",
)
MAX_RANGE_DAYS = 400


def _loads(data):
	return json.loads(data) if isinstance(data, str) else (data or {})


def _time_str(v):
	t = cal.to_time(v)
	return t.strftime("%H:%M") if t else None


def _clean(a, fields):
	out = {f: a.get(f) for f in fields}
	for f in ("start_time", "end_time"):
		if f in out:
			out[f] = _time_str(out[f])
	for f in ("start_date", "end_date"):
		if out.get(f):
			out[f] = str(out[f])
	return out


def _services():
	return [
		{**s, "start_time": _time_str(s.start_time), "end_time": _time_str(s.end_time)}
		for s in cal.active_services()
	]


@frappe.whitelist(allow_guest=True)
def get_calendar(from_date, to_date, include_proposed=1, include_cancelled=0):
	from_date, to_date = getdate(from_date), getdate(to_date)
	if to_date < from_date or (to_date - from_date).days > MAX_RANGE_DAYS:
		frappe.throw(_("Choose a shorter date range."))

	planner = frappe.session.user != "Guest" and perms.has_planning_access()
	services = cal.active_services()
	premises = cal.premises_venues()

	statuses = list(PUBLIC_STATUSES)
	if planner and int(include_proposed):
		statuses.append("Proposed")
	if planner and int(include_cancelled):
		statuses.append("Cancelled")
	filters = {"status": ["in", statuses]}
	published = published_gpoas()
	if not planner:
		# Members see only years the church has published, and only the
		# activities marked public in them.
		filters["is_public"] = 1
		filters["gpoa"] = ["in", published or [""]]
	rows = cal.activities_between(from_date, to_date, filters, ACTIVITY_FIELDS if planner else list(PUBLIC_FIELDS))

	# Services replaced (with the pastor's approval) on specific dates.
	replaced = []
	for a in rows:
		if a.service_relation == cal.REPLACES and a.pastor_approval == "Approved" and a.status in PUBLIC_STATUSES:
			for s, d in cal.services_overlapping(a, services):
				replaced.append({"service": s.name, "date": str(d), "by": a.title})

	if planner:
		# Conflicts against every active activity, not only the shown ones.
		active = cal.activities_between(from_date, to_date, {"status": ["in", cal.ACTIVE_STATUSES]})
		for a in rows:
			a["conflicts"] = cal.conflicts_for(a, active, services, premises)
		allowed = perms.planning_departments()
		activities = []
		for a in rows:
			out = _clean(a, ACTIVITY_FIELDS + ["conflicts"])
			out["can_edit"] = allowed is None or a.department in allowed
			activities.append(out)
	else:
		activities = [_clean(a, PUBLIC_FIELDS) for a in rows]

	return {
		"activities": activities,
		"services": _services(),
		"replaced": replaced,
		"planner": planner,
		"published_years": frappe.get_all("GPOA", filters={"calendar_published": 1}, pluck="year", order_by="year asc"),
		"departments": frappe.get_all("Department Name", pluck="name", order_by="name asc"),
	}


@frappe.whitelist()
def get_planner_options():
	"""Pickers for the activity form."""
	perms.require_planning_access()
	return {
		"departments": frappe.get_all("Department Name", pluck="name", order_by="name asc"),
		"my_departments": perms.planning_departments(),
		"venues": frappe.get_all("Church Venue", filters={"active": 1}, fields=["name", "on_premises"], order_by="name asc"),
		"services": _services(),
		"is_pastor": perms.is_pastor(),
	}


def _apply(doc, data):
	for f in EDITABLE:
		if f in data:
			doc.set(f, data[f] if data[f] != "" else None)


@frappe.whitelist()
def check_activity(data):
	"""Conflicts an activity would have, without saving it."""
	perms.require_planning_access()
	data = _loads(data)
	a = frappe._dict({f: data.get(f) for f in EDITABLE})
	a.name = data.get("name")
	a.status = a.status or "Proposed"
	if not a.start_date:
		return []
	a.end_date = a.end_date or a.start_date
	if a.all_day:
		a.start_time = a.end_time = None
	return cal.check(a)


@frappe.whitelist()
def save_activity(data):
	perms.require_planning_access()
	data = _loads(data)
	perms.require_department(data.get("department"))
	if data.get("name"):
		doc = frappe.get_doc("Church Activity", data["name"])
		perms.require_department(doc.department)
	else:
		doc = frappe.new_doc("Church Activity")
	if data.get("status") == "Confirmed" and doc.status != "Confirmed" and not perms.is_planning_admin():
		frappe.throw(_("Finance Team, the pastor or Pasig Admin confirms activities."), frappe.PermissionError)
	_apply(doc, data)
	doc.save(ignore_permissions=True)
	return _clean(doc.as_dict(), ACTIVITY_FIELDS)


@frappe.whitelist()
def delete_activity(name):
	perms.require_planning_access()
	doc = frappe.get_doc("Church Activity", name)
	perms.require_department(doc.department)
	doc.delete(ignore_permissions=True)
	return True


@frappe.whitelist()
def pending_approvals():
	"""Activities asking to replace a worship service, for the pastor."""
	perms.require_planning_access()
	rows = frappe.get_all(
		"Church Activity",
		filters={"service_relation": cal.REPLACES, "status": ["in", cal.ACTIVE_STATUSES], "pastor_approval": "Requested"},
		fields=ACTIVITY_FIELDS,
		order_by="start_date asc",
	)
	return [_clean(a, ACTIVITY_FIELDS) for a in rows]


@frappe.whitelist()
def decide_service_replacement(name, decision, remarks=None):
	"""The pastor approves or declines an activity replacing a worship service."""
	perms.require_pastor()
	if decision not in ("Approved", "Declined"):
		frappe.throw(_("Choose Approved or Declined."))
	doc = frappe.get_doc("Church Activity", name)
	if doc.service_relation != cal.REPLACES:
		frappe.throw(_("This activity does not replace a worship service."))
	doc.pastor_approval = decision
	doc.approved_by = frappe.session.user
	doc.approved_on = now_datetime()
	doc.approval_remarks = remarks
	if decision == "Declined" and doc.status == "Confirmed":
		doc.status = "Proposed"
	doc.flags.pastor_decision = True
	doc.save(ignore_permissions=True)
	return _clean(doc.as_dict(), ACTIVITY_FIELDS)


@frappe.whitelist()
def add_venue(venue_name, on_premises=0):
	perms.require_planning_access()
	venue_name = (venue_name or "").strip()
	if not venue_name:
		frappe.throw(_("Enter a venue name."))
	existing = frappe.db.get_value("Church Venue", {"venue_name": venue_name}, "name")
	if existing:
		return existing
	return frappe.get_doc({
		"doctype": "Church Venue", "venue_name": venue_name, "on_premises": 1 if int(on_premises) else 0,
	}).insert(ignore_permissions=True).name
