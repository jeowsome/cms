"""GPOA (General Planning of Activities) endpoints for the SPA.

Finance Team, the pastor, Pasig Admin and Administrator plan every
department. Department users (the ones on a department's Donation record)
add and change only their own departments' goals, regular activities,
activities and budget requests.
"""
import json
from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import flt, getdate, now_datetime, nowdate

from church_management.api import permissions as perms
from church_management.church_management import church_calendar as cal

METRICS = ["Attendance", "PRC", "Baptism", "Finance"]

# Disbursement purposes that pay for planned activities, for plan-vs-actual.
REGULAR_PURPOSE = "Regular Activity"
SPECIAL_PURPOSE = "Special Event"

GOAL_FIELDS = ["name", "department", "metric", "target", "actual", "remarks"]
REGULAR_FIELDS = [
	"name", "department", "description", "active", "on_calendar", "frequency", "weekday", "weeks_of_month",
	"start_month", "months", "all_day", "start_time", "end_time", "venue", "service_relation",
	"budget_per_occurrence", "occurrences", "annual_budget", "notes",
]
REQUEST_FIELDS = [
	"name", "department", "area", "description", "amount", "source_of_fund", "priority", "status", "notes",
]
ACTIVITY_FIELDS = cal.ACTIVITY_FIELDS + [
	"gpoa", "regular_activity", "budget", "transport_needed", "headcount", "notes",
	"location_details", "is_public", "approved_by", "approval_remarks",
]


def _loads(data):
	return json.loads(data) if isinstance(data, str) else (data or {})


def _gpoa_name(year):
	return frappe.db.get_value("GPOA", {"year": int(year)}, "name")


def _require_gpoa(name):
	if not name or not frappe.db.exists("GPOA", name):
		frappe.throw(_("GPOA not found."))
	return name


def _scope(rows):
	"""Mark which rows the user may edit, and send times as HH:MM."""
	allowed = perms.planning_departments()
	for r in rows:
		r["can_edit"] = allowed is None or r.get("department") in allowed
		for f in ("start_time", "end_time"):
			if f in r:
				t = cal.to_time(r[f])
				r[f] = t.strftime("%H:%M") if t else None
		for f in ("start_date", "end_date"):
			if r.get(f):
				r[f] = str(r[f])
	return rows


# ------------------------------------------------------------------ overview


@frappe.whitelist()
def get_years():
	perms.require_planning_access()
	return {
		"years": frappe.get_all("GPOA", fields=["name", "year", "status"], order_by="year asc"),
		"can_create": perms.is_planning_admin(),
	}


def _departments():
	return frappe.get_all("Department Name", pluck="name", order_by="name asc")


def _collections_total(year):
	return flt(frappe.db.sql(
		"""select sum(all_grand_total) from `tabCollection`
		where docstatus = 1 and year(`date`) = %s""",
		int(year),
	)[0][0])


def _spent_by_department(year):
	"""Claimed and committed activity spending per department in a year,
	from disbursements whose purpose is Regular Activity or Special Event."""
	from church_management.church_management import finance as fin

	out = defaultdict(lambda: {"regular": 0.0, "special": 0.0})
	try:
		lines = fin.collect_lines(year=int(year), include_cancelled=False)
	except Exception:
		frappe.log_error(title="GPOA: could not read disbursements")
		return {}
	for ln in lines:
		if not ln.counted or ln.year != int(year):
			continue
		if ln.purpose == REGULAR_PURPOSE:
			out[ln.department or "—"]["regular"] += flt(ln.amount)
		elif ln.purpose == SPECIAL_PURPOSE:
			out[ln.department or "—"]["special"] += flt(ln.amount)
	return dict(out)


def _planned_by_department(gpoa):
	out = defaultdict(lambda: {"regular": 0.0, "scheduled": 0.0, "requests": 0.0})
	if not gpoa:
		return {}
	for r in frappe.get_all("GPOA Regular Activity", filters={"gpoa": gpoa, "active": 1}, fields=["department", "annual_budget"]):
		out[r.department]["regular"] += flt(r.annual_budget)
	# Generated dates carry their rule's budget, which is already in "regular".
	for a in frappe.get_all(
		"Church Activity",
		filters={"gpoa": gpoa, "status": ["!=", "Cancelled"], "regular_activity": ["is", "not set"]},
		fields=["department", "budget"],
	):
		out[a.department]["scheduled"] += flt(a.budget)
	for b in frappe.get_all("GPOA Budget Request", filters={"gpoa": gpoa, "status": ["!=", "Declined"]}, fields=["department", "amount"]):
		out[b.department]["requests"] += flt(b.amount)
	return dict(out)


