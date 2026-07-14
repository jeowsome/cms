# Copyright (c) 2026, Jeomar Bayoguina and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


def normalize(name):
    """Canonical form used for duplicate detection: trimmed, lowercased,
    inner whitespace collapsed."""
    return " ".join((name or "").strip().lower().split())


def find_similar(name, exclude=None):
    """Existing purposes that are the same word or a likely misspelling /
    plural of `name` (e.g. contribution / contributions / contributionn)."""
    import difflib

    target = normalize(name)
    if not target:
        return []

    similar = []
    for existing in frappe.get_all("Donation Purpose", pluck="name"):
        if exclude and existing == exclude:
            continue
        candidate = normalize(existing)
        if candidate == target:
            similar.append(existing)
            continue
        # Catches simple plurals both ways.
        if candidate.rstrip("s") == target.rstrip("s"):
            similar.append(existing)
            continue
        if difflib.SequenceMatcher(None, target, candidate).ratio() >= 0.85:
            similar.append(existing)
    return similar


class DonationPurpose(Document):
    def validate(self):
        self.purpose_name = " ".join((self.purpose_name or "").strip().split())
        if not self.purpose_name:
            frappe.throw(_("Purpose name is required."))

        # Hard block on same-word duplicates regardless of case/spacing;
        # `unique` on the column only catches exact matches.
        for existing in frappe.get_all("Donation Purpose", pluck="name"):
            if existing == self.name:
                continue
            if normalize(existing) == normalize(self.purpose_name):
                frappe.throw(
                    _("Purpose {0} already exists as {1}.").format(
                        frappe.bold(self.purpose_name), frappe.bold(existing)
                    )
                )
