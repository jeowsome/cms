// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

const computeTotals = (frm, collection, total_field_cash, counter_field_cash, total_field_cls, counter_field_cls) => {
    let total_cash = 0;
    let total_cashless = 0;
    let num_rows_cash = 0;
    let num_rows_cashless = 0;
    const rows = collection;

    rows.map(row => {
        if (row.account_type === "Cash") {
            total_cash += row.amount;
            num_rows_cash++;
        } else {
            total_cashless += row.amount;
            num_rows_cashless++;
        }

    })
    frm.set_value(total_field_cash, total_cash)
    frm.set_value(counter_field_cash, num_rows_cash)
    frm.set_value(total_field_cls, total_cashless)
    frm.set_value(counter_field_cls, num_rows_cashless)
    computeGrandTotal(frm)
}

const computeGrandTotal = (frm) => {
    let grand_total_cash = frm.doc.tithes_total + frm.doc.offering_total + frm.doc.mission_total
        + frm.doc.benevolence_collection + frm.doc.loose_collection + frm.doc.sunday_school_collection;

    let grand_total_cls = frm.doc.tithes_total_cls + frm.doc.offering_total_cls + frm.doc.mission_total_cls
        + frm.doc.benevolence_collection_cls + frm.doc.loose_collection_cls;

    let tithes = frm.doc.tithes_total + frm.doc.tithes_total_cls;
    let offering = frm.doc.offering_total + frm.doc.offering_total_cls;
    let mission = frm.doc.mission_total + frm.doc.mission_total_cls;
    let loose = frm.doc.loose_collection + frm.doc.loose_collection_cls;
    let benevolence = frm.doc.benevolence_collection + frm.doc.benevolence_collection_cls;

    frm.set_value('all_tithes_total', tithes);
    frm.set_value('all_offering_total', offering);
    frm.set_value('all_mission_total', mission);
    frm.set_value('all_loose_total', loose);
    frm.set_value('all_benevolence_total', benevolence);
    frm.set_value('grand_total_cls', grand_total_cls)
    frm.set_value('grand_total', grand_total_cash);
    frm.set_value('all_grand_total', grand_total_cash + grand_total_cls);
}

frappe.ui.form.on('Collection', {
    onload: function (frm) {
        if (!frm.doc.cost_center) {
            frappe.db.get_single_value('Church Management Settings', 'default_cost_center')
                .then(value => {
                    if (value) {
                        frm.set_value('cost_center', value);
                    }
                });
        }
    },
    loose_collection: computeGrandTotal,
    loose_collection_cls: computeGrandTotal,
    benevolence_collection: computeGrandTotal,
    benevolence_collection_cls: computeGrandTotal,
    sunday_school_collection: computeGrandTotal
});

frappe.ui.form.on('Tithes Collection', {
    amount: (frm, cdt, cdn) => {
        computeTotals(frm, frm.doc.tithes_collection, 'tithes_total', 'no_of_tithes',
            'tithes_total_cls', 'no_of_tithes_cls');
    },
    tithes_collection_remove: (frm, cdt, cdn) => {
        computeTotals(frm, frm.doc.tithes_collection, 'tithes_total', 'no_of_tithes',
            'tithes_total_cls', 'no_of_tithes_cls');
    },
});

frappe.ui.form.on('Offering Collection', {
    amount: (frm, cdt, cdn) => {
        computeTotals(frm, frm.doc.offering_collection, 'offering_total', 'no_of_offering',
            'offering_total_cls', 'no_of_offering_cls');
    },
    offering_collection_remove: (frm, cdt, cdn) => {
        computeTotals(frm, frm.doc.offering_collection, 'offering_total', 'no_of_offering',
            'offering_total_cls', 'no_of_offering_cls');
    },
});

frappe.ui.form.on('Mission Collection', {
    amount: (frm, cdt, cdn) => {
        computeTotals(frm, frm.doc.mission_collection, 'mission_total', 'no_of_mission',
            'mission_total_cls', 'no_of_mission_cls');
    },
    mission_collection_remove: frm => {
        computeTotals(frm, frm.doc.mission_collection, 'mission_total', 'no_of_mission',
            'mission_total_cls', 'no_of_mission_cls');
    },
});

frappe.ui.form.on('Collection Tally', {
    quantity: (frm, cdt, cdn) => {
        const row = locals[cdt][cdn];
        let total = 0;
        const tally = frm.doc.collection_tally;
        tally.map(bill => {
            bill.total = parseFloat(bill.denomination) * bill.quantity;
            total += bill.total;
        })
        row.total = row.denomination * row.quantity;
        frm.set_value('tally_total', total);
        frm.refresh_field('tally_total');
        frm.refresh_field('collection_tally');
    },

    denomination: (frm, cdt, cdn) => {
        const row = locals[cdt][cdn];
        let total = 0;
        const tally = frm.doc.collection_tally;
        tally.map(bill => {
            bill.total = parseFloat(bill.denomination) * bill.quantity;
            total += bill.total;
        })
        row.total = row.denomination * row.quantity;
        frm.set_value('tally_total', total);
        frm.refresh_field('tally_total');
        frm.refresh_field('collection_tally');
    },
});