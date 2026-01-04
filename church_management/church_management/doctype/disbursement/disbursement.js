// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Disbursement', {
	setup(frm) {
		if (frm.is_new()) {
			let [year, month, date] = frappe.datetime.now_date().split("-")
			frm.set_value({
				year_recorded: year,
				month_recorded: moment(month, 'M').format('MMMM')
			}).then(() => frm.refresh_fields())
		}
	},

	refresh(frm) {
		frm.trigger('toggle_weeks');
	},

	month_recorded(frm) {
		frm.trigger('toggle_weeks');
	},

	year_recorded(frm) {
		frm.trigger('toggle_weeks');
	},

	toggle_weeks(frm) {
		const { month_recorded, year_recorded } = frm.doc;
		if (month_recorded && year_recorded) {
			frappe.call({
				method: 'church_management.church_management.doctype.disbursement.disbursement.get_weeks_in_month',
				args: {
					month: month_recorded,
					year: year_recorded
				},
				callback: function (r) {
					if (r.message) {
						const weeks_data = r.message;
						const count = weeks_data.length;

						// Debugging: Verify we got data
						// frappe.show_alert(`Loaded ${count} weeks. Label 1: ${weeks_data[0].label}`);

						// Define sections and fields for each week index (0-based)
						const sections = [
							{ sec: 'week_1_section', fields: ['week_1_section', 'disbursement_item_week_1', 'expense_item_week_1'] },
							{ sec: 'week_2_section', fields: ['week_2_section', 'disbursement_item_week_2', 'expense_item_week_2'] },
							{ sec: 'week_3_section', fields: ['week_3_section', 'disbursement_item_week_3', 'expense_item_week_3'] },
							{ sec: 'week_4_section', fields: ['week_4_section', 'disbursement_item_week_4', 'expense_item_week_4'] },
							{ sec: 'week_5_section', fields: ['week_5_section', 'disbursement_item_week_5', 'expense_item_week_5'] }
						];

						// Logic to toggle visibility
						sections.forEach((s, i) => {
							const exists = i < count;
							frm.toggle_display(s.fields, exists);
						});

						// Update labels directly in DOM to bypass any refresh issues
						setTimeout(() => {
							sections.forEach((s, i) => {
								if (i < count) {
									const label = weeks_data[i].label;

									// 1. Try standard property update (updates internal model)
									frm.set_df_property(s.sec, 'label', label);

									// 2. Direct DOM update (robust)
									const $section = frm.$wrapper.find(`[data-fieldname="${s.sec}"]`);

									if ($section.length) {
										const $head = $section.find('.section-head');
										// Replace only the text text node, preserving the collapse indicator span
										$head.contents().filter(function () {
											return this.nodeType === 3; // Text node
										}).first().replaceWith(label);
									}
								}
							});
						}, 100);
					}
				}
			});
		}
	}
});


frappe.ui.form.on('Disbursement Week Item', {
	purpose(frm, cdt, cdn) {
		let row = frappe.get_doc(cdt, cdn);

		if (row.purpose !== 'Regular Activity') {
			row.activity_type = ''
		}
	},

	claim_btn(frm, cdt, cdn) {
		let row = frappe.get_doc(cdt, cdn);
		if (row.status === 'Claimed') {
			frappe.msgprint(__('This item is already claimed.'));
			return;
		}

		let d = new frappe.ui.Dialog({
			title: __('Claim Disbursement'),
			fields: [
				{
					label: __('Worker'),
					fieldname: 'worker',
					fieldtype: 'Link',
					options: 'Church Worker',
					default: row.worker,
					read_only: 1
				},
				{
					label: __('Amount'),
					fieldname: 'amount',
					fieldtype: 'Currency',
					default: row.amount,
					read_only: 1
				},
				{
					label: __('Received By'),
					fieldname: 'received_by',
					fieldtype: 'Link',
					options: 'Church Worker',
					reqd: 1,
					default: row.received_by || row.worker // Default to existing or worker
				},
				{
					label: __('Received Date'),
					fieldname: 'received_date',
					fieldtype: 'Date',
					reqd: 1,
					default: frappe.datetime.get_today()
				}
			],
			primary_action_label: __('Confirm Claim'),
			primary_action(values) {
				frappe.model.set_value(cdt, cdn, 'received_by', values.received_by);
				frappe.model.set_value(cdt, cdn, 'received_date', values.received_date);
				frappe.model.set_value(cdt, cdn, 'status', 'Claimed');

				d.hide();

				// Refresh the specific row/grid if needed, but model set_value usually handles it
				// Maybe force refresh the layout?
				// Since we are changing status, the button visibility might change if we used depends_on
			}
		});

		d.show();
	}
});

frappe.ui.form.on('Disbursement Week Expense Item', {
	claim_btn(frm, cdt, cdn) {
		let row = frappe.get_doc(cdt, cdn);
		if (row.status === 'Claimed') {
			frappe.msgprint(__('This item is already claimed.'));
			return;
		}

		let d = new frappe.ui.Dialog({
			title: __('Claim Expense'),
			fields: [
				{
					label: __('Description'),
					fieldname: 'description',
					fieldtype: 'Data',
					default: row.description,
					read_only: 1
				},
				{
					label: __('Amount'),
					fieldname: 'amount',
					fieldtype: 'Currency',
					default: row.amount,
					read_only: 1
				},
				{
					label: __('Received By'),
					fieldname: 'received_by',
					fieldtype: 'Link',
					options: 'Church Worker',
					reqd: 1,
					default: row.received_by
				},
				{
					label: __('Received Date'),
					fieldname: 'received_date',
					fieldtype: 'Date',
					reqd: 1,
					default: frappe.datetime.get_today()
				}
			],
			primary_action_label: __('Confirm Claim'),
			primary_action(values) {
				frappe.model.set_value(cdt, cdn, 'received_by', values.received_by);
				frappe.model.set_value(cdt, cdn, 'received_date', values.received_date);
				frappe.model.set_value(cdt, cdn, 'status', 'Claimed');

				d.hide();
			}
		});

		d.show();
	}
});
