// Copyright (c) 2025, Jeomar Bayoguina and contributors
// For license information, please see license.txt

frappe.ui.form.on('White Gift', {
    refresh: function (frm) {
        //
    }
});

frappe.ui.form.on('White Gift Entry', {
    amount: function (frm, cdt, cdn) {
        calculate_total(frm);
    },
    white_gift_entry_remove: function (frm, cdt, cdn) {
        calculate_total(frm);
    }
});

frappe.ui.form.on('Collection Tally', {
    quantity: function (frm, cdt, cdn) {
        calculate_tally(frm, cdt, cdn);
    },
    denomination: function (frm, cdt, cdn) {
        calculate_tally(frm, cdt, cdn);
    },
    collection_tally_remove: function (frm, cdt, cdn) {
        calculate_tally_total_only(frm);
    }
});

function calculate_total(frm) {
    let total = 0;
    (frm.doc.white_gift_entry || []).forEach(row => {
        total += flt(row.amount);
    });
    frm.set_value('total', total);
    calculate_difference(frm);
}

function calculate_tally(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    row.total = flt(row.denomination) * flt(row.quantity);
    frm.refresh_field('collection_tally');
    calculate_tally_total_only(frm);
}

function calculate_tally_total_only(frm) {
    let total = 0;
    (frm.doc.collection_tally || []).forEach(row => {
        total += flt(row.total);
    });
    frm.set_value('tally_total', total);
    calculate_difference(frm);
}

function calculate_difference(frm) {
    let diff = flt(frm.doc.tally_total) - flt(frm.doc.total);
    frm.set_value('difference', diff);
}