def budget_summary(year):
	"""Per department: this year's plan, last year's plan, and what was
	actually spent last year and so far this year."""
	year = int(year)
	this_plan = _planned_by_department(_gpoa_name(year))
	prev_plan = _planned_by_department(_gpoa_name(year - 1))
	spent_prev = _spent_by_department(year - 1)
	spent_now = _spent_by_department(year)
	rows = []
	for d in sorted(set(this_plan) | set(prev_plan) | set(spent_prev) | set(spent_now)):
		p = this_plan.get(d, {"regular": 0, "scheduled": 0, "requests": 0})
		q = prev_plan.get(d, {"regular": 0, "scheduled": 0, "requests": 0})
		sp = spent_prev.get(d, {"regular": 0, "special": 0})
		sn = spent_now.get(d, {"regular": 0, "special": 0})
		rows.append({
			"department": d,
			"regular": p["regular"], "scheduled": p["scheduled"], "requests": p["requests"],
			"activities": p["regular"] + p["scheduled"], "total": p["regular"] + p["scheduled"] + p["requests"],
			"prev_activities": q["regular"] + q["scheduled"], "prev_total": q["regular"] + q["scheduled"] + q["requests"],
			"prev_spent": sp["regular"] + sp["special"], "spent": sn["regular"] + sn["special"],
		})
	return rows


@frappe.whitelist()
def get_gpoa(year):
	"""Everything the planner shows for one year, with last year beside it."""
	perms.require_planning_access()
	year = int(year)
	name = _gpoa_name(year)
	prev = _gpoa_name(year - 1)
	if not name:
		return {"exists": False, "year": year, "prev": prev, "can_create": perms.is_planning_admin()}

	doc = frappe.get_doc("GPOA", name)
	goals = frappe.get_all("GPOA Goal", filters={"gpoa": name}, fields=GOAL_FIELDS)
	prev_goals = frappe.get_all("GPOA Goal", filters={"gpoa": prev}, fields=GOAL_FIELDS) if prev else []
	regular = frappe.get_all(
		"GPOA Regular Activity", filters={"gpoa": name}, fields=REGULAR_FIELDS, order_by="department asc, description asc"
	)
	requests = frappe.get_all(
		"GPOA Budget Request", filters={"gpoa": name}, fields=REQUEST_FIELDS, order_by="department asc, creation asc"
	)
	activities = frappe.get_all(
		"Church Activity",
		filters={"gpoa": name, "regular_activity": ["is", "not set"]},
		fields=ACTIVITY_FIELDS,
		order_by="start_date asc, start_time asc",
		limit_page_length=0,
	)
	# Conflicts are checked against the whole calendar, generated dates included.
	everything = cal.activities_between(f"{year}-01-01", f"{year}-12-31")
	by_name = {a.name: a for a in cal.annotate(everything)}
	for a in activities:
		a["conflicts"] = by_name.get(a.name, {}).get("conflicts", [])
	generated = defaultdict(int)
	for r in frappe.get_all(
		"Church Activity", filters={"gpoa": name, "regular_activity": ["is", "set"]},
		fields=["regular_activity", "count(name) as n"], group_by="regular_activity",
	):
		generated[r.regular_activity] = r.n
	for r in regular:
		r["generated"] = generated.get(r.name, 0)

	allowed = perms.planning_departments()
	return {
		"exists": True,
		"year": year,
		"prev": prev,
		"gpoa": {
			"name": doc.name, "year": doc.year, "status": doc.status, "theme": doc.theme, "notes": doc.notes,
			"calendar_published": doc.calendar_published, "published_on": str(doc.published_on or "") or None,
			"published_by": frappe.utils.get_fullname(doc.published_by) if doc.published_by else None,
		},
		"public": public_summary(name),
		"goals": _scope(goals),
		"prev_goals": prev_goals,
		"regular": _scope(regular),
		"requests": _scope(requests),
		"activities": _scope(activities),
		"collections": {"this": _collections_total(year), "prev": _collections_total(year - 1)},
		"budget": budget_summary(year),
		"departments": _departments(),
		"my_departments": allowed,  # None = every department
		"is_admin": allowed is None,
		"metrics": METRICS,
		"venues": frappe.get_all("Church Venue", filters={"active": 1}, fields=["name", "on_premises"], order_by="name asc"),
	}


