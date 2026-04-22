import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime
import calendar
from datetime import date, timedelta


class MinistrySchedule(Document):
	def validate(self):
		self.validate_assignments()

	def validate_assignments(self):
		"""Detect conflicts: a member assigned to multiple ministries on the same Sunday."""
		conflicts = []
		by_sunday_member = {}

		for row in self.assignments or []:
			key = (str(row.sunday_date), row.member)
			if key not in by_sunday_member:
				by_sunday_member[key] = []
			by_sunday_member[key].append(row.ministry)

		for (sunday_date, member), ministries in by_sunday_member.items():
			if len(ministries) > 1:
				member_name = frappe.db.get_value(
					"Church Member", member, "firstname"
				) or member
				conflicts.append(
					f"{member_name} is assigned to {', '.join(ministries)} on {sunday_date}"
				)

		if conflicts:
			frappe.msgprint(
				"<b>Scheduling Conflicts Detected:</b><br>" + "<br>".join(conflicts),
				title="Conflicts",
				indicator="orange",
			)

	@frappe.whitelist()
	def populate_sundays(self):
		"""Auto-populate the sundays child table with all Sundays in the selected month/year."""
		if not self.month or not self.year:
			frappe.throw("Please select a month and year first.")

		month_num = [
			"January", "February", "March", "April", "May", "June",
			"July", "August", "September", "October", "November", "December"
		].index(self.month) + 1

		self.sundays = []
		cal = calendar.Calendar()
		for d in cal.itermonthdates(int(self.year), month_num):
			if d.weekday() == 6 and d.month == month_num:  # Sunday = 6
				self.append("sundays", {
					"sunday_date": d.isoformat(),
				})

		self.save()
		frappe.msgprint(
			f"Populated {len(self.sundays)} Sundays for {self.month} {self.year}.",
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
