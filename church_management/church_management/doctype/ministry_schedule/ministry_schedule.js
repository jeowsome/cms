frappe.ui.form.on('Ministry Schedule', {
	refresh: function(frm) {
		// Populate Sundays / Wednesdays buttons
		if (frm.doc.month && frm.doc.year && !frm.is_new()) {
			frm.add_custom_button(__('Populate Sundays'), function() {
				frm.call('populate_sundays').then(() => {
					frm.reload_doc();
				});
			}, __('Actions'));

			frm.add_custom_button(__('Populate Wednesdays'), function() {
				frm.call('populate_wednesdays').then(() => {
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
		var has_dates = (frm.doc.sundays && frm.doc.sundays.length > 0)
			|| (frm.doc.wednesdays && frm.doc.wednesdays.length > 0);
		if (!frm.is_new() && has_dates) {
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


// ISO week number for date string, used to bucket services into "Week N"
function _iso_week(date_str) {
	let d = new Date(date_str + 'T00:00:00');
	let target = new Date(d.valueOf());
	let dayNr = (d.getDay() + 6) % 7;
	target.setDate(target.getDate() - dayNr + 3);
	let firstThursday = target.valueOf();
	target.setMonth(0, 1);
	if (target.getDay() !== 4) {
		target.setMonth(0, 1 + ((4 - target.getDay()) + 7) % 7);
	}
	return 1 + Math.ceil((firstThursday - target) / 604800000);
}

function _build_services(frm) {
	let services = [];
	(frm.doc.sundays || []).forEach(s => services.push({ date: s.sunday_date, type: 'Sunday', sermon_title: s.sermon_title }));
	(frm.doc.wednesdays || []).forEach(s => services.push({ date: s.sunday_date, type: 'Wednesday', sermon_title: s.sermon_title }));
	services.sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0));

	// Group into Week 1, 2, ... by ISO week (renumbered sequentially)
	let week_num = 0;
	let last_iso = null;
	services.forEach(s => {
		let iso = _iso_week(s.date);
		if (iso !== last_iso) { week_num++; last_iso = iso; }
		s.week = week_num;
	});
	return services;
}

function render_schedule_grid(frm) {
	// Build the visual assignment grid above the raw table
	let wrapper = frm.fields_dict.assignments.$wrapper;
	let grid_id = 'ministry-schedule-grid';

	// Remove previous grid if exists
	wrapper.find('#' + grid_id).remove();

	let services = _build_services(frm);
	let assignments = frm.doc.assignments || [];

	// Identity key: linked member when present, normalized name for guests
	let row_identity = (a) => a.member
		? 'm::' + a.member
		: 'n::' + ((a.member_name || '').trim().toLowerCase());

	// Effective service-time set for a row — used to decide if two rows actually overlap.
	// Gate Ushers is morning-only (no evening posting). Worship Leader respects service_time;
	// blank = both. Everything else covers both services unless service_time is set.
	let row_slots = (a) => {
		if (a.ministry === 'Gate Ushers') return new Set(['morning']);
		let st = (a.service_time || '').toLowerCase();
		if (st === 'morning') return new Set(['morning']);
		if (st === 'evening') return new Set(['evening']);
		return new Set(['morning', 'evening']);
	};
	let slots_overlap = (s1, s2) => {
		for (let v of s1) if (s2.has(v)) return true;
		return false;
	};

	// Group assignments by sunday_date -> ministry -> [members]
	let assignment_map = {};
	assignments.forEach(function(a) {
		let key = a.sunday_date;
		if (!assignment_map[key]) assignment_map[key] = {};
		if (!assignment_map[key][a.ministry]) assignment_map[key][a.ministry] = [];
		assignment_map[key][a.ministry].push({
			member: a.member,
			member_name: a.member_name || a.member,
			identity: row_identity(a),
			is_guest: !a.member,
			row_name: a.name
		});
	});

	// Detect conflicts: same identity, same date, different ministries, overlapping time slots.
	let by_key = {};
	assignments.forEach(function(a) {
		let key = a.sunday_date + '|' + row_identity(a);
		if (!by_key[key]) by_key[key] = [];
		by_key[key].push(a);
	});
	let conflicts = {};
	Object.keys(by_key).forEach(function(key) {
		let rows = by_key[key];
		let has_conflict = false;
		for (let i = 0; i < rows.length && !has_conflict; i++) {
			for (let j = i + 1; j < rows.length && !has_conflict; j++) {
				if (rows[i].ministry !== rows[j].ministry
					&& !rows[i].conflict_acknowledged
					&& !rows[j].conflict_acknowledged
					&& slots_overlap(row_slots(rows[i]), row_slots(rows[j]))) {
					has_conflict = true;
				}
			}
		}
		if (has_conflict) {
			conflicts[key] = [...new Set(rows.map(r => r.ministry))];
		}
	});

	// Get distinct ministries used
	let all_ministries = [...new Set(assignments.map(a => a.ministry))].sort();

	// Distinct weeks for filter dropdown
	let week_nums = [...new Set(services.map(s => s.week))].sort((a, b) => a - b);

	// Build HTML
	let html = '<div id="' + grid_id + '" style="margin-bottom: 20px;">';
	html += '<div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; gap: 12px; flex-wrap: wrap;">';
	html += '<h6 style="font-weight: 700; color: #334155; margin: 0;">Schedule Overview</h6>';
	html += '<div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">';
	html += '<select id="ms-week-filter" class="form-control input-xs" style="width: auto; display: inline-block; height: 28px;">';
	html += '<option value="all">All weeks</option>';
	week_nums.forEach(w => { html += '<option value="' + w + '">Week ' + w + '</option>'; });
	html += '</select>';
	html += '<select id="ms-ministry-filter" class="form-control input-xs" style="width: auto; display: inline-block; height: 28px;">';
	html += '<option value="all">All ministries</option>';
	all_ministries.forEach(m => { html += '<option value="' + frappe.utils.escape_html(m) + '">' + frappe.utils.escape_html(m) + '</option>'; });
	html += '</select>';
	html += '<button class="btn btn-xs btn-default" onclick="add_assignment_dialog()">+ Add Assignment</button>';
	html += '</div>';
	html += '</div>';

	if (services.length === 0) {
		html += '<p style="color: #94a3b8; font-size: 13px;">Click "Populate Sundays" or "Populate Wednesdays" first to set up the month.</p>';
		html += '</div>';
		wrapper.prepend(html);
		return;
	}

	// Conflict warnings — each row gets an "Acknowledge" button that flags the
	// underlying assignment rows so the conflict stops being detected.
	let conflict_msgs = [];
	Object.keys(conflicts).forEach(function(key) {
		let uniq_ministries = [...new Set(conflicts[key])];
		if (uniq_ministries.length > 1) {
			let sep = key.indexOf('|');
			let sunday_date = key.substring(0, sep);
			let identity = key.substring(sep + 1);
			let match = assignments.find(a => a.sunday_date === sunday_date && row_identity(a) === identity);
			let member_name = match ? (match.member_name || match.member || 'Unknown') : 'Unknown';
			conflict_msgs.push(
				'<div style="display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 4px 0;">' +
				'<span style="color: #dc2626; font-size: 12px; font-weight: 500;">' +
					frappe.utils.escape_html(member_name) + ' is double-booked on ' + sunday_date +
					' (' + uniq_ministries.map(m => frappe.utils.escape_html(m)).join(', ') + ')' +
				'</span>' +
				'<button class="btn btn-xs btn-default ms-ack-btn" ' +
					'data-conflict-date="' + sunday_date + '" ' +
					'data-conflict-identity="' + frappe.utils.escape_html(identity) + '" ' +
					'style="white-space: nowrap;">' +
					'&#10003; ' + __('Acknowledge') +
				'</button>' +
				'</div>'
			);
		}
	});

	if (conflict_msgs.length > 0) {
		html += '<div id="ms-conflicts-box" style="background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 10px 14px; margin-bottom: 12px;">';
		html += '<div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: #991b1b; margin-bottom: 6px;">Conflicts Detected</div>';
		html += conflict_msgs.join('');
		html += '</div>';
	}

	// Grid table — wrap in scroll container so wide tables don't break the page
	html += '<div style="overflow-x: auto;">';
	html += '<table style="width: 100%; border-collapse: separate; border-spacing: 0; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; font-size: 13px;">';

	// Header row — service columns (Sundays + Wednesdays)
	html += '<thead><tr style="background: #f8fafc;">';
	html += '<th style="padding: 10px 14px; text-align: left; font-size: 10px; font-weight: 900; text-transform: uppercase; letter-spacing: 0.1em; color: #94a3b8; border-bottom: 1px solid #e2e8f0; width: 140px;">Ministry</th>';
	services.forEach(function(s) {
		let d = new Date(s.date + 'T00:00:00');
		let day = d.getDate();
		let month = d.toLocaleDateString('en-US', { month: 'short' });
		let type_color = s.type === 'Sunday' ? '#0369a1' : '#5b21b6';
		html += '<th data-service-date="' + s.date + '" data-week="' + s.week + '" style="padding: 10px 14px; text-align: left; border-bottom: 1px solid #e2e8f0; border-left: 1px solid #e2e8f0; min-width: 140px;">';
		html += '<div style="font-size: 10px; font-weight: 900; text-transform: uppercase; letter-spacing: 0.1em; color: ' + type_color + ';">' + s.type + ' &middot; W' + s.week + '</div>';
		html += '<div style="font-weight: 700; font-size: 16px; color: #0f172a;">' + month + ' ' + day + '</div>';
		if (s.sermon_title) {
			html += '<div style="font-size: 11px; color: #64748b; margin-top: 2px;">' + frappe.utils.escape_html(s.sermon_title) + '</div>';
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
		html += '<tr data-ministry="' + frappe.utils.escape_html(ministry) + '">';
		html += '<td style="padding: 10px 14px; font-weight: 700; font-size: 12px; color: #0f172a; border-top: 1px solid #f1f5f9; white-space: nowrap;">';
		html += '<span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; background: ' + mc.text + ';"></span>';
		html += ministry;
		html += '</td>';

		services.forEach(function(s) {
			let members = (assignment_map[s.date] || {})[ministry] || [];
			html += '<td data-service-date="' + s.date + '" data-week="' + s.week + '" style="padding: 8px 10px; border-top: 1px solid #f1f5f9; border-left: 1px solid #f1f5f9; vertical-align: top;">';
			if (members.length === 0) {
				html += '<span style="font-size: 11px; color: #cbd5e1; font-style: italic;">—</span>';
			} else {
				members.forEach(function(m) {
					let initials = m.member_name.split(' ').map(p => p[0]).slice(0, 2).join('').toUpperCase();
					let conflict_ministries = [...new Set(conflicts[s.date + '|' + m.identity] || [])];
					let is_conflict = conflict_ministries.length > 1;
					let chip_bg = is_conflict ? '#fef2f2' : (m.is_guest ? '#fef3c7' : mc.bg);
					let chip_border = is_conflict ? '1px solid #fecaca' : (m.is_guest ? '1px dashed #f59e0b' : '1px solid transparent');
					let chip_color = is_conflict ? '#dc2626' : (m.is_guest ? '#92400e' : mc.text);
					html += '<div style="display: inline-flex; align-items: center; gap: 4px; padding: 2px 8px 2px 2px; border-radius: 999px; background: ' + chip_bg + '; border: ' + chip_border + '; margin: 2px; font-size: 11px; font-weight: 600; color: ' + chip_color + ';">';
					html += '<span style="width: 18px; height: 18px; border-radius: 50%; background: #fff; display: flex; align-items: center; justify-content: center; font-size: 8px; font-weight: 700;">' + initials + '</span>';
					html += frappe.utils.escape_html(m.member_name);
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
	html += '</div></div>';

	wrapper.prepend(html);

	// Wire up filter dropdowns
	let $grid = wrapper.find('#' + grid_id);
	function apply_filters() {
		let week_val = $grid.find('#ms-week-filter').val();
		let ministry_val = $grid.find('#ms-ministry-filter').val();

		// Show/hide service columns by week
		$grid.find('th[data-service-date], td[data-service-date]').each(function() {
			let w = this.getAttribute('data-week');
			this.style.display = (week_val === 'all' || w === week_val) ? '' : 'none';
		});
		// Show/hide ministry rows
		$grid.find('tr[data-ministry]').each(function() {
			let m = this.getAttribute('data-ministry');
			this.style.display = (ministry_val === 'all' || m === ministry_val) ? '' : 'none';
		});
	}
	$grid.find('#ms-week-filter, #ms-ministry-filter').on('change', apply_filters);

	// Wire up "Acknowledge" buttons — flag every assignment row that participates
	// in this conflict, then save so the warning disappears.
	$grid.find('.ms-ack-btn').on('click', function() {
		let btn = this;
		let date = btn.getAttribute('data-conflict-date');
		let identity = btn.getAttribute('data-conflict-identity');

		let touched = 0;
		(frm.doc.assignments || []).forEach(function(a) {
			if (a.sunday_date === date && row_identity(a) === identity && !a.conflict_acknowledged) {
				a.conflict_acknowledged = 1;
				touched++;
			}
		});

		if (touched === 0) {
			frappe.show_alert({ message: __('Already acknowledged.'), indicator: 'blue' });
			return;
		}

		frm.dirty();
		frm.save().then(() => {
			frappe.show_alert({
				message: __('Conflict acknowledged ({0} row(s)).', [touched]),
				indicator: 'green'
			});
		});
	});
}


// Global function for the "Add Assignment" button — bulk add multiple members at once
window.add_assignment_dialog = function() {
	let frm = cur_frm;
	let services = _build_services(frm);  // unified Sundays + Wednesdays, sorted

	if (services.length === 0) {
		frappe.msgprint(__('Please populate Sundays and/or Wednesdays first.'));
		return;
	}

	// Helpers used by ministry-aware field visibility
	let is_prayer_meeting = (ministry) => !!ministry && ministry.toLowerCase().indexOf('prayer meeting') !== -1;

	let date_options_for = (ministry) => {
		let filtered = services;
		if (ministry) {
			filtered = is_prayer_meeting(ministry)
				? services.filter(s => s.type === 'Wednesday')
				: services.filter(s => s.type === 'Sunday');
		}
		return filtered.map(s => {
			let dt = new Date(s.date + 'T00:00:00');
			let label = s.type + ' — ' + dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
			return { label: label, value: s.date };
		});
	};

	let d = new frappe.ui.Dialog({
		title: __('Add Ministry Assignments'),
		size: 'large',
		fields: [
			{
				fieldname: 'ministry',
				fieldtype: 'Link',
				label: __('Ministry'),
				options: 'Ministry',
				filters: { active: 1 },
				reqd: 1
			},
			{
				fieldname: 'sunday_date',
				fieldtype: 'Select',
				label: __('Service Date'),
				options: date_options_for(''),
				reqd: 1,
				description: __('Wednesdays for Prayer Meeting ministries, Sundays otherwise.')
			},
			{
				fieldname: 'service_time',
				fieldtype: 'Select',
				label: __('Service Time'),
				options: '\nMorning\nEvening',
				depends_on: 'eval:(doc.ministry || "").toLowerCase() === "worship leader"',
				description: __('Leave blank if the same leader covers both Morning and Evening.')
			},
			{ fieldname: 'members_section', fieldtype: 'Section Break', label: __('Members') },
			{
				fieldname: 'member_picker',
				fieldtype: 'Link',
				label: __('Add Member'),
				options: 'Church Member',
				description: __('Search by firstname, lastname, or envelope number. Each selection adds a chip below.')
			},
			{
				fieldname: 'selected_members_html',
				fieldtype: 'HTML'
			}
		],
		primary_action_label: __('Add All'),
		primary_action: function(values) {
			let members = d.selected_members || [];
			if (members.length === 0) {
				frappe.msgprint(__('Add at least one member before submitting.'));
				return;
			}
			_do_multi_add(frm, values.sunday_date, values.ministry, values.service_time || '', members, d);
		}
	});

	d.selected_members = [];

	// When ministry changes, re-filter the Service Date options (Wed for Prayer Meeting, Sun otherwise).
	// The Service Time field auto-shows/hides via depends_on.
	d.fields_dict.ministry.df.onchange = function() {
		let ministry = d.get_value('ministry') || '';
		let new_options = date_options_for(ministry);

		if (new_options.length === 0) {
			let need = is_prayer_meeting(ministry) ? 'Wednesdays' : 'Sundays';
			frappe.show_alert({
				message: __('No {0} in this schedule. Click "Populate {0}" first.', [need]),
				indicator: 'orange'
			}, 7);
		}

		// Rebuild options on the underlying Select control. set_df_property alone
		// doesn't reliably re-render an array-of-{label,value} options list.
		let ctrl = d.fields_dict.sunday_date;
		ctrl.df.options = new_options;
		if (ctrl.set_options) {
			ctrl.set_options();
		} else {
			// Fallback: rebuild the <select> manually
			let $sel = ctrl.$input;
			if ($sel && $sel.length) {
				$sel.empty();
				new_options.forEach(o => $sel.append(new Option(o.label, o.value)));
			}
		}
		ctrl.refresh();

		// Clear date if the current pick is no longer in the filtered list
		let current = d.get_value('sunday_date');
		let valid_dates = new_options.map(o => o.value);
		if (current && valid_dates.indexOf(current) === -1) {
			d.set_value('sunday_date', '');
		}
		// Clear service_time when leaving Worship Leader
		if (ministry.toLowerCase() !== 'worship leader') {
			d.set_value('service_time', '');
		}
	};

	// When a member is picked, add it as a chip and clear the picker
	d.fields_dict.member_picker.df.onchange = function() {
		let value = d.get_value('member_picker');
		if (!value) return;

		if (d.selected_members.find(m => m.member === value)) {
			frappe.show_alert({ message: __('Already added'), indicator: 'orange' });
			d.set_value('member_picker', '');
			return;
		}

		frappe.db.get_value('Church Member', value, ['firstname', 'lastname']).then(r => {
			let fn = (r.message && r.message.firstname) || '';
			let ln = (r.message && r.message.lastname) || '';
			let name = (fn + ' ' + ln).trim() || value;
			d.selected_members.push({ member: value, member_name: name });
			_render_chips(d);
			d.set_value('member_picker', '');
		});
	};

	_render_chips(d);
	d.show();

	// Inject prev/next service buttons + "Add guest by name" link after the dialog renders
	setTimeout(function() {
		let current_date_list = () => date_options_for(d.get_value('ministry') || '').map(o => o.value);
		let $wrap = d.fields_dict.sunday_date.$wrapper;
		if (!$wrap.find('.ms-sunday-nav').length) {
			$wrap.append(
				'<div class="ms-sunday-nav" style="display: flex; gap: 6px; margin-top: 6px;">' +
					'<button type="button" class="btn btn-xs btn-default ms-nav-prev" style="display: inline-flex; align-items: center; gap: 4px;">&lsaquo; ' + __('Previous') + '</button>' +
					'<button type="button" class="btn btn-xs btn-default ms-nav-next" style="display: inline-flex; align-items: center; gap: 4px;">' + __('Next') + ' &rsaquo;</button>' +
				'</div>'
			);
			$wrap.find('.ms-nav-prev').on('click', function() {
				let date_list = current_date_list();
				let idx = date_list.indexOf(d.get_value('sunday_date'));
				if (idx === -1) idx = 0;
				if (idx > 0) d.set_value('sunday_date', date_list[idx - 1]);
				else frappe.show_alert({ message: __('Already on the first service date'), indicator: 'blue' });
			});
			$wrap.find('.ms-nav-next').on('click', function() {
				let date_list = current_date_list();
				let idx = date_list.indexOf(d.get_value('sunday_date'));
				if (idx === -1) idx = -1;
				if (idx < date_list.length - 1) d.set_value('sunday_date', date_list[idx + 1]);
				else frappe.show_alert({ message: __('Already on the last service date'), indicator: 'blue' });
			});
		}

		let $pick = d.fields_dict.member_picker.$wrapper;
		if (!$pick.find('.ms-guest-add').length) {
			$pick.append(
				'<div style="margin-top: 6px;">' +
					'<button type="button" class="btn btn-xs btn-link ms-guest-add" style="padding-left: 0; color: #0369a1;">+ ' +
					__("Add guest by name (no church record yet)") +
					'</button>' +
				'</div>'
			);
			$pick.find('.ms-guest-add').on('click', function() { _add_guest_chip(d); });
		}
	}, 50);
};

// Prompt for a free-text name and add it as a "guest" chip with no linked member.
function _add_guest_chip(d) {
	frappe.prompt([
		{
			fieldname: 'guest_name',
			fieldtype: 'Data',
			label: __('Full Name'),
			reqd: 1,
			description: __('Use this for people without a church record yet.')
		}
	], function(values) {
		let name = (values.guest_name || '').trim();
		if (!name) return;

		let dup = (d.selected_members || []).find(
			m => !m.member && (m.member_name || '').trim().toLowerCase() === name.toLowerCase()
		);
		if (dup) {
			frappe.show_alert({ message: __('Already added'), indicator: 'orange' });
			return;
		}

		d.selected_members.push({ member: '', member_name: name, is_guest: true });
		_render_chips(d);
	}, __('Add Guest'), __('Add'));
}

function _render_chips(dlg) {
	let wrapper = dlg.fields_dict.selected_members_html.$wrapper;
	let html = '<div style="display: flex; flex-wrap: wrap; gap: 6px; min-height: 32px; padding: 8px; background: #f8fafc; border-radius: 8px; border: 1px dashed #e2e8f0;">';
	if (dlg.selected_members.length === 0) {
		html += '<span style="color: #94a3b8; font-size: 12px; font-style: italic;">' + __('No members added yet — use the picker above.') + '</span>';
	} else {
		dlg.selected_members.forEach(function(m, i) {
			let initials = m.member_name.split(' ').map(p => p[0]).slice(0, 2).join('').toUpperCase();
			let is_guest = !m.member;
			let bg = is_guest ? '#fef3c7' : '#e0f2fe';
			let fg = is_guest ? '#92400e' : '#075985';
			let close_color = is_guest ? '#b45309' : '#0369a1';
			html += '<span style="display: inline-flex; align-items: center; gap: 6px; padding: 2px 4px 2px 2px; border-radius: 9999px; background: ' + bg + '; color: ' + fg + '; font-size: 12px; font-weight: 600;">';
			html += '<span style="width: 20px; height: 20px; border-radius: 9999px; background: #fff; display: flex; align-items: center; justify-content: center; font-size: 9px; font-weight: 700;">' + initials + '</span>';
			html += '<span style="padding-right: 4px;">' + frappe.utils.escape_html(m.member_name) + (is_guest ? ' <em style="font-weight:400; font-size:10px;">(guest)</em>' : '') + '</span>';
			html += '<button type="button" data-index="' + i + '" style="border: none; background: transparent; color: ' + close_color + '; cursor: pointer; font-size: 14px; padding: 0 6px 0 0; line-height: 1;" aria-label="Remove">&times;</button>';
			html += '</span>';
		});
	}
	html += '</div>';
	html += '<div style="margin-top: 6px; font-size: 11px; color: #64748b;">' + __('{0} member(s) selected', [dlg.selected_members.length]) + '</div>';
	wrapper.html(html);

	wrapper.find('button[data-index]').on('click', function() {
		let idx = parseInt(this.dataset.index);
		dlg.selected_members.splice(idx, 1);
		_render_chips(dlg);
	});
}

function _do_multi_add(frm, sunday_date, ministry, service_time, members, dialog) {
	let added = 0;
	let skipped_duplicates = [];
	let conflicts = [];

	// Identity key so guests (no linked member) don't all collide on empty member
	let identity = (row_or_obj) => row_or_obj.member
		? 'm::' + row_or_obj.member
		: 'n::' + ((row_or_obj.member_name || '').trim().toLowerCase());

	// Same time-slot logic as the grid: Gate Ushers is morning-only,
	// Worship Leader respects service_time, blank/other ministries cover both.
	let slots_for = (m_ministry, m_service_time) => {
		if (m_ministry === 'Gate Ushers') return new Set(['morning']);
		let st = (m_service_time || '').toLowerCase();
		if (st === 'morning') return new Set(['morning']);
		if (st === 'evening') return new Set(['evening']);
		return new Set(['morning', 'evening']);
	};
	let new_slots = slots_for(ministry, service_time);

	members.forEach(function(m) {
		let m_id = identity(m);

		// Skip exact duplicate (same date + ministry + service_time + identity).
		// Morning vs Evening of the same person on the same ministry are NOT duplicates.
		let dup = (frm.doc.assignments || []).find(
			a => a.sunday_date === sunday_date
				&& a.ministry === ministry
				&& (a.service_time || '') === (service_time || '')
				&& identity(a) === m_id
		);
		if (dup) {
			skipped_duplicates.push(m.member_name);
			return;
		}

		// Cross-ministry conflict only when time slots overlap
		let clashes = (frm.doc.assignments || []).filter(function(a) {
			if (a.sunday_date !== sunday_date) return false;
			if (a.ministry === ministry) return false;
			if (identity(a) !== m_id) return false;
			let other = slots_for(a.ministry, a.service_time);
			for (let v of new_slots) if (other.has(v)) return true;
			return false;
		});
		if (clashes.length > 0) {
			conflicts.push(m.member_name + ' (' + clashes.map(c => c.ministry).join(', ') + ')');
		}

		let row = frm.add_child('assignments');
		row.sunday_date = sunday_date;
		row.ministry = ministry;
		row.service_time = service_time || '';
		row.member = m.member || '';
		row.member_name = m.member_name;
		added++;
	});

	frm.refresh_field('assignments');
	frm.dirty();

	let parts = [__('Added {0} assignment(s).', [added])];
	if (skipped_duplicates.length > 0) {
		parts.push(__('Skipped {0} already assigned: {1}.', [skipped_duplicates.length, skipped_duplicates.join(', ')]));
	}
	if (conflicts.length > 0) {
		parts.push(__('Double-booked on this service date: {0}.', [conflicts.join('; ')]));
	}

	if (added === 0) {
		frappe.show_alert({ message: parts.join(' '), indicator: 'red' }, 7);
		return;
	}

	// Persist immediately so the new rows are saved without requiring a separate Save click.
	// Keep the dialog open so the user can continue assigning to other ministries/dates.
	frm.save().then(() => {
		frappe.show_alert({
			message: parts.join(' ') + ' ' + __('Saved.'),
			indicator: conflicts.length > 0 ? 'orange' : 'green'
		}, 7);
		// Reset just the member selection; keep Ministry / Service Date / Service Time
		// so the user can quickly add another batch.
		dialog.selected_members = [];
		dialog.set_value('member_picker', '');
		_render_chips(dialog);
	}).catch((err) => {
		frappe.show_alert({
			message: __('Could not save: {0}', [(err && err.message) || __('see console for details')]),
			indicator: 'red'
		}, 9);
	});
}