@frappe.whitelist()
def create_gpoa(year, copy_previous=1):
	"""Start a year's GPOA. Copies last year's regular activities (they
	usually continue) and lists last year's goal rows with blank targets."""
	perms.require_planning_admin()
	year = int(year)
	if _gpoa_name(year):
		frappe.throw(_("GPOA {0} already exists.").format(year))
	doc = frappe.get_doc({"doctype": "GPOA", "year": year, "status": "Planning"}).insert(ignore_permissions=True)
	prev = _gpoa_name(year - 1)
	if prev and int(copy_previous):
		for g in frappe.get_all("GPOA Goal", filters={"gpoa": prev}, fields=["department", "metric"]):
			frappe.get_doc({"doctype": "GPOA Goal", "gpoa": doc.name, "department": g.department, "metric": g.metric}).insert(ignore_permissions=True)
		for r in frappe.get_all("GPOA Regular Activity", filters={"gpoa": prev, "active": 1}, fields=REGULAR_FIELDS):
			r.pop("name")
			r.pop("occurrences", None)
			r.pop("annual_budget", None)
			frappe.get_doc({"doctype": "GPOA Regular Activity", "gpoa": doc.name, **r}).insert(ignore_permissions=True)
	return doc.name


@frappe.whitelist()
def update_gpoa(name, status=None, theme=None, notes=None):
	perms.require_planning_admin()
	doc = frappe.get_doc("GPOA", _require_gpoa(name))
	if status is not None:
		doc.status = status
	if theme is not None:
		doc.theme = theme
	if notes is not None:
		doc.notes = notes
	doc.save(ignore_permissions=True)
	return {"status": doc.status, "theme": doc.theme, "notes": doc.notes}


def public_summary(gpoa):
	"""What members would see of this year on the public calendar."""
	counts = defaultdict(int)
	for r in frappe.get_all(
		"Church Activity", filters={"gpoa": gpoa},
		fields=["status", "is_public", "count(name) as n"], group_by="status, is_public",
	):
		if r.status in ("Confirmed", "Done"):
			counts["shown" if r.is_public else "hidden"] += r.n
		elif r.status == "Proposed":
			counts["proposed"] += r.n
	return {"shown": counts["shown"], "hidden": counts["hidden"], "proposed": counts["proposed"]}


@frappe.whitelist()
def set_published(name, published):
	"""Publish (or withdraw) a year's activities on the members' calendar.
	Members never see budgets, transport, headcount or notes either way."""
	perms.require_planning_admin()
	doc = frappe.get_doc("GPOA", _require_gpoa(name))
	doc.calendar_published = 1 if int(published) else 0
	doc.published_on = now_datetime() if doc.calendar_published else None
	doc.published_by = frappe.session.user if doc.calendar_published else None
	doc.save(ignore_permissions=True)
	return public_summary(doc.name)


def published_gpoas():
	return frappe.get_all("GPOA", filters={"calendar_published": 1}, pluck="name")


# ------------------------------------------------------------------ goals


@frappe.whitelist()
def save_goal(gpoa, department, metric, target=None, actual=None, remarks=None):
	"""Create or update the goal for one department and metric."""
	perms.require_planning_access()
	_require_gpoa(gpoa)
	perms.require_department(department)
	if metric not in METRICS:
		frappe.throw(_("Unknown metric."))
	name = frappe.db.get_value("GPOA Goal", {"gpoa": gpoa, "department": department, "metric": metric})
	doc = frappe.get_doc("GPOA Goal", name) if name else frappe.get_doc(
		{"doctype": "GPOA Goal", "gpoa": gpoa, "department": department, "metric": metric}
	)
	doc.target = flt(target) if target not in (None, "") else None
	doc.actual = flt(actual) if actual not in (None, "") else None
	if remarks is not None:
		doc.remarks = remarks
	doc.save(ignore_permissions=True)
	return {k: doc.get(k) for k in GOAL_FIELDS}


@frappe.whitelist()
def delete_goal_department(gpoa, department):
	"""Remove a department's column from the goals table."""
	perms.require_planning_access()
	perms.require_department(department)
	frappe.db.delete("GPOA Goal", {"gpoa": _require_gpoa(gpoa), "department": department})
	return True


# ------------------------------------------------------------------ rows


