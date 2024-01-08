# Copyright (c) 2024, Jeomar Bayoguina and contributors
# For license information, please see license.txt

import frappe
from frappe.website.website_generator import WebsiteGenerator
from frappe.model.document import Document
import json

TAGS = {"PYP": "Young People - Pasig"}
STATUS_ICONS = {"Upcoming": "🔜", "Done": "✔️ ", "Cancelled": "❌ ", "Moved": "⏩ "}


class ChurchEvents(Document):
    def update_status(self):
        self.color = (
            "#ffff00"
            if self.status == "Done"
            else "#adadad"
            if self.status == "Moved"
            else "#ff0000"
            if self.status == "Cancelled"
            else "#00ff26"
        )

    def validate(self):
        self.update_status()


@frappe.whitelist()
def get_events(filters=None):
    docs = get_church_events(json.loads(filters))

    for doc in docs:
        doc["subject"] = update_event_description(doc)
    return docs


def parse_filter(filters):
    tags = []
    assigned = None
    if len(filters):
        for f in filters:
            if f[1] == "_user_tags":
                tags.append(f[3].replace("%", ""))
            if not assigned and f[1] == "_assign":
                assigned = f[3].replace("%", "")
    return {"tags": set(tags), "assigned": assigned}


def update_event_description(doc):
    added_icons = []
    if doc.get("van_req"):
        added_icons.append("🚚")
    if doc.get("to_announce"):
        added_icons.append("🔔")
    if doc.get("budget"):
        added_icons.append(
            f'{frappe.utils.fmt_money(doc.get("budget"), currency="PHP")}'
        )
    return f"{STATUS_ICONS.get(doc.get('status'))}{doc.get('event_name').title()}\n{' '.join(added_icons)}"


def get_church_events(filters=None):
    docs = frappe.db.get_list(
        "Church Events",
        fields=[
            "name",
            "event_name",
            "budget",
            "van_req",
            "to_announce",
            "status",
            "event_date",
            "until",
            "color",
        ],
    )
    if len(filters):
        filtered_data = []
        _f = parse_filter(filters=filters)
        for doc in docs:
            _doc = frappe.get_doc("Church Events", doc.get("name"))
            if _f.get("assigned") in _doc.get_assigned_users() or bool(
                set(_doc.get_tags()) & _f.get("tags")
            ):
                filtered_data.append(_doc.as_dict())
        return filtered_data

    return docs
