# Copyright (c) 2026, Jeomar Bayoguina and contributors
# For license information, please see license.txt
"""One dated entry on the church calendar: a GPOA activity, or a date
generated from a GPOA Regular Activity.

Rules (see church_management/church_calendar.py):
- an on-premises venue holds one activity at a time;
- an activity may not overlap a worship service unless it is part of the
  service, or replaces it with the pastor's approval.
"""
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from church_management.church_management import church_calendar as cal

# Changing any of these re-runs the conflict check.
SCHEDULE_FIELDS = (
	"start_date", "end_date", "all_day", "start_time", "end_time",
	"venue", "service_relation", "status",
)
TIME_FIELDS = ("start_date", "end_date", "all_day", "start_time", "end_time")


class ChurchActivity(Document):
	def validate(self):
		self.normalise_dates()
		self.set_gpoa()
		self.guard_approval()
		if self.regular_activity and not self.is_new() and not self.flags.from_generator:
			if any(self.has_value_changed(f) for f in SCHEDULE_FIELDS + ("title", "budget")):
				self.manually_edited = 1
		if self.flags.skip_conflict_check:
			return
		if self.is_new() or any(self.has_value_changed(f) for f in SCHEDULE_FIELDS):
			self.check_conflicts()

	def normalise_dates(self):
		if not self.end_date:
			self.end_date = self.start_date
		if getdate(self.end_date) < getdate(self.start_date):
			frappe.throw(_("End date cannot be before the start date."))
		if self.all_day:
			self.start_time = None
			self.end_time = None
		else:
			if not (self.start_time and self.end_time):
				frappe.throw(_("Set a start and end time, or mark the activity as all day."))
			start, end = cal.interval(self)
			if end <= start:
				frappe.throw(_("The end time must be after the start time."))

	def set_gpoa(self):
		if not self.gpoa and self.start_date:
			self.gpoa = frappe.db.get_value("GPOA", {"year": getdate(self.start_date).year}, "name")

	def guard_approval(self):
		"""Only the pastor (through api.church_calendar.decide_service_replacement)
		may approve or decline replacing a worship service."""
		if self.flags.pastor_decision:
			return
		before = None if self.is_new() else self.get_doc_before_save()
		old = before.pastor_approval if before else None
		if self.pastor_approval in ("Approved", "Declined") and self.pastor_approval != old:
			frappe.throw(_("Only the pastor can approve or decline replacing a worship service."))
		# Moving an approved activity to another date or time needs a fresh decision.
		if (
			before
			and old in ("Approved", "Declined")
			and any(self.has_value_changed(f) for f in TIME_FIELDS)
		):
			self.pastor_approval = "Requested"
			self.approved_by = None
			self.approved_on = None
			if self.status == "Confirmed":
				self.status = "Proposed"
				frappe.msgprint(_("The date or time changed, so the pastor's approval was asked again and the activity is back to Proposed."))

	def check_conflicts(self):
		if self.status not in cal.ACTIVE_STATUSES:
			return
		found = cal.check(self)
		venue = [c["message"] for c in found if c["kind"] == "venue"]
		if venue:
			frappe.throw("<br>".join(venue), title=_("Venue already taken"))
		services = [c["message"] for c in found if c["kind"] == "service"]
		relation = self.service_relation or cal.SEPARATE
		if relation == cal.SEPARATE and services:
			frappe.throw(
				"<br>".join(services)
				+ "<br><br>"
				+ _("Change the date or time, mark it as part of the worship service, or ask the pastor to let it replace the service."),
				title=_("Overlaps a worship service"),
			)
		if relation == cal.REPLACES:
			if not services:
				frappe.throw(_("This activity does not overlap any worship service, so it cannot replace one."))
			if self.pastor_approval not in ("Approved", "Declined"):
				self.pastor_approval = "Requested"
			if self.status == "Confirmed" and self.pastor_approval != "Approved":
				frappe.throw(_("Replacing a worship service needs the pastor's approval before the activity can be confirmed."))
		elif self.pastor_approval:
			self.pastor_approval = None
			self.approved_by = None
			self.approved_on = None