def _save_row(doctype, fields, data):
	data = _loads(data)
	perms.require_planning_access()
	_require_gpoa(data.get("gpoa"))
	perms.require_department(data.get("department"))
	if data.get("name"):
		doc = frappe.get_doc(doctype, data["name"])
		perms.require_department(doc.department)  # can't move another dept's row
		if doc.gpoa != data.get("gpoa"):
			frappe.throw(_("This row belongs to another GPOA."))
	else:
		doc = frappe.get_doc({"doctype": doctype, "gpoa": data.get("gpoa")})
	for f in fields:
		if f in ("name", "occurrences", "annual_budget") or f not in data:
			continue
		doc.set(f, data[f])
	doc.save(ignore_permissions=True)
	return _scope([{f: doc.get(f) for f in fields}])[0]


def _delete_row(doctype, name):
	perms.require_planning_access()
	doc = frappe.get_doc(doctype, name)
	perms.require_department(doc.department)
	doc.delete(ignore_permissions=True)
	return True


@frappe.whitelist()
def save_regular(data):
	return _save_row("GPOA Regular Activity", REGULAR_FIELDS, data)


@frappe.whitelist()
def delete_regular(name, delete_generated=1):
	perms.require_planning_access()
	doc = frappe.get_doc("GPOA Regular Activity", name)
	perms.require_department(doc.department)
	for a in frappe.get_all("Church Activity", filters={"regular_activity": name}, fields=["name", "status", "start_date"]):
		if int(delete_generated) and a.status in cal.ACTIVE_STATUSES and getdate(a.start_date) >= getdate(nowdate()):
			frappe.delete_doc("Church Activity", a.name, ignore_permissions=True)
		else:
			frappe.db.set_value("Church Activity", a.name, "regular_activity", None, update_modified=False)
	doc.delete(ignore_permissions=True)
	return True


@frappe.whitelist()
def preview_regular(data, year):
	"""Dates a rule would produce, for the form's live preview."""
	perms.require_planning_access()
	return [str(d) for d in cal.occurrence_dates(_loads(data), int(year))]


@frappe.whitelist()
def save_budget_request(data):
	return _save_row("GPOA Budget Request", REQUEST_FIELDS, data)


@frappe.whitelist()
def delete_budget_request(name):
	return _delete_row("GPOA Budget Request", name)


# ------------------------------------------------------------------ generate


@frappe.whitelist()
def generate_dates(gpoa, regular=None, from_date=None):
	"""Put regular activities on the calendar as dated activities.

	Re-running replaces the future dates it generated before, except dates
	someone edited by hand. Dates that clash with another activity or a
	worship service are skipped and reported so they can be fixed by hand."""
	perms.require_planning_access()
	gpoa = _require_gpoa(gpoa)
	g = frappe.db.get_value("GPOA", gpoa, ["year", "status"], as_dict=True)
	from_date = getdate(from_date) if from_date else max(getdate(f"{g.year}-01-01"), getdate(nowdate()))
	filters = {"gpoa": gpoa, "active": 1, "on_calendar": 1}
	if regular:
		filters["name"] = regular
	rules = frappe.get_all("GPOA Regular Activity", filters=filters, fields=REGULAR_FIELDS)
	allowed = perms.planning_departments()
	rules = [r for r in rules if allowed is None or r.department in allowed]
	status = "Confirmed" if g.status == "Approved" else "Proposed"

	created, kept, skipped = 0, 0, []
	for r in rules:
		existing = frappe.get_all(
			"Church Activity",
			filters={"regular_activity": r.name, "start_date": [">=", from_date]},
			fields=["name", "start_date", "manually_edited", "status"],
		)
		keep_dates = set()
		for a in existing:
			if a.manually_edited or a.status not in cal.ACTIVE_STATUSES:
				keep_dates.add(getdate(a.start_date))
				kept += 1
			else:
				frappe.delete_doc("Church Activity", a.name, ignore_permissions=True)
		for d in cal.occurrence_dates(r, g.year, from_date=from_date):
			if d in keep_dates:
				continue
			doc = frappe.get_doc({
				"doctype": "Church Activity",
				"title": r.description,
				"department": r.department,
				"gpoa": gpoa,
				"regular_activity": r.name,
				"status": status,
				"start_date": d,
				"end_date": d,
				"all_day": 1 if (r.all_day or not r.start_time) else 0,
				"start_time": r.start_time,
				"end_time": r.end_time,
				"venue": r.venue,
				"service_relation": r.service_relation or cal.SEPARATE,
				"budget": r.budget_per_occurrence,
			})
			doc.flags.from_generator = True
			try:
				doc.insert(ignore_permissions=True)
				created += 1
			except frappe.ValidationError as e:
				frappe.clear_messages()
				skipped.append({"rule": r.description, "department": r.department, "date": str(d), "reason": frappe.utils.strip_html(str(e))})
	return {"created": created, "kept": kept, "skipped": skipped}
