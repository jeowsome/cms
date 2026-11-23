"""Church calendar rules shared by the GPOA planner, the calendar API and the
Church Activity controller.

- Recurrence: turns a GPOA Regular Activity rule ("2nd & 4th Sunday",
  "quarterly from March") into dates.
- Conflicts: two activities may share a day, but not an on-premises venue at
  the same time, and an activity must not overlap a worship service unless it
  is part of the service, or replaces it with the pastor's approval.

The conflict functions are pure (they take plain dicts) so the same code
checks one activity on save and annotates a whole month for the calendar.
"""
import calendar as _cal
import re
from datetime import date, datetime, time, timedelta

import frappe
from frappe.utils import getdate

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

SEPARATE = "Separate from worship service"
PART_OF_SERVICE = "Part of worship service"
REPLACES = "Replaces worship service"

# Statuses that occupy the calendar. Cancelled and Done never conflict.
ACTIVE_STATUSES = ("Proposed", "Confirmed")

# How many months apart a frequency repeats; weekly and twice-a-month run
# every month.
MONTH_STEP = {
	"Weekly": 1,
	"Twice a Month": 1,
	"Monthly": 1,
	"Every 2 Months": 2,
	"Quarterly": 3,
	"Thrice a Year": 4,
	"Yearly": 12,
}
DEFAULT_WEEKS = {"Twice a Month": "1,3"}


# ---------------------------------------------------------------- recurrence


def parse_weeks(text):
	"""'2nd & 4th' → [2, 4]; '1st & Last' → [1, -1]. -1 means the last week."""
	out = []
	for tok in re.findall(r"last|\d", (text or "").lower()):
		n = -1 if tok == "last" else int(tok)
		if (n == -1 or 1 <= n <= 5) and n not in out:
			out.append(n)
	return out


def parse_months(text):
	out = []
	for tok in re.findall(r"\d+", text or ""):
		n = int(tok)
		if 1 <= n <= 12 and n not in out:
			out.append(n)
	return sorted(out)


def rule_months(frequency, start_month=None, months=None):
	explicit = parse_months(months)
	if explicit:
		return explicit
	start = int(start_month or 1)
	if not 1 <= start <= 12:
		start = 1
	if frequency == "Yearly":
		return [start]
	step = MONTH_STEP.get(frequency, 1)
	return [m for m in range(1, 13) if (m - start) % step == 0]


def weekdays_in_month(year, month, weekday):
	"""Every date in the month falling on `weekday` (0 = Monday)."""
	_, ndays = _cal.monthrange(year, month)
	first = date(year, month, 1)
	offset = (weekday - first.weekday()) % 7
	return [first + timedelta(days=d) for d in range(offset, ndays, 7)]


def occurrence_dates(rule, year, from_date=None, to_date=None):
	"""Dates in `year` for a regular-activity rule (dict-like with frequency,
	weekday, weeks_of_month, start_month, months)."""
	frequency = rule.get("frequency") or "Monthly"
	weekday = WEEKDAYS.index(rule.get("weekday") or "Sunday")
	weeks = parse_weeks(rule.get("weeks_of_month"))
	if not weeks and frequency != "Weekly":
		weeks = parse_weeks(DEFAULT_WEEKS.get(frequency, "1"))

	out = set()
	for month in rule_months(frequency, rule.get("start_month"), rule.get("months")):
		days = weekdays_in_month(int(year), month, weekday)
		if not weeks:
			out.update(days)
			continue
		for w in weeks:
			if w == -1:
				out.add(days[-1])
			elif w <= len(days):
				out.add(days[w - 1])
	from_date = getdate(from_date) if from_date else None
	to_date = getdate(to_date) if to_date else None
	return sorted(d for d in out if (not from_date or d >= from_date) and (not to_date or d <= to_date))


# ---------------------------------------------------------------- time windows


