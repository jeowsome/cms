# Ministry Schedule — Feature Context

Reference document for extending the Ministry Scheduling feature. Hand this to Claude (or any future maintainer) along with the relevant files when iterating.

## Purpose

Manage monthly ministry assignments for Jezreel Baptist Church Pasig. One **Ministry Schedule** doc per `{Month}-{Year}` covers all Sunday services and Wednesday prayer meetings, with per-person assignments to ministries (Music Team, Usher, Worship Leader, etc.). Drafts are private; published schedules render on the public page at `/ministry_schedule`.

## File Map

| File | Role |
|------|------|
| `church_management/doctype/ministry_schedule/ministry_schedule.json` | Parent doctype: month, year, status, three child tables (`sundays`, `wednesdays`, `assignments`) |
| `church_management/doctype/ministry_schedule/ministry_schedule.py` | Server controller: validation, conflict detection, `populate_sundays/wednesdays`, `publish/unpublish` |
| `church_management/doctype/ministry_schedule/ministry_schedule.js` | Desk form: action buttons, custom assignment grid, "+ Add Assignment" modal |
| `church_management/doctype/ministry_schedule_assignment/ministry_schedule_assignment.json` | Child doctype: one row per (date, ministry, person) assignment |
| `church_management/doctype/sunday_service_info/sunday_service_info.json` | Child doctype reused for both Sunday and Wednesday rows (date + optional theme/sermon) |
| `church_management/populate_ministry.py` | One-off seed script for the `Ministry` doctype. Includes legacy-name renames |
| `www/ministry_schedule.py` | Public page context: builds week-grouped service list with per-ministry/per-time member buckets |
| `www/ministry_schedule.html` | Public page template: hero, sermon summary, filter bar, per-week service cards |

## Data Model

### Ministry Schedule (parent)
- `month` (Select Jan-Dec), `year` (Int), composite `name` = `{month}-{year}` via `autoname: format:{month}-{year}`
- `status` Select: `Draft` / `Published`. Read-only — flipped by `publish()` / `unpublish()`
- `published_on` Datetime, set on publish
- Child tables:
  - `sundays` → `Sunday Service Info` (Sundays in the month)
  - `wednesdays` → `Sunday Service Info` (Wednesdays — reuses same shape)
  - `assignments` → `Ministry Schedule Assignment`

### Ministry Schedule Assignment (child)
- `sunday_date` (Date) — actually any service date, the field name is historical
- `ministry` (Link → Ministry)
- `service_time` (Select: blank / Morning / Evening) — only meaningful for Worship Leader. Blank means "covers both services"
- `member` (Link → Church Member, optional) — blank for guests without a church record
- `member_name` (Data, required) — has `fetch_from: member.firstname` (single-field limit), so the **display layer must batch-fetch full names** from Church Member; `member_name` alone is unreliable
- `conflict_acknowledged` (Check) — when set, this row is excluded from conflict detection

### Sunday Service Info (shared child)
- `sunday_date` (Date), optional `theme`, `sermon_title`, `sermon_passage`
- Used for both the `sundays` and `wednesdays` tables (same shape)

## Key Behaviors

### Populate dates
`populate_sundays()` / `populate_wednesdays()` fill the corresponding child table with every matching weekday in the selected month. Implemented via `_populate_weekday(child_table, weekday)` (Mon=0…Sun=6). Buttons live in the Desk form's Actions menu.

### Conflict detection (time-aware)
Two assignments only conflict if **all** of these are true:
1. Same date
2. Same person identity (linked member, or normalized typed name for guests)
3. Different ministries
4. **Time slots overlap**
5. Neither row has `conflict_acknowledged = 1`

Time slots are computed by `_row_time_slots(row)` (Python) / `row_slots(a)` (JS):
- `Gate Ushers` → `{morning}` (always — there are no evening Gate Ushers)
- `Worship Leader` with `service_time = Morning` → `{morning}`
- `Worship Leader` with `service_time = Evening` → `{evening}`
- Anything else (or blank `service_time`) → `{morning, evening}` ("all day")

To extend: if you add another time-restricted ministry, edit both the Python helper and the JS helper — they must stay in lockstep.

### Acknowledging a conflict
The Desk grid's red "Conflicts Detected" panel renders a ✓ Acknowledge button next to each conflict line. The handler walks `frm.doc.assignments`, sets `conflict_acknowledged = 1` on every row matching `(date, identity)`, and calls `frm.save()`. After save the conflict is gone from both the panel and the chip styling.

