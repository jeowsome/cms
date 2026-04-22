// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Church Member', {
	refresh: function(frm) {
		frm.trigger('toggle_music_team_tag');
		frm.trigger('sync_music_role_preference');
	},

	toggle_music_team_tag: function(frm) {
		const has_music_team = (frm.doc.ministry || []).some(r => r.ministry === 'Music Team');
		if (!has_music_team) {
			frm.clear_table('music_team_tag');
			frm.refresh_field('music_team_tag');
			frm.clear_table('music_role_preference');
			frm.refresh_field('music_role_preference');
		}
	},

	sync_music_role_preference: function(frm) {
		const current_tags = (frm.doc.music_team_tag || []).map(r => r.music_team_tag);
		const current_prefs = frm.doc.music_role_preference || [];

		// Remove rows whose tag no longer exists in music_team_tag
		const to_remove = current_prefs.filter(r => !current_tags.includes(r.music_team_tag));
		to_remove.forEach(r => {
			frm.doc.music_role_preference = frm.doc.music_role_preference.filter(row => row.name !== r.name);
		});

		// Add rows for tags that don't have a preference row yet
		const existing_tags = current_prefs
			.filter(r => current_tags.includes(r.music_team_tag))
			.map(r => r.music_team_tag);

		current_tags.forEach(tag => {
			if (!existing_tags.includes(tag)) {
				const row = frm.add_child('music_role_preference');
				row.music_team_tag = tag;
				row.skill_level = '1';
			}
		});

		frm.refresh_field('music_role_preference');
	}
});

frappe.ui.form.on('Church Member Ministry', {
	ministry: function(frm) {
		frm.trigger('toggle_music_team_tag');
	},
	ministry_remove: function(frm) {
		frm.trigger('toggle_music_team_tag');
	}
});

frappe.ui.form.on('Church Member Music Tag', {
	music_team_tag: function(frm, cdt, cdn) {
		const row = locals[cdt][cdn];

		// Prevent duplicate tags
		const duplicates = (frm.doc.music_team_tag || []).filter(
			r => r.music_team_tag === row.music_team_tag && r.name !== cdn
		);
		if (duplicates.length) {
			frappe.msgprint(__('Music Team Tag {0} is already added.', [row.music_team_tag]));
			frappe.model.set_value(cdt, cdn, 'music_team_tag', '');
			return;
		}

		frm.trigger('sync_music_role_preference');
	},
	music_team_tag_remove: function(frm) {
		frm.trigger('sync_music_role_preference');
	}
});
