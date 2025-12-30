frappe.query_reports["Disbursement Summary Tree"] = {
    "tree": true,
    "name_field": "description",
    "parent_field": "parent",
    "initial_depth": 1,
    "filters": [
        {
            "fieldname": "year",
            "label": __("Year"),
            "fieldtype": "Int",
            "default": new Date().getFullYear(),
            "width": 60
        },
        {
            "fieldname": "month",
            "label": __("Month"),
            "fieldtype": "Select",
            "options": [
                "",
                "January",
                "February",
                "March",
                "April",
                "May",
                "June",
                "July",
                "August",
                "September",
                "October",
                "November",
                "December"
            ],
            "width": 100
        },
        {
            "fieldname": "purpose",
            "label": __("Purpose"),
            "fieldtype": "Select",
            "options": [
                "",
                "Allowance",
                "Regular Activity",
                "Transportation",
                "Mission Support",
                "Rent",
                "Unplanned",
                "Digital",
                "Maintenance",
                "Government",
                "Special Event",
                "Benevolence"
            ],
            "width": 150
        },
        {
            "fieldname": "department",
            "label": __("Department"),
            "fieldtype": "Data",
            "width": 150
        }
    ]
};