### Add Assignment modal
Three fields, in order:
1. **Ministry** (Link, required) — drives the rest of the form
2. **Service Date** (Select, required) — auto-filtered: Wednesdays for Prayer Meeting ministries (`is_prayer_meeting()` matches `prayer meeting` substring), Sundays otherwise
3. **Service Time** (Select) — only visible for `Worship Leader` via `depends_on`

Members are added as chips below (linked Members via picker, or free-text guests via "Add guest by name"). Clicking **Add All**:
- Calls `_do_multi_add` which adds each member as a child row (deduped by date+ministry+service_time+identity, time-aware conflict warning toast)
- Calls `frm.save()` to persist immediately
- Keeps the dialog open and clears just the member chips so the user can do another batch

To extend the modal (e.g., add a new field): drop it into the `fields` array; if it should react to ministry, hook into `d.fields_dict.ministry.df.onchange` (which already handles re-filtering Service Date and clearing Service Time).

### Public page render pipeline
`www/ministry_schedule.py`:
- Picks the schedule via `?schedule=<docname>` param, or defaults to the published schedule **nearest to today** (ties favor current/future over past) using a custom `distance_key`
- Batch-fetches firstname+lastname for every linked member into `member_names` and uses that for display (Frappe's `fetch_from` only stores firstname)
- Builds `assignments_map[date][ministry] = {all: [], morning: [], evening: []}` based on `service_time`
- **Same-person collapse**: if Morning and Evening lists are identical, both are merged into `all` so the page renders one name (indicating "covers both services")
- Sorts Sun + Wed services chronologically and groups by ISO week into `weeks: [{number, services: [...]}]`

`www/ministry_schedule.html`:
- Hero header + month-switcher dropdown (uses `?schedule=<name>` so multiple schedules in the same month/year are still distinct)
- Filter bar with Week chips (single-select) + Ministry chips (multi-toggle); pure client-side via `data-week`/`data-ministry` attrs and `.hidden-by-filter`
- Per-week sections, each with one service card per Sun/Wed, each card lists all ministries with assignments
- Worship Leader rows render up to three lines: All / Morning / Evening — with small color-coded pills

To extend the public page (e.g., add a "View Calendar" mode): the `weeks` structure already exposes everything you need; rebuild the markup using that without touching the Python pipeline.

## Common Extension Patterns

| Change | Where to edit |
|--------|---------------|
| Add a new ministry | `populate_ministry.py` seed list. Run the script once. |
| Rename an existing ministry | Add to the `renames` dict in `populate_ministry.py` (uses `frappe.rename_doc(force=True)` which cascades to assignment rows). |
| Add a new time-restricted ministry | Update `_row_time_slots` (Python) **and** `row_slots` (JS in the grid + modal). |
| Change the date-filter rule for the modal | Edit `is_prayer_meeting()` and/or `date_options_for()` near the top of `add_assignment_dialog`. |
| Add a field to the assignment row | (1) Add to `ministry_schedule_assignment.json` with `in_list_view: 1` if it should show in the grid; (2) include in the modal's `fields` array; (3) set it in `_do_multi_add`'s `frm.add_child(...)` block; (4) include in `www/ministry_schedule.py` if it should reach the public page. |
| Show a new column on the public page | Edit the per-ministry block inside the `{% for service in week.services %}` loop in `ministry_schedule.html`. |

## Gotchas

- **`member_name` is firstname-only on the row** because `fetch_from` only supports a single field path. Never display it directly as a "full name" — always batch-fetch from Church Member when rendering. The Desk grid currently does NOT do this fix and shows firstname-only chips; only the public page resolves full names.
- **`sunday_date` is misnamed** — it's the date of any service (Sunday or Wednesday). Don't rename without a data migration; many places query it as a string.
- **Conflict logic lives in three places** (Python validator, JS grid, JS modal). They must stay in sync. When you change one, change all three.
- **`conflict_acknowledged` is per-row, not per-conflict-pair.** Acknowledging flags every row matching `(date, identity)`. If a person has THREE overlapping ministries on the same date, one click flags all three rows.
- **Renaming Ministry records is cascading** thanks to `frappe.rename_doc`, but only when invoked through the renames block in `populate_ministry.py`. Manual SQL renames will leave assignment rows pointing at the old name.
- **Public page param is `?schedule=<docname>`**, not `?month=&year=`. The Desk form's "View Public Page" button still uses the old style — that's a known minor inconsistency, fix when convenient.
- **Tailwind on the public page is a CDN inline `<style>` block**, not a build pipeline. Match that pattern for new public templates (or migrate everything to a build, but don't mix).

## Migration & Cache

Whenever you change a doctype JSON or add a new field:
```bash
bench --site jbc-pasig.com migrate
bench --site jbc-pasig.com clear-cache
```
After JS changes, hard-refresh the browser — Frappe caches bundles aggressively.
