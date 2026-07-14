## Current Task
Donations shipped in the Vue 3 SPA: 2026+ department-scoped records, email invitations, /admin/roles Donations toggle, purpose dropdown with fuzzy dedup, mission approval flow posting Journal Entries with realtime admin toasts.

## Key Decisions
- Donation access is role-gated (Donation Editor, desk_access=0 → invitees stay Website Users); Donation.assigned_to only scopes departments; Pasig Admin assignees + Administrator see all
- Mission purposes (Donation Purpose.is_mission) need admin approval; approval posts JE (Mission Cash/Cashless → Mission Income) and locks the row server-side; record delete blocked while approved rows exist
- Stale-chunk recovery: vite:preloadError + router.onError force reload; login redirect-loop guard

## Next Steps
- User testing mission approval flow end-to-end in browser (backend verified in console)
- Cancelling a Collection doesn't cascade-cancel its Journal Entry — decide if it should
- Music team follow-ups remain: slim member view, dedicated Worship Leader view, route-guard non-music pages
