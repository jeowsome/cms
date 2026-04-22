# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ChurchMember(Document):
	def validate(self):
		self.validate_music_role_preference()

	def validate_music_role_preference(self):
		music_tags = {r.music_team_tag for r in (self.music_team_tag or [])}

		seen = set()
		for row in (self.music_role_preference or []):
			if row.music_team_tag in seen:
				frappe.throw(f"Duplicate Music Team Tag '{row.music_team_tag}' in Music Role Preference.")
			seen.add(row.music_team_tag)

			if row.music_team_tag not in music_tags:
				frappe.throw(
					f"Music Team Tag '{row.music_team_tag}' in Music Role Preference "
					"is not in the member's Music Team Tags."
				)
