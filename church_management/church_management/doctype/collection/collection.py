# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from operator import itemgetter
from frappe.utils import flt

class Collection(Document):

	def autoname(self):
		date = self.date.split(' ')
		self.name = str(date[0]) + ' MORNING' if int(str(date[1])[0:2]) <= 12 else str(date[0]) + ' EVENING'

	def compute_total(self, table):
		cash_total = 0
		cls_total = 0
		count = 0
		c_count = 0

		for i in self.get(table):
			if i.account_type in ('GCash', 'Bank'):
				cls_total += i.amount
				c_count += 1
			elif i.account_type == 'Cash':
				cash_total += i.amount
				count += 1

		return {
			'cash': cash_total,
			'cls': cls_total,
			'cash_count': count,
			'cls_count': c_count
		}

	def compute_tally_total(self):
		total = 0
		coins_total = 0
		for i in self.get('collection_tally'):
			total += i.total
			if i.denum_name in ('20', '10', '5', '1', '0.25'):
				if i.denum_name == '20':
					coins_total += flt(i.denomination *  i.quantity_coins)
					continue
				coins_total += flt(i.denomination *  i.quantity)

		return {
			'tally_total': total,
			'coins_total': coins_total
		}

	def validate(self):
		tithes = self.compute_total('tithes_collection')
		offering = self.compute_total('offering_collection')
		mission = self.compute_total('mission_collection')

		self.tithes_total = tithes.get('cash')
		self.tithes_total_cls = tithes.get('cls')
		self.no_of_tithes = tithes.get('cash_count')
		self.no_of_tithes_cls = tithes.get('cls_count')

		self.mission_total = mission.get('cash')
		self.mission_total_cls = mission.get('cls')
		self.no_of_mission = mission.get('cash_count')
		self.no_of_mission_cls = mission.get('cls_count')

		self.offering_total = offering.get('cash')
		self.offering_total_cls = offering.get('cls')
		self.no_of_offering = offering.get('cash_count')
		self.no_of_offering_cls = offering.get('cls_count')

		tally_total = self.compute_tally_total()

		self.tally_total = tally_total.get('tally_total')
		self.coins_total = tally_total.get('coins_total')

		self.grand_total = sum((self.tithes_total or 0,
								self.mission_total or 0,
								self.offering_total or 0,
								self.benevolence_collection or 0,
								self.loose_collection or 0,
								self.sunday_school_collection or 0
								))

		self.grand_total_cls = sum((self.tithes_total_cls or 0,
								self.mission_total_cls or 0,
								self.offering_total_cls or 0,
								self.benevolence_collection_cls or 0,
								self.loose_collection_cls or 0,
								))

		self.all_benevolence_total = self.benevolence_collection_cls + self.benevolence_collection
		self.all_loose_total = self.loose_collection_cls + self.loose_collection
		self.all_grand_total = self.grand_total_cls + self.grand_total
		self.all_tithes_total = self.tithes_total + self.tithes_total_cls
		self.all_offering_total = self.offering_total + self.offering_total_cls
		self.all_mission_total = self.mission_total + self.mission_total_cls
		self.cash_grand_total_difference = self.tally_total - self.grand_total


@frappe.whitelist()
def number_sorter(collection):
	return sorted([{'order': int(num['number'][0:-1]) + .1 if num['number'][-1].isalpha() else int(num['number']), 'number': num['number'], 'amount': num['amount']} for num in [collect for collect in collection]], key=itemgetter('order'))


@frappe.whitelist()
def sort_denomination(denomination_list):
	return sorted([{'order': int(item['denomination']), 'denomination': item['denomination'], 'quantity': item['quantity'], 'total': item['total']} for item in [denomination for denomination in denomination_list]], key=itemgetter('order'), reverse=True)