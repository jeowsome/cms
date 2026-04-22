import frappe
from frappe.utils import getdate


@frappe.whitelist(allow_guest=True)
def get_published_schedule(month=None, year=None):
	"""Get the latest published ministry schedule. If month/year not specified, returns the most recent."""
	filters = {"status": "Published"}
	if month and year:
		filters["month"] = month
		filters["year"] = int(year)

	schedules = frappe.get_all(
		"Ministry Schedule",
		filters=filters,
		fields=["name", "month", "year", "published_on"],
		order_by="year desc, published_on desc",
		limit=1,
	)

	if not schedules:
		return {"schedule": None}

	doc = frappe.get_doc("Ministry Schedule", schedules[0].name)

	sundays = []
	for s in doc.sundays:
		sundays.append({
			"sunday_date": str(s.sunday_date),
			"theme": s.theme,
			"sermon_title": s.sermon_title,
			"sermon_passage": s.sermon_passage,
		})

	assignments = []
	for a in doc.assignments:
		member_doc = frappe.db.get_value(
			"Church Member", a.member,
			["firstname", "lastname", "envelope_number"],
			as_dict=True,
		)
		assignments.append({
			"sunday_date": str(a.sunday_date),
			"ministry": a.ministry,
			"member": a.member,
			"member_name": f"{member_doc.firstname} {member_doc.lastname}" if member_doc else a.member,
		})

	ministries = list({a["ministry"] for a in assignments})
	ministry_details = {}
	for m in ministries:
		ministry_details[m] = frappe.db.get_value("Ministry", m, "ministry_name") or m

	return {
		"schedule": {
			"name": doc.name,
			"month": doc.month,
			"year": doc.year,
			"published_on": str(doc.published_on) if doc.published_on else None,
			"sundays": sorted(sundays, key=lambda x: x["sunday_date"]),
			"assignments": assignments,
			"ministries": ministry_details,
		}
	}


@frappe.whitelist()
def get_members_for_scheduling():
	"""Get all church members with their ministry associations."""
	members = frappe.get_all(
		"Church Member",
		fields=["name", "firstname", "lastname", "envelope_number"],
		order_by="firstname asc",
	)

	for m in members:
		m["ministries"] = [
			r.ministry for r in frappe.get_all(
				"Church Member Ministry",
				filters={"parent": m["name"]},
				fields=["ministry"],
			)
		]
		m["full_name"] = f"{m['firstname']} {m['lastname']}"

	return members


@frappe.whitelist()
def get_active_ministries():
	"""Get all active ministries."""
	return frappe.get_all(
		"Ministry",
		filters={"active": 1},
		fields=["name", "ministry_name", "head"],
		order_by="ministry_name asc",
	)


@frappe.whitelist()
def get_available_months():
	"""Get list of months that have published schedules."""
	return frappe.get_all(
		"Ministry Schedule",
		filters={"status": "Published"},
		fields=["name", "month", "year", "published_on"],
		order_by="year desc, published_on desc",
	)
