frappe.ui.form.on('Ministry Schedule', {
	refresh: function(frm) {
		// Populate Sundays button
		if (frm.doc.month && frm.doc.year && !frm.is_new()) {
			frm.add_custom_button(__('Populate Sundays'), function() {
				frm.call('populate_sundays').then(() => {
					frm.reload_doc();
				});
			}, __('Actions'));
		}

		// Publish / Unpublish buttons
		if (!frm.is_new() && frm.doc.status === 'Draft') {
			frm.add_custom_button(__('Publish'), function() {
				frappe.confirm(
					__('Publish this schedule? It will be visible on the public Ministry Schedule page.'),
					function() {
						frm.call('publish').then(() => {
							frm.reload_doc();
						});
					}
				);
			}, __('Actions'));
		}

		if (!frm.is_new() && frm.doc.status === 'Published') {
			frm.add_custom_button(__('Unpublish'), function() {
				frm.call('unpublish').then(() => {
					frm.reload_doc();
				});
			}, __('Actions'));

			frm.add_custom_button(__('View Public Page'), function() {
				window.open('/ministry_schedule?month=' + frm.doc.month + '&year=' + frm.doc.year, '_blank');
			});
		}

		// Render the visual schedule grid
		if (!frm.is_new() && frm.doc.sundays && frm.doc.sundays.length > 0) {
			render_schedule_grid(frm);
		}

		// Color the status indicator
		if (frm.doc.status === 'Published') {
			frm.page.set_indicator(__('Published'), 'green');
		} else {
			frm.page.set_indicator(__('Draft'), 'orange');
		}
	},

	month: function(frm) {
		if (frm.doc.month && frm.doc.year) {
			frm.trigger('refresh');
		}
	},

	year: function(frm) {
		if (frm.doc.month && frm.doc.year) {
			frm.trigger('refresh');
		}
	}
});


function render_schedule_grid(frm) {
	// Build the visual assignment grid above the raw table
	let wrapper = frm.fields_dict.assignments.$wrapper;
	let grid_id = 'ministry-schedule-grid';

	// Remove previous grid if exists
	wrapper.find('#' + grid_id).remove();

	let sundays = frm.doc.sundays || [];
	let assignments = frm.doc.assignments || [];

	// Group assignments by sunday_date -> ministry -> [members]
	let assignment_map = {};
	assignments.forEach(function(a) {
		let key = a.sunday_date;
		if (!assignment_map[key]) assignment_map[key] = {};
		if (!assignment_map[key][a.ministry]) assignment_map[key][a.ministry] = [];
		assignment_map[key][a.ministry].push({
			member: a.member,
			member_name: a.member_name || a.member,
			row_name: a.name
		});
	});

	// Detect conflicts: member in multiple ministries on same Sunday
	let conflicts = {};
	assignments.forEach(function(a) {
		let key = a.sunday_date + '|' + a.member;
		if (!conflicts[key]) conflicts[key] = [];
		conflicts[key].push(a.ministry);
	});

	// Get distinct ministries used
	let all_ministries = [...new Set(assignments.map(a => a.ministry))].sort();

	// Build HTML
	let html = '<div id="' + grid_id + '" style="margin-bottom: 20px; overflow-x: auto;">';
	html += '<div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">';
	html += '<h6 style="font-weight: 700; color: #334155; margin: 0;">Schedule Overview</h6>';
	html += '<button class="btn btn-xs btn-default" onclick="add_assignment_dialog()">+ Add Assignment</button>';
	html += '</div>';

	if (sundays.length === 0) {
		html += '<p style="color: #94a3b8; font-size: 13px;">Click "Populate Sundays" first to set up the month.</p>';
		html += '</div>';
		wrapper.prepend(html);
		return;
	}

	// Conflict warnings
	let conflict_msgs = [];
	Object.keys(conflicts).forEach(function(key) {
		if (conflicts[key].length > 1) {
			let parts = key.split('|');
			let member_name = parts[1];
			// Find actual name from assignments
			let match = assignments.find(a => a.member === parts[1] && a.sunday_date === parts[0]);
			if (match) member_name = match.member_name || match.member;
			conflict_msgs.push(
				'<span style="color: #dc2626; font-size: 12px; font-weight: 500;">' +
				member_name + ' is double-booked on ' + parts[0] +
				' (' + conflicts[key].join(', ') + ')</span>'
			);
		}
	});

	if (conflict_msgs.length > 0) {
		html += '<div style="background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 10px 14px; margin-bottom: 12px;">';
		html += '<div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: #991b1b; margin-bottom: 6px;">Conflicts Detected</div>';
		html += conflict_msgs.join('<br>');
		html += '</div>';
	}

	// Grid table
	html += '<table style="width: 100%; border-collapse: separate; border-spacing: 0; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; font-size: 13px;">';

	// Header row — Sundays
	html += '<thead><tr style="background: #f8fafc;">';
	html += '<th style="padding: 10px 14px; text-align: left; font-size: 10px; font-weight: 900; text-transform: uppercase; letter-spacing: 0.1em; color: #94a3b8; border-bottom: 1px solid #e2e8f0; width: 140px;">Ministry</th>';
	sundays.forEach(function(s) {
		let d = new Date(s.sunday_date);
		let day = d.getDate();
		let weekday = d.toLocaleDateString('en-US', { weekday: 'short' });
		let month = d.toLocaleDateString('en-US', { month: 'short' });
		html += '<th style="padding: 10px 14px; text-align: left; border-bottom: 1px solid #e2e8f0; border-left: 1px solid #e2e8f0;">';
		html += '<div style="font-size: 10px; font-weight: 900; text-transform: uppercase; letter-spacing: 0.1em; color: #94a3b8;">Sunday</div>';
		html += '<div style="font-weight: 700; font-size: 16px; color: #0f172a;">' + month + ' ' + day + '</div>';
		if (s.sermon_title) {
			html += '<div style="font-size: 11px; color: #64748b; margin-top: 2px;">' + s.sermon_title + '</div>';
		}
		html += '</th>';
	});
	html += '</tr></thead>';

	// Body rows — one per ministry
	let ministry_colors = [
		{ bg: '#fffbeb', text: '#92400e' },
		{ bg: '#fff1f2', text: '#9f1239' },
		{ bg: '#f0f9ff', text: '#075985' },
		{ bg: '#ecfdf5', text: '#065f46' },
		{ bg: '#f5f3ff', text: '#5b21b6' },
		{ bg: '#eef2ff', text: '#3730a3' },
		{ bg: '#fdf2f8', text: '#9d174d' },
		{ bg: '#f0fdfa', text: '#115e59' },
	];

	html += '<tbody>';
	all_ministries.forEach(function(ministry, midx) {
		let mc = ministry_colors[midx % ministry_colors.length];
		html += '<tr>';
		html += '<td style="padding: 10px 14px; font-weight: 700; font-size: 12px; color: #0f172a; border-top: 1px solid #f1f5f9; white-space: nowrap;">';
		html += '<span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; background: ' + mc.text + ';"></span>';
		html += ministry;
		html += '</td>';

		sundays.forEach(function(s) {
			let members = (assignment_map[s.sunday_date] || {})[ministry] || [];
			html += '<td style="padding: 8px 10px; border-top: 1px solid #f1f5f9; border-left: 1px solid #f1f5f9; vertical-align: top;">';
			if (members.length === 0) {
				html += '<span style="font-size: 11px; color: #cbd5e1; font-style: italic;">—</span>';
			} else {
				members.forEach(function(m) {
					let initials = m.member_name.split(' ').map(p => p[0]).slice(0, 2).join('').toUpperCase();
					let is_conflict = (conflicts[s.sunday_date + '|' + m.member] || []).length > 1;
					let chip_bg = is_conflict ? '#fef2f2' : mc.bg;
					let chip_border = is_conflict ? '1px solid #fecaca' : '1px solid transparent';
					let chip_color = is_conflict ? '#dc2626' : mc.text;
					html += '<div style="display: inline-flex; align-items: center; gap: 4px; padding: 2px 8px 2px 2px; border-radius: 999px; background: ' + chip_bg + '; border: ' + chip_border + '; margin: 2px; font-size: 11px; font-weight: 600; color: ' + chip_color + ';">';
					html += '<span style="width: 18px; height: 18px; border-radius: 50%; background: #fff; display: flex; align-items: center; justify-content: center; font-size: 8px; font-weight: 700;">' + initials + '</span>';
					html += m.member_name;
					if (is_conflict) {
						html += ' <span title="Double-booked" style="color: #dc2626;">&#9888;</span>';
					}
					html += '</div>';
				});
			}
			html += '</td>';
		});
		html += '</tr>';
	});
	html += '</tbody></table>';
	html += '</div>';

	wrapper.prepend(html);
}


