import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime
import calendar
from datetime import date, timedelta


class MinistrySchedule(Document):
	def validate(self):
		self.validate_assignment_rows()
		self.validate_assignments()

	def validate_assignment_rows(self):
		"""Every row must have at least a name. Linked members auto-fill name; guests type it in."""
		for row in self.assignments or []:
			if not (row.member_name or "").strip():
				if row.member:
					first = frappe.db.get_value("Church Member", row.member, "firstname") or ""
					last = frappe.db.get_value("Church Member", row.member, "lastname") or ""
					row.member_name = (first + " " + last).strip() or row.member
				else:
					frappe.throw(
						f"Row {row.idx}: please type a Name (or link a Church Member)."
					)

	def _row_identity(self, row):
		"""Stable identity key for a row — use linked member when present, otherwise
		fall back to a normalized name so two chips with the same typed name are treated
		as the same person for conflict detection."""
		if row.member:
			return ("member", row.member)
		return ("name", (row.member_name or "").strip().lower())

	def _row_time_slots(self, row):
		"""Effective service-time set for a row. Two rows only conflict if their
		slot sets overlap.
		- Gate Ushers serves only the morning (no evening posting).
		- Worship Leader respects its service_time field; blank = both services.
		- Everything else is treated as covering both services unless service_time is set.
		"""
		ministry = (row.ministry or "")
		st = (row.service_time or "").lower()
		if ministry == "Gate Ushers":
			return {"morning"}
		if st == "morning":
			return {"morning"}
		if st == "evening":
			return {"evening"}
		return {"morning", "evening"}

	def validate_assignments(self):
		"""Detect conflicts: a person assigned to overlapping ministries on the same date.
		Time-aware so morning-only and evening-only ministries don't false-positive."""
		conflicts = []
		by_date_identity = {}

		for row in self.assignments or []:
			identity = self._row_identity(row)
			if not identity[1]:
				continue
			key = (str(row.sunday_date), identity)
			by_date_identity.setdefault(key, []).append(row)

		for (sched_date, _identity), rows in by_date_identity.items():
			# A pair only counts as a conflict if both rows are unacknowledged,
			# different ministries, and have overlapping time slots.
			has_conflict = False
			for i in range(len(rows)):
				for j in range(i + 1, len(rows)):
					a, b = rows[i], rows[j]
					if a.ministry == b.ministry:
						continue
					if a.conflict_acknowledged or b.conflict_acknowledged:
						continue
					if self._row_time_slots(a) & self._row_time_slots(b):
						has_conflict = True
						break
				if has_conflict:
					break

			if has_conflict:
				ministries = sorted({r.ministry for r in rows if r.ministry})
				display_name = (rows[0].member_name or rows[0].member) or "Unknown"
				conflicts.append(
					f"{display_name} is assigned to {', '.join(ministries)} on {sched_date}"
				)

		if conflicts:
			frappe.msgprint(
				"<b>Scheduling Conflicts Detected:</b><br>" + "<br>".join(conflicts),
				title="Conflicts",
				indicator="orange",
			)

	def _month_num(self):
		if not self.month or not self.year:
			frappe.throw("Please select a month and year first.")
		return [
			"January", "February", "March", "April", "May", "June",
			"July", "August", "September", "October", "November", "December"
		].index(self.month) + 1

	def _populate_weekday(self, child_table, weekday):
		"""Fill `child_table` with every date in the selected month falling on `weekday`
		(Mon=0 … Sun=6). The child rows use the `sunday_date` field as a generic date column."""
		month_num = self._month_num()
		setattr(self, child_table, [])
		cal = calendar.Calendar()
		for d in cal.itermonthdates(int(self.year), month_num):
			if d.weekday() == weekday and d.month == month_num:
				self.append(child_table, {"sunday_date": d.isoformat()})

	@frappe.whitelist()
	def populate_sundays(self):
		"""Auto-populate the sundays child table with all Sundays in the selected month/year."""
		self._populate_weekday("sundays", 6)
		self.save()
		frappe.msgprint(
			f"Populated {len(self.sundays)} Sundays for {self.month} {self.year}.",
			indicator="green",
		)

	@frappe.whitelist()
	def populate_wednesdays(self):
		"""Auto-populate the wednesdays child table with all Wednesdays in the selected month/year."""
		self._populate_weekday("wednesdays", 2)
		self.save()
		frappe.msgprint(
			f"Populated {len(self.wednesdays)} Wednesdays for {self.month} {self.year}.",
			indicator="green",
		)

	@frappe.whitelist()
	def publish(self):
		"""Mark this schedule as Published."""
		if not self.assignments:
			frappe.throw("Cannot publish an empty schedule. Add assignments first.")

		self.status = "Published"
		self.published_on = now_datetime()
		self.save()
		frappe.msgprint(
			f"Ministry schedule for {self.month} {self.year} has been published.",
			indicator="green",
		)

	@frappe.whitelist()
	def unpublish(self):
		"""Revert to Draft."""
		self.status = "Draft"
		self.published_on = None
		self.save()
		frappe.msgprint("Schedule reverted to Draft.", indicator="blue")