def to_time(value):
	"""Frappe returns Time fields as timedelta from the DB and str from the
	client; normalise both to datetime.time."""
	if value in (None, ""):
		return None
	if isinstance(value, time):
		return value
	if isinstance(value, timedelta):
		secs = int(value.total_seconds()) % 86400
		return time(secs // 3600, (secs % 3600) // 60, secs % 60)
	parts = str(value).split(".")[0].split(":")
	try:
		h, m = int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
		s = int(parts[2]) if len(parts) > 2 else 0
		return time(h, m, s)
	except (ValueError, IndexError):
		return None


def interval(a):
	"""[start, end) datetimes an activity occupies. All-day (or time not set)
	occupies whole days; timed multi-day activities run continuously from the
	first day's start time to the last day's end time (e.g. a retreat)."""
	sd = getdate(a.get("start_date"))
	ed = getdate(a.get("end_date") or a.get("start_date"))
	st, et = to_time(a.get("start_time")), to_time(a.get("end_time"))
	if a.get("all_day") or not st or not et:
		return datetime.combine(sd, time.min), datetime.combine(ed + timedelta(days=1), time.min)
	return datetime.combine(sd, st), datetime.combine(ed, et)


def fmt_time(t):
	t = to_time(t)
	if not t:
		return ""
	h = t.hour % 12 or 12
	return f"{h}:{t.minute:02d} {'AM' if t.hour < 12 else 'PM'}"


def services_overlapping(a, services):
	"""[(service, date)] for every worship service the activity overlaps."""
	start, end = interval(a)
	if end <= start:
		return []
	out = []
	d, last = start.date(), (end - timedelta(microseconds=1)).date()
	while d <= last:
		dayname = WEEKDAYS[d.weekday()]
		for s in services:
			if s.get("weekday") != dayname:
				continue
			ws = datetime.combine(d, to_time(s.get("start_time")))
			we = datetime.combine(d, to_time(s.get("end_time")))
			if ws < end and start < we:
				out.append((s, d))
		d += timedelta(days=1)
	return out


def overlaps(a, b):
	a0, a1 = interval(a)
	b0, b1 = interval(b)
	return a0 < b1 and b0 < a1


# ---------------------------------------------------------------- conflicts


def conflicts_for(a, others, services, premises):
	"""Conflicts of activity `a` against `others` (other activities) and the
	weekly worship services. `premises` is the set of on-premises venue names.

	Returns a list of dicts: kind 'service' (overlaps a worship service) or
	'venue' (same on-premises venue at the same time)."""
	if (a.get("status") or "Proposed") not in ACTIVE_STATUSES:
		return []
	relation = a.get("service_relation") or SEPARATE
	out = []
	if relation != PART_OF_SERVICE:
		for s, d in services_overlapping(a, services):
			out.append({
				"kind": "service",
				"service": s.get("name") or s.get("service_name"),
				"date": str(d),
				"message": f"Overlaps {s.get('name') or s.get('service_name')} on {d.strftime('%a %b %-d')} "
				f"({fmt_time(s.get('start_time'))}–{fmt_time(s.get('end_time'))})",
			})
	venue = a.get("venue")
	if venue and venue in premises and relation != PART_OF_SERVICE:
		for o in others:
			if o.get("name") and o.get("name") == a.get("name"):
				continue
			if o.get("venue") != venue or (o.get("status") or "Proposed") not in ACTIVE_STATUSES:
				continue
			if (o.get("service_relation") or SEPARATE) == PART_OF_SERVICE:
				continue
			if overlaps(a, o):
				out.append({
					"kind": "venue",
					"activity": o.get("name"),
					"title": o.get("title"),
					"department": o.get("department"),
					"message": f"{venue} is taken by “{o.get('title')}” ({o.get('department')}) "
					f"on {getdate(o.get('start_date')).strftime('%a %b %-d')}"
					+ (f", {fmt_time(o.get('start_time'))}–{fmt_time(o.get('end_time'))}" if not o.get("all_day") and o.get("start_time") else ", all day"),
				})
	return out


ACTIVITY_FIELDS = [
	"name", "title", "department", "status", "start_date", "end_date", "all_day",
	"start_time", "end_time", "venue", "service_relation", "pastor_approval",
]


def active_services():
	return frappe.get_all(
		"Worship Service",
		filters={"active": 1},
		fields=["name", "service_name", "weekday", "start_time", "end_time", "venue"],
		order_by="start_time asc",
	)


def premises_venues():
	return set(frappe.get_all("Church Venue", filters={"on_premises": 1}, pluck="name"))


def activities_between(from_date, to_date, extra_filters=None, fields=None):
	"""Activities whose date range touches [from_date, to_date]."""
	filters = {"start_date": ["<=", to_date], "end_date": [">=", from_date]}
	filters.update(extra_filters or {})
	return frappe.get_all(
		"Church Activity", filters=filters, fields=fields or ACTIVITY_FIELDS,
		order_by="start_date asc, start_time asc", limit_page_length=0,
	)


def check(a):
	"""Conflicts for one activity (dict or doc) against the database."""
	a = a.as_dict() if hasattr(a, "as_dict") else a
	if not a.get("start_date"):
		return []
	others = []
	if a.get("venue"):
		others = activities_between(
			a.get("start_date"), a.get("end_date") or a.get("start_date"),
			{"venue": a.get("venue"), "status": ["in", ACTIVE_STATUSES]},
		)
	return conflicts_for(a, others, active_services(), premises_venues())


def annotate(activities, services=None, premises=None):
	"""Add a `conflicts` list to every activity in the list (in place)."""
	services = active_services() if services is None else services
	premises = premises_venues() if premises is None else premises
	for a in activities:
		a["conflicts"] = conflicts_for(a, activities, services, premises)
	return activities
