## Current Task
Vue 3 frontend scaffolded and building successfully. Ready to implement Disbursement UI features.

## Key Decisions
- Tailwind v3 (not v4) due to Node 18 compatibility on server
- Hash-mode Vue Router (`/church_management#/disbursements`) to avoid server-side route conflicts
- API endpoints in `church_management/api/` grouped by feature (disbursement.py, collection.py, settings.py)

## Next Steps
- Test the SPA at `/church_management` with bench running
- Implement full Disbursement form editing (create/save/submit)
- Add Reka UI components (Dialog, Select, Popover) for interactive form elements
