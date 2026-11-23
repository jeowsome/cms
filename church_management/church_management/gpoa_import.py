"""One-off import of a GPOA workbook (the 2026 planning spreadsheet) so the
next GPOA can be compared with it.

	bench --site <site> execute church_management.church_management.gpoa_import.run \
		--kwargs "{'path': '/abs/path/GPOA 2026.xlsx', 'year': 2026}"

Sheets read: Goals, Regular Activities, Activities, Budget Request, Special
Notes. A goals cell "150 / 140" is this year's goal / last year's goal, so the
previous year's GPOA is created too (goals only). The workbook itself stays
out of the repository; nothing personal is hard-coded here.
"""
import re
from datetime import date, datetime, timedelta

import frappe
from frappe.utils import flt, getdate, nowdate

from church_management.church_management import church_calendar as cal

GOAL_COLUMNS = {
	"JBC Pasig": "Pasig General",
	"PSS": "Pasig Sunday School",
	"PColsPro": "Pasig ColSPro",
	"PYP": "Pasig Young People",
	"PJ": "Pasig Juniors",
	"PLadies": "Pasig Ladies",
	"PMen": "Pasig Men",
	"Cainta": "Cainta General",
}

DEPARTMENTS = {
	"ladies": "Pasig Ladies",
	"men": "Pasig Men",
	"colspro": "Pasig ColSPro",
	"yp": "Pasig Young People",
	"juniors": "Pasig Juniors",
	"pj": "Pasig Juniors",
	"ss": "Pasig Sunday School",
	"music team": "Pasig Music Team",
	"soc med": "Pasig SocMed",
	"socmed": "Pasig SocMed",
	"church": "Pasig General",
	"cainta": "Cainta General",
	"couples": "Pasig Couples",
	"disclipeship": "Pasig General",
	"discipleship": "Pasig General",
	"kitchen": "Pasig General",
}
NEW_DEPARTMENTS = ("Pasig Couples",)

VENUES = {
	"church": "Church",
	"3rd floor": "3rd Floor",
	"4th floor": "4th Floor",
	"jbc-cainta": "JBC Cainta",
	"cainta": "JBC Cainta",
}
UNKNOWN_VENUE = ("tba", "tbd", "")

FREQUENCIES = {
	"weekly": "Weekly",
	"twice a month": "Twice a Month",
	"monthly": "Monthly",
	"every 2 months": "Every 2 Months",
	"quarterly": "Quarterly",
	"thrice a year": "Thrice a Year",
	"yearly": "Yearly",
}
# Budget-only regular lines: no calendar dates.
NOT_ON_CALENDAR = ("rent", "bulletin")
PART_OF_SERVICE = ("special number",)


def _s(v):
	return str(v).strip() if v is not None else ""


def _dept(label):
	key = _s(label).lower()
	if not key:
		return "Pasig General"
	if key not in DEPARTMENTS:
		frappe.throw(f"Unknown department in workbook: {label}")
	return DEPARTMENTS[key]


def _number(text):
	"""'2.5M' → 2500000, '300K' → 300000, '150' → 150."""
	t = _s(text).upper().replace(",", "")
	if not t:
		return None
	mult = 1
	if t.endswith("M"):
		mult, t = 1_000_000, t[:-1]
	elif t.endswith("K"):
		mult, t = 1_000, t[:-1]
	try:
		return float(t) * mult
	except ValueError:
		return None


def _rows(ws):
	rows = list(ws.iter_rows(values_only=True))
	return rows[0], [r for r in rows[1:] if any(c not in (None, "") for c in r)]


def _gpoa(year, status):
	name = frappe.db.get_value("GPOA", {"year": year}, "name")
	if name:
		return name
	return frappe.get_doc({"doctype": "GPOA", "year": year, "status": status}).insert(ignore_permissions=True).name


