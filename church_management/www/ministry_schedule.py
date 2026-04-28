import frappe
from frappe.utils import getdate, formatdate
import calendar

_MONTH_INDEX = {name: i for i, name in enumerate(calendar.month_name) if name}


def get_context(context):
	context.no_cache = 1
	context.show_sidebar = False

	selected_name = frappe.form_dict.get("schedule", "")

	# Get published schedules for the month picker, sorted most recent first
	published = frappe.get_all(
		"Ministry Schedule",
		filters={"status": "Published"},
		fields=["name", "month", "year", "published_on"],
	)
	published.sort(key=lambda p: (p.year, _MONTH_INDEX.get(p.month, 0)), reverse=True)

	available_months = [{"name": p.name, "month": p.month, "year": p.year} for p in published]

	# Determine which schedule to show
	schedule = None
	if selected_name:
		match = next((p for p in published if p.name == selected_name), None)
		if match:
			schedule = frappe.get_doc("Ministry Schedule", match.name)

	if not schedule and published:
		# Default to the published schedule nearest to today; on ties prefer current/future over past
		today = getdate()
		today_ym = today.year * 12 + today.month

		def distance_key(p):
			ym = p.year * 12 + _MONTH_INDEX.get(p.month, 0)
			diff = ym - today_ym
			return (abs(diff), 0 if diff >= 0 else 1)

		nearest = min(published, key=distance_key)
		schedule = frappe.get_doc("Ministry Schedule", nearest.name)

	# Build structured data for template
	schedule_data = None
	if schedule:
		def _service_row(s, service_type):
			d = getdate(s.sunday_date)
			return {
				"date": s.sunday_date,
				"day": d.day,
				"weekday": d.strftime("%A"),
				"month_short": d.strftime("%b").upper(),
				"theme": s.theme or "",
				"sermon_title": s.sermon_title or "",
				"sermon_passage": s.sermon_passage or "",
				"type": service_type,
			}

		sundays = [_service_row(s, "Sunday")
			for s in sorted(schedule.sundays, key=lambda x: str(x.sunday_date))]
		wednesdays = [_service_row(s, "Wednesday")
			for s in sorted(getattr(schedule, "wednesdays", []) or [], key=lambda x: str(x.sunday_date))]

		# Batch-fetch full names for linked members. member_name on the assignment
		# row is only firstname (fetch_from supports a single field path), so it's
		# unreliable as a display name — resolve the Church Member record instead.
		linked_ids = {a.member for a in schedule.assignments if a.member}
		member_names = {}
		if linked_ids:
			for r in frappe.get_all(
				"Church Member",
				filters={"name": ["in", list(linked_ids)]},
				fields=["name", "firstname", "lastname"],
			):
				member_names[r.name] = f"{r.firstname or ''} {r.lastname or ''}".strip()

		# Build assignments grouped by sunday_date -> ministry -> {all/morning/evening: [members]}
		assignments_map = {}
		for a in schedule.assignments:
			sd = str(a.sunday_date)
			if sd not in assignments_map:
				assignments_map[sd] = {}
			if a.ministry not in assignments_map[sd]:
				assignments_map[sd][a.ministry] = {"all": [], "morning": [], "evening": []}

			# Linked member → always use the full Member record name.
			# Guest (no member link) → use the typed member_name as-is.
			if a.member and member_names.get(a.member):
				name = member_names[a.member]
			else:
				name = (a.member_name or "").strip() or a.member or "Unknown"

			initials = "".join([p[0].upper() for p in name.split()[:2]]) or "?"
			entry = {
				"member": a.member or "",
				"name": name,
				"initials": initials,
				"is_guest": not bool(a.member),
			}
			slot = (a.service_time or "").lower()
			if slot not in ("morning", "evening"):
				slot = "all"
			assignments_map[sd][a.ministry][slot].append(entry)

		# Collapse: if Morning + Evening have the same single person, treat as "all"
		# so the public page shows one name (indicates assignment for both services).
		for sd, ministries in assignments_map.items():
			for ministry, slots in ministries.items():
				m_names = sorted(p["name"] for p in slots["morning"])
				e_names = sorted(p["name"] for p in slots["evening"])
				if m_names and m_names == e_names:
					slots["all"].extend(slots["morning"])
					slots["morning"] = []
					slots["evening"] = []

		# Get distinct ministries used in assignments
		all_ministries = sorted(set(
			a.ministry for a in schedule.assignments
		))

		# Ministry color mapping
		ministry_colors = _get_ministry_colors(all_ministries)

		# Combine Sundays + Wednesdays into chronological week buckets.
		# Group by ISO week so a Wednesday and the following Sunday share a "Week N".
		all_services = sorted(sundays + wednesdays, key=lambda s: str(s["date"]))
		weeks = []
		current_iso = None
		for service in all_services:
			# Attach this service's per-ministry assignments
			service["assignments_by_ministry"] = assignments_map.get(str(service["date"]), {})
			iso_week = getdate(service["date"]).isocalendar()[1]
			if iso_week != current_iso:
				current_iso = iso_week
				weeks.append({"number": len(weeks) + 1, "services": []})
			weeks[-1]["services"].append(service)

		schedule_data = {
			"name": schedule.name,
			"month": schedule.month,
			"year": schedule.year,
			"published_on": schedule.published_on,
			"sundays": sundays,
			"wednesdays": wednesdays,
			"weeks": weeks,
			"assignments": assignments_map,
			"ministries": all_ministries,
			"ministry_colors": ministry_colors,
		}

	context.schedule = schedule_data
	context.available_months = available_months
	context.selected_name = selected_name


def _get_ministry_colors(ministries):
	"""Assign color classes to ministries for visual distinction."""
	palette = [
		{"bg": "bg-amber-50", "text": "text-amber-800", "dot": "bg-amber-500", "ring": "ring-amber-200", "icon_bg": "bg-amber-50"},
		{"bg": "bg-rose-50", "text": "text-rose-800", "dot": "bg-rose-500", "ring": "ring-rose-200", "icon_bg": "bg-rose-50"},
		{"bg": "bg-sky-50", "text": "text-sky-800", "dot": "bg-sky-500", "ring": "ring-sky-200", "icon_bg": "bg-sky-50"},
		{"bg": "bg-emerald-50", "text": "text-emerald-800", "dot": "bg-emerald-500", "ring": "ring-emerald-200", "icon_bg": "bg-emerald-50"},
		{"bg": "bg-violet-50", "text": "text-violet-800", "dot": "bg-violet-500", "ring": "ring-violet-200", "icon_bg": "bg-violet-50"},
		{"bg": "bg-indigo-50", "text": "text-indigo-800", "dot": "bg-indigo-500", "ring": "ring-indigo-200", "icon_bg": "bg-indigo-50"},
		{"bg": "bg-pink-50", "text": "text-pink-800", "dot": "bg-pink-500", "ring": "ring-pink-200", "icon_bg": "bg-pink-50"},
		{"bg": "bg-teal-50", "text": "text-teal-800", "dot": "bg-teal-500", "ring": "ring-teal-200", "icon_bg": "bg-teal-50"},
		{"bg": "bg-orange-50", "text": "text-orange-800", "dot": "bg-orange-500", "ring": "ring-orange-200", "icon_bg": "bg-orange-50"},
		{"bg": "bg-cyan-50", "text": "text-cyan-800", "dot": "bg-cyan-500", "ring": "ring-cyan-200", "icon_bg": "bg-cyan-50"},
	]
	colors = {}
	for i, m in enumerate(ministries):
		colors[m] = palette[i % len(palette)]
	return colors
