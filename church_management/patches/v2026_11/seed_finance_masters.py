"""Masters for the finance upgrades. Safe to run twice: every step checks
the current value first and never overwrites a value someone has set since.

- departments the disbursement lines use
- purposes Student Allowance and White Gift Project (Miscellaneous and
  Unplanned stay active, as agreed)
- first creditor: Christian Bible Heritage Learning Center
- each worker's default disbursement department / purpose
- the 2026 template: department per recurring expense (Cainta Rent ->
  Cainta General; ministry fellowships back to their ministries for new
  months) and purposes (SEC fee -> Professional Fees, student support ->
  Student Allowance)
"""
import frappe

from church_management.patches.v2026_11.backfill_2026_lines import load_people

DEPARTMENTS = [
	"Pasig General", "Cainta General", "Mission", "Pasig Sunday School", "Pasig Young People",
	"Pasig ColSPro", "Pasig Ladies", "Pasig Music Team", "Pasig SocMed",
]
PURPOSES = ["Student Allowance", "White Gift Project"]
CREDITORS = ["Christian Bible Heritage Learning Center"]

# Worker names (Cainta workers, missionaries, love-gift payees, student
# support lines) come from people_2026.json, kept off git: see load_people().

# (description match, field, wrong value or None for "any", right value)
TEMPLATE_FIXES = [
	("Cainta Rent", "department", "Pasig General", "Cainta General"),
	("Sunday School Miryenda", "department", "Pasig General", "Pasig Sunday School"),
	("YP Regular Fellowship", "department", "Pasig General", "Pasig Young People"),
	("ColSPro Regular Fellowship", "department", "Pasig General", "Pasig ColSPro"),
	("SEC Accountant", "purpose", "Government", "Professional Fees"),
]


def execute():
	for d in DEPARTMENTS:
		if not frappe.db.exists("Department Name", d):
			frappe.get_doc({"doctype": "Department Name", "department_name": d}).insert(ignore_permissions=True)
	company = frappe.db.get_single_value("Global Defaults", "default_company") or frappe.db.get_value("Company", {}, "name")
	for p in PURPOSES:
		if not frappe.db.exists("Disbursement Purpose", p):
			frappe.get_doc({"doctype": "Disbursement Purpose", "purpose": p, "active": 1, "company": company}).insert(ignore_permissions=True)
	for c in CREDITORS:
		if not frappe.db.exists("Creditor", c):
			frappe.get_doc({"doctype": "Creditor", "creditor_name": c, "active": 1}).insert(ignore_permissions=True)

	people = load_people()
	if people is None:
		print("  people_2026.json not found: worker defaults and student-support template fixes skipped")
	_worker_defaults(people)
	_template_fixes(people)


def _set_worker(name, dept=None, purpose=None):
	if not frappe.db.exists("Church Worker", name):
		return
	cur = frappe.db.get_value("Church Worker", name, ["disbursement_department", "default_purpose"], as_dict=True)
	vals = {}
	if dept and not cur.disbursement_department:
		vals["disbursement_department"] = dept
	if purpose and not cur.default_purpose:
		vals["default_purpose"] = purpose
	if vals:
		frappe.db.set_value("Church Worker", name, vals)


def _worker_defaults(people):
	if people is None:
		return
	cainta, missionaries = people["cainta_workers"], people["missionaries"]
	allowance_workers = set(frappe.get_all("Weekly Allowance Item", pluck="worker"))
	for w in allowance_workers:
		if w and w not in cainta and w not in missionaries:
			_set_worker(w, "Pasig General")
	for w in cainta:
		_set_worker(w, "Cainta General")
	for w in missionaries:
		_set_worker(w, "Mission")
	for w in people["love_gift_payees"]:
		_set_worker(w, "Pasig General", "Love Gift")


def _template_fixes(people):
	fixes = list(TEMPLATE_FIXES)
	for desc in (people or {}).get("student_support_templates", []):
		fixes.append((desc, "purpose", "Allowance", "Student Allowance"))
	for name in frappe.get_all("Disbursement Template", pluck="name"):
		doc = frappe.get_doc("Disbursement Template", name)
		changed = False
		for table in ("monthly_expenses", "weekly_activity", "monthly_disbursement"):
			for row in doc.get(table) or []:
				desc = (row.get("description") or "").strip().lower()
				for match, field, wrong, right in fixes:
					if desc.startswith(match.lower()) and field in row.as_dict() and row.get(field) in (wrong, None, ""):
						if row.get(field) != right:
							row.set(field, right)
							changed = True
		if changed:
			doc.save(ignore_permissions=True)
			print(f"Template {name} updated")
