// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

function checkMonthYearWeek(frm) {
	const {week_recorded, year_recorded, month_recorded, __unsaved, __islocal} = frm.doc

	if (week_recorded && year_recorded && month_recorded && (!__unsaved && __islocal)) {
		frm.call('validate_ymw').then(e => {
			let {exists} = e.message
			if (exists) {
				frappe.msgprint(__(`Disbursement with same month year and week already exists`));
			}
		})
	}
	
}

frappe.ui.form.on('Disbursement', {
	setup(frm) {
		let [year, month, date] = frappe.datetime.now_date().split("-")
		frm.set_value({
			year_recorded: year,
			month_recorded: moment(month, 'M').format('MMMM')
		}).then(() => frm.refresh_fields())
	},

	disbursement_template: (frm) => {
		if (frm.doc.disbursed && frm.doc.disbursed.length) {
			frappe.confirm("Are you sure you want to change Disbursement Template?", 
			() => {
				frm.set_value('disbursed', []).then(() => frm.call('populate_template').then(() => frm.refresh_fields()))
			},
			() => {})
		} else if (frm.doc.disbursement_template) {
			frm.call('populate_template').then(() => frm.refresh_fields())
		}
	},

	month_recorded: (frm) => checkMonthYearWeek(frm),
	year_recorded: (frm) => checkMonthYearWeek(frm),
	week_recorded: (frm) => checkMonthYearWeek(frm)
});


frappe.ui.form.on('Disbursement Item', {
    purpose(frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);

		if (row.purpose !== 'Regular Activity') {
			row.activity_type = ''
		}
    }
})