// Global function for the "Add Assignment" button
window.add_assignment_dialog = function() {
	let frm = cur_frm;
	let sundays = (frm.doc.sundays || []).map(s => s.sunday_date);

	if (sundays.length === 0) {
		frappe.msgprint(__('Please populate Sundays first.'));
		return;
	}

	let d = new frappe.ui.Dialog({
		title: __('Add Ministry Assignment'),
		fields: [
			{
				fieldname: 'sunday_date',
				fieldtype: 'Select',
				label: __('Sunday'),
				options: sundays.map(s => {
					let dt = new Date(s);
					return { label: dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }), value: s };
				}),
				reqd: 1
			},
			{
				fieldname: 'ministry',
				fieldtype: 'Link',
				label: __('Ministry'),
				options: 'Ministry',
				filters: { active: 1 },
				reqd: 1
			},
			{
				fieldname: 'member',
				fieldtype: 'Link',
				label: __('Member'),
				options: 'Church Member',
				reqd: 1
			}
		],
		primary_action_label: __('Add'),
		primary_action: function(values) {
			// Check if this member is already assigned to another ministry on the same Sunday
			let existing = (frm.doc.assignments || []).filter(
				a => a.sunday_date === values.sunday_date && a.member === values.member && a.ministry !== values.ministry
			);
			if (existing.length > 0) {
				frappe.confirm(
					__('This member is already assigned to {0} on this Sunday. Add anyway?', [existing.map(e => e.ministry).join(', ')]),
					function() {
						_do_add(frm, values, d);
					}
				);
			} else {
				// Check for exact duplicate
				let dup = (frm.doc.assignments || []).find(
					a => a.sunday_date === values.sunday_date && a.member === values.member && a.ministry === values.ministry
				);
				if (dup) {
					frappe.msgprint(__('This member is already assigned to this ministry on this Sunday.'));
					return;
				}
				_do_add(frm, values, d);
			}
		}
	});
	d.show();
};

function _do_add(frm, values, dialog) {
	let row = frm.add_child('assignments');
	row.sunday_date = values.sunday_date;
	row.ministry = values.ministry;
	row.member = values.member;
	// Fetch member name
	frappe.db.get_value('Church Member', values.member, ['firstname', 'lastname']).then(r => {
		let fn = r.message.firstname || '';
		let ln = r.message.lastname || '';
		row.member_name = (fn + ' ' + ln).trim() || values.member;
		frm.refresh_field('assignments');
		frm.dirty();
		frm.trigger('refresh');
	});
	dialog.hide();
}