def run(path, year=2026, force=0):
	import openpyxl

	year = int(year)
	if frappe.db.exists("GPOA", {"year": year}) and not int(force):
		frappe.throw(f"GPOA {year} already exists. Pass force=1 to add to it anyway.")
	for d in NEW_DEPARTMENTS:
		if not frappe.db.exists("Department Name", d):
			frappe.get_doc({"doctype": "Department Name", "department_name": d}).insert(ignore_permissions=True)

	wb = openpyxl.load_workbook(path, data_only=True)
	this = _gpoa(year, "Approved")
	counts = {}

	# ---- goals: "this / last"
	header, rows = _rows(wb["Goals"])
	prev = None
	n = 0
	for r in rows:
		metric = _s(r[0])
		if metric not in ("Attendance", "PRC", "Baptism", "Finance"):
			continue
		for col, label in enumerate(header):
			dept = GOAL_COLUMNS.get(_s(label))
			if not dept or col >= len(r) or r[col] in (None, ""):
				continue
			parts = [p.strip() for p in _s(r[col]).split("/")]
			targets = [(this, _number(parts[0]))]
			if len(parts) > 1:
				prev = prev or _gpoa(year - 1, "Closed")
				targets.append((prev, _number(parts[1])))
			for gpoa, target in targets:
				if target is None or frappe.db.exists("GPOA Goal", {"gpoa": gpoa, "department": dept, "metric": metric}):
					continue
				frappe.get_doc({"doctype": "GPOA Goal", "gpoa": gpoa, "department": dept, "metric": metric, "target": target}).insert(ignore_permissions=True)
				n += 1
	counts["goals"] = n

	# ---- regular activities
	_, rows = _rows(wb["Regular Activities"])
	n = 0
	for r in rows:
		freq = FREQUENCIES.get(_s(r[0]).lower())
		if not freq or not _s(r[2]):
			continue
		desc = _s(r[2])
		weeks = ""
		m = re.match(r"^\s*((?:\d(?:st|nd|rd|th)?|last)(?:\s*(?:&|and|,)\s*(?:\d(?:st|nd|rd|th)?|last))*)\s*(?:sunday)?\s*,?\s*(.*)$", desc, re.I)
		if m and cal.parse_weeks(m.group(1)):
			weeks = ",".join("last" if w == -1 else str(w) for w in cal.parse_weeks(m.group(1)))
			desc = m.group(2).strip() or desc
		if _s(r[1]).lower() in ("disclipeship", "discipleship") and "disciple" not in desc.lower():
			desc = f"Discipleship {desc}"
		venue = VENUES.get(_s(r[5] if len(r) > 5 else "").lower())
		frappe.get_doc({
			"doctype": "GPOA Regular Activity",
			"gpoa": this,
			"department": _dept(r[1]),
			"description": desc,
			"frequency": freq,
			"weekday": "Sunday",
			"weeks_of_month": weeks,
			"venue": venue,
			"on_calendar": 0 if any(k in desc.lower() for k in NOT_ON_CALENDAR) else 1,
			"budget_per_occurrence": flt(r[3]),
		}).insert(ignore_permissions=True)
		n += 1
	counts["regular"] = n

	# ---- dated activities
	_, rows = _rows(wb["Activities"])
	today = getdate(nowdate())
	n = 0
	for r in rows:
		start = r[0]
		if not isinstance(start, (datetime, date)) or not _s(r[3]):
			continue
		start = getdate(start)
		days = int(flt(r[1]) or 1)
		end = start + timedelta(days=max(days, 1) - 1)
		venue_text = _s(r[5])
		venue = VENUES.get(venue_text.lower())
		title = _s(r[3])
		doc = frappe.get_doc({
			"doctype": "Church Activity",
			"title": title,
			"department": _dept(r[2]),
			"gpoa": this,
			"status": "Done" if end < today else "Confirmed",
			"start_date": start,
			"end_date": end,
			"all_day": 1,
			"venue": venue,
			"location_details": None if venue or venue_text.lower() in UNKNOWN_VENUE else venue_text,
			"service_relation": cal.PART_OF_SERVICE if any(k in title.lower() for k in PART_OF_SERVICE) else cal.SEPARATE,
			"budget": flt(r[4]),
			"transport_needed": 1 if _s(r[6]).upper().startswith("Y") else 0,
			"headcount": int(flt(r[7])) if r[7] not in (None, "") else None,
			"notes": _s(r[8]) or None,
		})
		# Imported as planned last year; conflicts show on the calendar instead.
		doc.flags.skip_conflict_check = True
		doc.insert(ignore_permissions=True)
		n += 1
	counts["activities"] = n

	# ---- budget requests
	_, rows = _rows(wb["Budget Request"])
	n = 0
	for r in rows:
		if not _s(r[1]):
			continue
		area = _s(r[0])
		frappe.get_doc({
			"doctype": "GPOA Budget Request",
			"gpoa": this,
			"department": _dept(area),
			"area": area or None,
			"description": _s(r[1]),
			"amount": flt(r[2]),
			"source_of_fund": "White Gift" if "white gift" in _s(r[3]).lower() else None,
			"priority": 1 if "priority" in _s(r[4] if len(r) > 4 else "").lower() else 0,
		}).insert(ignore_permissions=True)
		n += 1
	counts["requests"] = n

	# ---- special notes
	if "Special Notes" in wb.sheetnames:
		lines = [_s(c) for row in wb["Special Notes"].iter_rows(values_only=True) for c in row if _s(c)]
		if lines:
			frappe.db.set_value("GPOA", this, "notes", "\n".join(f"- {l}" for l in lines))

	frappe.db.commit()
	print(counts)
	return counts
