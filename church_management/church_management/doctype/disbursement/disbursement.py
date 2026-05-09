# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class Disbursement(Document):
	def autoname(self):
		self.name = f"{self.get('month_recorded')}-{self.get('year_recorded')}"

	def validate(self):
		self._enforce_active_weeks()

		total = 0
		count = 0

		# Define all table fields
		tables = [
			"monthly_disbursement_items",
			"monthly_expense_items"
		]

		# Add weekly tables
		for i in range(1, 6):
			tables.append(f"disbursement_item_week_{i}")
			tables.append(f"expense_item_week_{i}")
		
		# Date Validation Setup
		import calendar
		from frappe.utils import getdate, get_last_day
		
		month_map = {name: i for i, name in enumerate(calendar.month_name) if name}
		month_idx = month_map.get(self.month_recorded)
		
		month_start = None
		month_end = None
		
		if month_idx and self.year_recorded:
			# Create strictly date objects for comparison
			month_start = getdate(f"{self.year_recorded}-{month_idx:02d}-01")
			month_end = getdate(get_last_day(month_start))

		# Calculate Totals and Validate Dates
		for table_field in tables:
			for item in self.get(table_field) or []:
				total += item.amount
				count += 1
				
				# Year-based Date Validation
				if self.year_recorded and item.get("received_date"):
					r_date = getdate(item.received_date)
					# Allow any date within the same year
					if r_date.year != int(self.year_recorded):
						frappe.throw(
							f"Row #{item.idx} in {frappe.get_meta(self.doctype).get_label(table_field)} has a Received Date ({item.received_date}) "
							f"outside the recorded year ({self.year_recorded})."
						)
		
		self.total_amount_disbursed = total
		self.total_disbursed = count

	def _enforce_active_weeks(self):
		"""Strip rows from week tabs that don't exist in this month.

		A month has 4 or 5 Sundays. If there are only 4 Sundays, week_5 child
		tables must be empty — orphan rows there are invisible in the UI and
		corrupt unclaimed counts. We drop unclaimed orphans automatically and
		refuse to save if any are already claimed (so the user can investigate).
		"""
		import calendar
		import datetime

		month_map = {name: i for i, name in enumerate(calendar.month_name) if name}
		month_idx = month_map.get(self.month_recorded)
		if not month_idx or not self.year_recorded:
			return

		year = int(self.year_recorded)
		days = calendar.monthrange(year, month_idx)[1]
		sundays = sum(
			1 for d in range(1, days + 1)
			if datetime.date(year, month_idx, d).weekday() == 6
		)
		active_weeks = min(sundays, 5)

		for week_num in range(active_weeks + 1, 6):
			for field in (f"disbursement_item_week_{week_num}", f"expense_item_week_{week_num}"):
				rows = self.get(field) or []
				if not rows:
					continue
				claimed_orphans = [
					r for r in rows
					if (r.get("status") == "Claimed") or (r.get("received_by") and r.get("received_date"))
				]
				if claimed_orphans:
					frappe.throw(
						f"{self.month_recorded} {self.year_recorded} only has {sundays} Sundays, "
						f"but {field} contains {len(claimed_orphans)} claimed row(s). "
						f"Move or unclaim them before saving."
					)
				# Drop unclaimed orphan rows silently.
				self.set(field, [])

	def on_submit(self):
		# TODO: Implement Journal Entry creation for new schema
		pass

	def make_journal_entry(self):
		pass

@frappe.whitelist()
def get_weeks_in_month(month, year):
	import calendar
	from datetime import date, timedelta

	month_map = {name: i for i, name in enumerate(calendar.month_name) if name}
	month_idx = month_map.get(month)
	
	if not month_idx or not year:
		return 0 # Or empty list

	year = int(year)
	
	month_start = date(year, month_idx, 1)
	if month_idx == 12:
		next_month = date(year + 1, 1, 1)
	else:
		next_month = date(year, month_idx + 1, 1)

	current_date = month_start
	sundays = []
	
	while current_date < next_month:
		if current_date.weekday() == 6: # Sunday
			sundays.append(current_date)
		current_date += timedelta(days=1)
		
	weeks = []
	for i, sunday in enumerate(sundays):
		weeks.append({
			"index": i + 1,
			"label": f"Week {i + 1}: {sunday.strftime('%B')} {sunday.day}, Sunday"
		})
		
		# Cap at 5 weeks as per schema
		if len(weeks) == 5:
			break
			
	return weeks

