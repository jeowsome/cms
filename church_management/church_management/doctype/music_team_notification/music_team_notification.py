import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class MusicTeamNotification(Document):
	def before_insert(self):
		if not self.sent_at:
			self.sent_at = now_datetime()

	def after_insert(self):
		frappe.publish_realtime(
			"music_team_notification",
			{
				"name": self.name,
				"title": self.title,
				"type": self.notification_type,
				"sunday_date": str(self.sunday_date) if self.sunday_date else None,
				"service_time": self.service_time,
				"body": self.body,
				"sent_at": str(self.sent_at),
			},
			after_commit=True,
		)
