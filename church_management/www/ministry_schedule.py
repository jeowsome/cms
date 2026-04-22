import frappe
from frappe.utils import getdate, formatdate
import calendar


def get_context(context):
	context.no_cache = 1
	context.show_sidebar = False

	selected_month = frappe.form_dict.get("month", "")
	selected_year = frappe.form_dict.get("year", "")

	# Get published schedules for the month picker
	published = frappe.get_all(
		"Ministry Schedule",
		filters={"status": "Published"},
		fields=["name", "month", "year", "published_on"],
		order_by="year desc, published_on desc",
	)

	available_months = [{"name": p.name, "month": p.month, "year": p.year} for p in published]

	# Determine which schedule to show
	schedule = None
	if selected_month and selected_year:
		matches = [p for p in published if p.month == selected_month and str(p.year) == str(selected_year)]
		if matches:
			schedule = frappe.get_doc("Ministry Schedule", matches[0].name)
	elif published:
		schedule = frappe.get_doc("Ministry Schedule", published[0].name)

	# Build structured data for template
	schedule_data = None
	if schedule:
		# Collect sunday info
		sundays = []
		for s in sorted(schedule.sundays, key=lambda x: str(x.sunday_date)):
			d = getdate(s.sunday_date)
			sundays.append({
				"date": s.sunday_date,
				"day": d.day,
				"weekday": d.strftime("%A"),
				"month_short": d.strftime("%b").upper(),
				"theme": s.theme or "",
				"sermon_title": s.sermon_title or "",
				"sermon_passage": s.sermon_passage or "",
			})

		# Build assignments grouped by sunday_date -> ministry -> [members]
		assignments_map = {}
		for a in schedule.assignments:
			sd = str(a.sunday_date)
			if sd not in assignments_map:
				assignments_map[sd] = {}
			if a.ministry not in assignments_map[sd]:
				assignments_map[sd][a.ministry] = []

			member = frappe.db.get_value(
				"Church Member", a.member,
				["firstname", "lastname"],
				as_dict=True,
			)
			name = f"{member.firstname} {member.lastname}" if member else a.member
			initials = "".join([p[0].upper() for p in name.split()[:2]])
			assignments_map[sd][a.ministry].append({
				"member": a.member,
				"name": name,
				"initials": initials,
			})

		# Get distinct ministries used in assignments
		all_ministries = sorted(set(
			a.ministry for a in schedule.assignments
		))

		# Ministry color mapping
		ministry_colors = _get_ministry_colors(all_ministries)

		schedule_data = {
			"name": schedule.name,
			"month": schedule.month,
			"year": schedule.year,
			"published_on": schedule.published_on,
			"sundays": sundays,
			"assignments": assignments_map,
			"ministries": all_ministries,
			"ministry_colors": ministry_colors,
		}

	context.schedule = schedule_data
	context.available_months = available_months
	context.selected_month = selected_month
	context.selected_year = selected_year


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
