## Current Task
Music team registration + login + leader queue + member profile shipped (Vue 3 SPA + Frappe). Public `/music_register`, role-aware `/login`, side-by-side envelope match verification with per-field apply check/cross icons.

## Key Decisions
- New doctype `Music Team Registration` (Pending/Accepted/Rejected, soft envelope match)
- Roles `Music Team Member` + `Music Team Leader` via `setup_music_roles.execute`; acceptance creates User + temp password, forces `/music/change-password` first login
- Match panel syncs `first_name/last_name/email/contact_number/birthday` either direction via `apply_match_field`; envelope is verification-only

## Next Steps
- Cleanup music team member view — must differ from leader/admin view (slim profile-centric, no admin tools)
- Build a dedicated Worship Leader view (separate from Music Team Leader's registrations queue)
- Restrict music-team-only roles to music pages; hide and route-guard Disbursements + other non-music pages
