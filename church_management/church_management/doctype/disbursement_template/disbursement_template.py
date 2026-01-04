import frappe
from frappe.model.document import Document
import calendar

class DisbursementTemplate(Document):
	pass

@frappe.whitelist()
def generate_disbursements(template_name, months, year):
	template = frappe.get_doc("Disbursement Template", template_name)
	year = int(year)
	months = frappe.parse_json(months)
	
	generated_docs = []

	# specialized mapping for purposes to accounts
	purpose_map = {}
	purposes = frappe.get_all("Disbursement Purpose", fields=["purpose", "default_account"])
	for p in purposes:
		purpose_map[p.purpose] = p.default_account

	month_map = {
		"January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
		"July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12
	}

	for month_name in months:
		month_idx = month_map.get(month_name)
		if not month_idx: continue

		# Calculate weeks using Sunday as start to match UI logic
		cal = calendar.Calendar(firstweekday=calendar.SUNDAY)
		month_weeks = cal.monthdayscalendar(year, month_idx)
		num_weeks = len(month_weeks) 
		if num_weeks > 5: num_weeks = 5 # Cap at 5 weeks as per schema

		doc = frappe.new_doc("Disbursement")
		doc.disbursement_template = template_name
		doc.company = template.company
		doc.month_recorded = month_name
		doc.year_recorded = year
		
		# Helper to add item to week or monthly tab
		def add_to_week(target, source_row, source_type="Descriptive"):
			# target can be week_num (int) or "Monthly" (str)
			
			table_field = ""
			is_monthly = False
			
			if target == "Monthly":
				is_monthly = True
				if source_type in ["Descriptive", "Worker"]:
					table_field = "monthly_disbursement_items"
				elif source_type == "Expense":
					table_field = "monthly_expense_items"
			else:
				# Weekly target
				week_num = target
				if week_num > 5: return
				
				if source_type in ["Descriptive", "Worker"]:
					table_field = f"disbursement_item_week_{week_num}"
				elif source_type == "Expense":
					table_field = f"expense_item_week_{week_num}"

			if not table_field: return

			row = doc.append(table_field, {})
			
			# Map fields
			if source_type == "Descriptive": 
				# Handling 'Monthly Disbursement' which usually has default_receiver
				row.worker = source_row.default_receiver if hasattr(source_row, 'default_receiver') else None
				row.amount = source_row.amount
				row.remarks = source_row.description or source_row.purpose
				row.purpose = source_row.purpose
				# Priority 1: Explicit Source in Template
				if hasattr(source_row, 'source') and source_row.source:
					row.source = source_row.source
				# Priority 2: Map from Purpose
				elif source_row.purpose and source_row.purpose in purpose_map:
					row.source = purpose_map[source_row.purpose]
			
			elif source_type == "Worker":
				# Handling 'Mission Support' and 'Weekly Allowances'
				row.worker = source_row.worker
				row.amount = source_row.amount
				row.received_by = source_row.default_receiver if hasattr(source_row, 'default_receiver') else None
				row.remarks = source_row.description or source_row.purpose
				row.purpose = source_row.purpose
				# Priority 1: Explicit Source in Template
				if hasattr(source_row, 'source') and source_row.source:
					row.source = source_row.source
				# Priority 2: Map from Purpose
				elif source_row.purpose and source_row.purpose in purpose_map:
					row.source = purpose_map[source_row.purpose]

			elif source_type == "Expense":
				# Handling 'Weekly Activity' and 'Monthly Expenses'
				row.description = source_row.description or source_row.purpose
				row.amount = source_row.amount
				row.department = source_row.department if hasattr(source_row, 'department') else None
				row.received_by = source_row.default_receiver if hasattr(source_row, 'default_receiver') else None
				row.remarks = source_row.description
				row.purpose = source_row.purpose
				# Priority 1: Explicit Source in Template
				if hasattr(source_row, 'source') and source_row.source:
					row.source = source_row.source
				# Priority 2: Map from Purpose
				elif source_row.purpose and source_row.purpose in purpose_map:
					row.source = purpose_map[source_row.purpose]

		# Distribute Items
		
		# 1. Monthly Items (Monthly Tab)
		# Worker Focused
		# User requested to NOT map monthly_disbursement to monthly_disbursement_items (Step 909)
		# only mission_support populates it.
			
		for item in (template.mission_support or []):
			add_to_week("Monthly", item, "Worker")

		# Expense Focused
		for item in (template.monthly_expenses or []):
			add_to_week("Monthly", item, "Expense")


		# 2. Weekly Items (All Weeks)
		for w in range(1, num_weeks + 1):
			# Worker Focused
			for item in (template.weekly_allowances or []):
				add_to_week(w, item, "Worker")
				
			# Expense Focused
			for item in (template.weekly_activity or []):
				add_to_week(w, item, "Expense")

		doc.save()
		generated_docs.append(doc.name)

	return generated_docs
