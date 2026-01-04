# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class Disbursement(Document):
	def autoname(self):
		self.name = f"{self.get('month_recorded')}-{self.get('year_recorded')}"

	def validate(self):
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
				
				# Strict Date Validation
				if month_start and month_end and item.get("received_date"):
					r_date = getdate(item.received_date)
					if r_date < month_start or r_date > month_end:
						frappe.throw(
							f"Row #{item.idx} in {frappe.get_meta(self.doctype).get_label(table_field)} has a Received Date ({item.received_date}) "
							f"outside the recorded month ({self.month_recorded} {self.year_recorded})."
						)
		
		self.total_amount_disbursed = total
		self.total_disbursed = count

	def on_submit(self):
		# TODO: Implement Journal Entry creation for new schema
		pass

	def make_journal_entry(self):
		pass

@frappe.whitelist()
def get_weeks_in_month(month, year):
	import calendar
	from frappe.utils import getdate, formatdate
	from datetime import date, timedelta

	month_map = {name: i for i, name in enumerate(calendar.month_name) if name}
	month_idx = month_map.get(month)
	
	if not month_idx or not year:
		return 0 # Or empty list

	year = int(year)
	# Use Sunday as first day of week (6) so weeks align nicely (e.g. Feb 1 Sun is start of week)
	c = calendar.Calendar(firstweekday=calendar.SUNDAY)
	month_days = c.monthdatescalendar(year, month_idx)
	
	weeks = []
	for i, week in enumerate(month_days):
		# With Sunday start, the first day (index 0) is Sunday
		sunday_date = week[0]
		
		# Clamp date to start of month if Sunday is in previous month
		# This ensures labels like "Week 1: January 1" instead of "December 28"
		month_start = date(year, month_idx, 1)
		display_date = sunday_date
		if sunday_date < month_start:
			display_date = month_start
			
		weeks.append({
			"index": i + 1,
			"label": f"Week {i + 1}: {display_date.strftime('%B %-d, %Y')}"
		})
		
		# Cap at 5 weeks as per schema
		if len(weeks) == 5:
			break
			
	return weeks

