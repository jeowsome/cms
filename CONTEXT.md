## Current Task
Music team UI ported from `frontend/ui_kits/music-team/` into Vue 3 SPA, wired to Frappe doctypes with socket.io realtime.

## Key Decisions
- New doctypes: `Member Unavailability`, `Schedule Decline`, `Music Team Notification` (+ recipient child)
- Added `music_role` (Link → Music Team Tag) on `Ministry Schedule Assignment`; added `preferred` Check on `Music Role Preference`
- Realtime via Frappe `publish_realtime` → `socket.io-client`; `useRealtime(event, handler)` composable in `composables/useRealtime.js`
- All music-team API endpoints in `church_management/api/music_team.py`; routes under `/music/*` in hash router

## Next Steps
- Test 5 pages live at `/church_management#/music/lineup` (and roles, unavail, me, notify)
- Port the JBC desk worship-leader role/permissions if needed
- Wire `MusicMember` to the logged-in user's linked Church Member instead of dropdown
