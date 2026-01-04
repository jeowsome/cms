// Copyright (c) 2023, Jeomar Bayoguina and contributors
// For license information, please see license.txt

frappe.ui.form.on('Disbursement Template', {
	onload: function (frm) {
		if (frm.is_new() && !frm.doc.company) {
			frm.set_value('company', frappe.defaults.get_user_default("Company"));
		}
	},

	refresh: function (frm) {
		frm.trigger('toggle_monthly_tables');
		frm.add_custom_button(__('Generate Disbursement'), function () {
			let d = new frappe.ui.Dialog({
				title: __('Select Months'),
				fields: [
					{
						label: __('Year'),
						fieldname: 'year',
						fieldtype: 'Int',
						default: frappe.datetime.get_today().split('-')[0],
						reqd: 1
					},
					{
						label: __('Months'),
						fieldname: 'months',
						fieldtype: 'MultiCheck',
						sort_options: 0,
						options: [
							{ label: "January", value: "January" },
							{ label: "February", value: "February" },
							{ label: "March", value: "March" },
							{ label: "April", value: "April" },
							{ label: "May", value: "May" },
							{ label: "June", value: "June" },
							{ label: "July", value: "July" },
							{ label: "August", value: "August" },
							{ label: "September", value: "September" },
							{ label: "October", value: "October" },
							{ label: "November", value: "November" },
							{ label: "December", value: "December" }
						],
						columns: 3
					}
				],
				primary_action_label: __('Generate'),
				primary_action(values) {
					if (!values.months || values.months.length === 0) {
						frappe.msgprint(__('Please select at least one month.'));
						return;
					}
					d.hide();
					frappe.confirm(
						__('Are you sure you want to generate disbursements for the selected months?'),
						function () {
							frappe.call({
								method: 'church_management.church_management.doctype.disbursement_template.disbursement_template.generate_disbursements',
								args: {
									template_name: frm.doc.name,
									months: values.months,
									year: values.year
								},
								freeze: true,
								callback: function (r) {
									if (!r.exc) {
										frappe.msgprint(__('Disbursements generated successfully: ' + r.message.join(', ')));
									}
								}
							});
						}
					);
				}
			});
			d.show();
		});
	},

	validate: function (frm) {
		frm.trigger('toggle_monthly_tables');
	},

	toggle_monthly_tables: function (frm) {
		let has_mission = false;
		let has_other_expenses = false;
		let allowed_purposes = [];

		(frm.doc.monthly_disbursement || []).forEach(row => {
			if (row.purpose === "Mission Support") {
				has_mission = true;
			} else if (row.purpose) {
				// Any purpose that is NOT Mission Support should trigger monthly_expenses
				has_other_expenses = true;
				if (!allowed_purposes.includes(row.purpose)) {
					allowed_purposes.push(row.purpose);
				}
			}
		});

		frm.toggle_display("monthly_expenses", has_other_expenses);
		if (!has_other_expenses) {
			frm.clear_table("monthly_expenses");
			frm.refresh_field("monthly_expenses");
		}

		// Filter monthly_expenses purpose based on monthly_disbursement purposes (excluding Mission Support)
		frm.set_query("purpose", "monthly_expenses", function () {
			return {
				filters: [
					["Disbursement Purpose", "name", "in", allowed_purposes],
					["Disbursement Purpose", "active", "=", 1]
				]
			};
		});

		frm.toggle_display("mission_support", has_mission);
		// Note: Not auto-clearing Mission Support as strictly requested only for expenses/allowance previously, 
		// but standard behavior would be to clear if hidden. adhering to specific user instructions to "show/hide".
	},


	monthly_disbursement_add: function (frm, cdt, cdn) {
		frm.trigger('toggle_monthly_tables');
	},

	monthly_disbursement_remove: function (frm, cdt, cdn) {
		frm.trigger('toggle_monthly_tables');
	}
});

frappe.ui.form.on('Monthly Disbursement Item', {
	purpose: function (frm, cdt, cdn) {
		frm.trigger('toggle_monthly_tables');
	}
});
