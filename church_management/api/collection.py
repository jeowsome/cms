import frappe
from frappe import _


@frappe.whitelist()
def get_list(year=None, month=None):
    """Get list of collections with summary totals."""
    filters = {}
    if year:
        filters["posting_date"] = ["between", [f"{year}-01-01", f"{year}-12-31"]]
    if month:
        filters["month"] = month

    collections = frappe.get_all(
        "Collection",
        filters=filters,
        fields=[
            "name",
            "posting_date",
            "service_type",
            "docstatus",
            "total_tithes",
            "total_offering",
            "total_mission",
            "grand_total",
            "creation",
        ],
        order_by="posting_date desc",
    )

    return collections


@frappe.whitelist()
def get_detail(name):
    """Get full collection document."""
    frappe.has_permission("Collection", doc=name, throw=True)
    doc = frappe.get_doc("Collection", name)
    return doc.as_dict()


@frappe.whitelist()
def get_ytd_summary(year=None):
    """Get year-to-date collection summary by category."""
    if not year:
        year = frappe.utils.now_datetime().year

    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"

    collections = frappe.get_all(
        "Collection",
        filters={
            "posting_date": ["between", [start_date, end_date]],
            "docstatus": 1,
        },
        fields=[
            "total_tithes",
            "total_offering",
            "total_mission",
            "grand_total",
        ],
    )

    summary = {
        "tithes": sum(c.total_tithes or 0 for c in collections),
        "offering": sum(c.total_offering or 0 for c in collections),
        "mission": sum(c.total_mission or 0 for c in collections),
        "grand_total": sum(c.grand_total or 0 for c in collections),
        "count": len(collections),
        "year": year,
    }

    return summary
