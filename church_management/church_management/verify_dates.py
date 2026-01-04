
import frappe
from church_management.church_management.doctype.disbursement.disbursement import get_weeks_in_month

def run():
    print("Testing January 2026:")
    weeks = get_weeks_in_month("January", 2026)
    for w in weeks:
        print(f"Index: {w.get('index')}, Label: {w.get('label')}")
