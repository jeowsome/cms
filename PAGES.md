# SPA Pages — Reference & Audit

Vue 3 + Pinia SPA mounted at `/church_management`. Routes use hash history
(`#/login`, `#/music/lineup`, ...). Every page is in
`church_management/frontend/src/pages/`.

Role legend used below:

| Role               | Source        | Notes                                                    |
| ------------------ | ------------- | -------------------------------------------------------- |
| Administrator      | Frappe        | Bypass — implicit via `System Manager` superset          |
| Finance Team       | App-managed   | Disbursement CRUD only                                   |
| Music Team Leader  | App-managed   | Music admin: registrations, roster, notify, publish      |
| Worship Leader     | App-managed   | Songs, practice, lineup arrangement                      |
| Music Team Member  | App-managed   | Slim profile + own schedule + swap                       |

`Music Team Leader` ⊃ `Worship Leader` ⊃ `Music Team Member` for *access*
checks but **not** for action gates — e.g. `publish_schedule` requires Music
Team Leader specifically (not Worship Leader). See **Audit › Bugs › #1**.

---

## Public pages

### `Login.vue` — `/login`
- **Purpose:** Email + password sign-in. On success, calls `landingRoute()` to
  send the user to their role's home (admin → lineup, worship leader → worship
  plan, music leader → registrations, member → profile, finance → disbursements).
- **Access:** Public.
- **API:** `music_team.login` → `music_team.whoami` (via `session.refresh()`).
- **Notes:** Lower-cases the email unless it's literally `Administrator`. Has
  a "redirect" query param so deep links to gated pages survive the bounce.

### `ForgotPassword.vue` — `/forgot-password`
- **Purpose:** Sends a Frappe password-reset email.
- **Access:** Public.
- **API:** `music_team.request_password_reset`.
- **Notes:** Always returns success to avoid user enumeration.

### `MusicRegister.vue` — `/register`
- **Purpose:** Public sign-up form for prospective music team members.
  Captures contact info + skills (filtered: Females cannot pick Worship Lead;
  Devotion is auto-locked as required for everyone).
- **Access:** Public.
- **API:** `music_team.get_roles`, `music_team.submit_registration`.
- **Notes:** Submission goes into `Music Team Registration` with status
  `Pending`; the leader reviews via `MusicRegistrations.vue`.

---

## Auth-required, all roles

### `ChangePassword.vue` — `/music/change-password`
- **Purpose:** Update password; doubles as the forced first-login flow when
  `temp_password_pending` is set on the session.
- **Access:** Any logged-in user. Router locks the user to this page until
  they finish if a temp password is pending.
- **API:** `music_team.change_password`.

---

## Disbursements — Finance Team + Admin

### `DisbursementList.vue` — `/disbursements`
- **Purpose:** Tabular list of monthly disbursements, with unclaimed-vs-planned
  counts and amounts. Filter by year. Click into a row → DisbursementForm.
- **Access:** `requiresFinance` (Finance Team or Admin).
- **API:** `disbursement.get_list`.

### `DisbursementForm.vue` — `/disbursements/:name`
- **Purpose:** Edit a single Disbursement: per-week tabs (active week
  detection, overdue blink), per-row claim/edit, bulk claim modal,
  add/remove items, monthly totals, summary card.
- **Access:** `requiresFinance`.
- **API:** `disbursement.get_detail`, `claim_item`, `claim_items_bulk`,
  `update_item`, `add_item`, `delete_item`, `get_workers`, `get_purposes`,
  `get_source_accounts`, `get_summary`.

---

## Music Team — read-only/lineup

### `MusicLineup.vue` — `/music/lineup`
- **Purpose:** Sunday-by-Sunday AM/PM grid of role assignments. Click a slot
  to open a member picker (filters by role + availability); shows open
  declines per Sunday with a "Mark resolved" button.
- **Access:** `requiresWorshipLeader` (Worship Leader / Music Leader / Admin).
- **API:** `music_team.get_lineup`, `set_assignment`, `publish_schedule`,
  `resolve_decline`, `list_unavailability`.
- ⚠ See **Audit › Bugs › #1**: `Publish & notify` button is visible to
  Worship Leaders but `publish_schedule` rejects them.

### `MusicWorship.vue` — `/music/worship` *(new this session)*
- **Purpose:** Per-Sunday worship plan editor — songs (one per line), practice
  date/time, practice location, leader notes. Includes an inline lineup picker
  so the Worship Leader can rearrange roles without leaving the page.
- **Access:** `requiresWorshipLeader`.
- **API:** `music_team.get_worship_plan`, `set_worship_plan`, plus the lineup
  read/write endpoints.

### `MusicRoles.vue` — `/music/roles`
- **Purpose:** Matrix view of every roster member × every role. Click a cell
  to mark **allowed → preferred → cleared** (3-state cycle). Each click
  immediately persists.
- **Access:** `requiresLeader` (Music Team Leader or Admin).
- **API:** `music_team.get_members`, `set_member_roles`.

### `MusicUnavail.vue` — `/music/unavail`
- **Purpose:** Two tabs:
  1. **Unavailability windows** — timeline visualisation of every member's
     leave/medical/suspended/event blocks.
  2. **Decline log** — every `Schedule Decline` row with status pill.
- **Access:** `requiresLeader`.
- **API:** `music_team.list_unavailability`, `list_declines`,
  `create_unavailability`.

### `MusicNotify.vue` — `/music/notify`
- **Purpose:** Compose songs/practice/swap/general messages. Picks a Sunday
  and service, auto-resolves recipients from the lineup, sends via email
  (and optional SMS toggle). Logs sent notifications below.
- **Access:** `requiresLeader`.
- **API:** `music_team.send_notification`, `list_notifications`,
  `get_lineup`.

### `MusicRegistrations.vue` — `/music/registrations`
- **Purpose:** Side-by-side review queue for `Music Team Registration` rows.
  Per-field check/cross icons sync envelope-matched Church Member fields
  either direction. Accept creates a User + temp password and emails it;
  Reject records a reason.
- **Access:** `requiresLeader`.
- **API:** `music_team.list_registrations`, `update_registration`,
  `apply_match_field`, `accept_registration`, `reject_registration`.

---

## Music Team — member self-service

### `MusicMember.vue` — `/music/me` *(rewritten this session)*
- **Purpose:** Slim mobile-first "My Schedule" — auto-resolves the logged-in
  user's Church Member, shows the next assignment hero card, three quick
  actions (Confirm ✓ / Swap ↔ / Decline ✕), inline lists of incoming swap
  requests + outgoing pending requests, and the upcoming list with per-row
  action buttons.
- **Access:** `requiresMusic` (any music role; the page is shown to leaders
  too but the member-only sidebar surfaces it as the primary route).
- **API:** `music_team.my_assignments`, `confirm_assignment`,
  `decline_assignment`, `request_swap`, `respond_swap`, `cancel_swap`,
  `list_swap_requests`, `list_swap_candidates`.

### `MusicProfile.vue` — `/music/profile`
- **Purpose:** Personal profile editor — name, profile picture upload, skills
  + preferred role, plus the member's own unavailability windows and a
  read-only list of upcoming assignments.
- **Access:** `requiresMusic`.
- **API:** `music_team.get_my_music_profile`, `update_my_music_profile`,
  `list_unavailability` (filtered client-side to own member),
  `create_unavailability`, `delete_unavailability`, `my_assignments`,
  `get_roles`.

---

## Admin

### `AdminRoles.vue` — `/admin/roles` *(new this session)*
- **Purpose:** Grant/revoke the four app-managed roles per user. Filter chips
  with live counts, search, role-color toggle pills, dirty-state save with
  reset, success/failure flash.
- **Access:** `requiresLeader`. Music Team Leader sees Website Users only and
  can grant only Worship Leader / Music Team Member; Admin sees every enabled
  user and can grant all four. Other Frappe roles are never touched.
- **API:** `admin.list_grantable_roles`, `admin.list_assignable_users`,
  `admin.set_user_roles`.

---

## Audit

### Bugs

1. **`MusicLineup.vue` `Publish & notify` shown to Worship Leaders → 403**
   - Worship Leader can land on `/music/lineup` (the route is gated to
     `requiresWorshipLeader`), but `publish_schedule` is gated server-side
     to `require_music_leader`. Clicking the button surfaces a
     `PermissionError`.
   - **Fix:** wrap the button in `v-if="session.isLeader"` *or* loosen the
     server gate to `require_worship_leader`. Picking the former preserves
     the intended split (leader publishes, worship leader arranges).

2. **`MusicMember.vue` shadows `window.confirm`**
   - The page defines `function confirm(a)` (assignment-confirm), which
     hides the global `window.confirm` inside the `<script setup>` scope.
     The original implementation of `cancelSwap` had `if (!confirm) return;`
     which always evaluated truthy — fixed during this session to use
     `window.confirm(...)`. Footgun: any future code that types `confirm("…")`
     in this file will silently call the assignment helper with a string.
   - **Fix:** rename the local function to `confirmAssignment` (or `confirmRow`)
     for clarity.

3. **`Music Swap Request` doctype permissions don't include Worship Leader**
   - The doctype JSON grants read/create/write to System Manager, Music Team
     Member, Music Team Leader. A Worship Leader querying via REST
     (`/api/resource/...`) would be denied. The whitelisted endpoints all use
     `ignore_permissions` paths, so the SPA itself isn't affected — but it
     is inconsistent with the role hierarchy.
   - **Fix:** add a Worship Leader read permission row, or document that the
     doctype is API-only.

4. **`is_planned` field on monthly expense rows isn't populated**
   - Cosmetic, in DisbursementForm. The summary computes `totalPlanned` from
     `i.is_planned`, but `Monthly Expense Item` rows don't carry that flag,
     so they're under-counted in the planned total. Pre-existing — not
     introduced by this session's changes.

### Gaps / missing features

5. **Members can't see the worship plan**
   - Worship Leader sets songs + practice date/time/location on
     `MusicWorship.vue`, but `MusicMember.vue` has no surface for the team to
     read it. The "Songs" / "Practice" quick-action buttons on the next-up
     hero card are placeholders without click handlers.
   - **Fix:** extend `my_assignments` (or add `get_my_worship_plan`) to
     attach the per-Sunday `songs`, `practice_datetime`, `practice_location`,
     `worship_leader_notes` for each upcoming row, and render them on
     `MusicMember.vue`.

6. **No leader-side view of swap requests**
   - `Music Swap Request` rows are visible to the originator, the proposed
     replacement, and (via `list_swap_requests`) any leader who calls the
     endpoint. There's no UI for it. `MusicUnavail.vue` already aggregates
     declines — adding a third tab "Swap requests" would close the loop.

7. **`MusicNotify.vue` doesn't notify on swap-accepted / decline-resolved**
   - Notification type list is `songs / practice / swap / general` but the
     actual swap workflow goes via `Music Swap Request` (email + realtime).
     The "swap" notification type from MusicNotify is a separate manual
     compose; redundant once the swap flow is fully adopted.
   - **Suggestion:** drop `swap` from `MusicNotify.vue` `TYPES` to reduce
     ambiguity.

8. **No worship-leader assignment UI**
   - `Worship Leader` is granted via `AdminRoles.vue`, but a typical workflow
     would be the Music Team Leader promoting an existing Music Team Member.
     `MusicRoles.vue` only handles instrument-role preferences, not Frappe
     roles. The new `AdminRoles.vue` covers it but isn't linked from
     anywhere obvious during the leader flow (e.g. the registrations queue).
   - **Suggestion:** in `MusicRegistrations.vue`, after Accept, surface a
     "Open role assignments" link.

9. **Disbursement audit log / approval workflow**
   - Out of scope for the role refactor but worth noting: there's no
     approval gate before a Disbursement is submitted. Finance Team has full
     CRUD. If you want a four-eyes flow (creator vs approver), it'd need a
     new role split + workflow on the doctype.

### Inconsistencies

10. **Two "logout" surfaces**
    - `AppSidebar.vue` (desktop) and `MusicProfile.vue` / `MusicRegistrations.vue`
      hero each render their own logout button. Not buggy — just visually
      duplicated for users who use those pages.

11. **`MusicMember.vue` "Songs" / "Practice" quick action buttons are dead**
    - The 3-button quick-action grid on the next-up hero contains Songs and
      Practice icons that don't do anything yet (placeholders for #5).

12. **Mobile bottom nav doesn't include Role Assignments**
    - `BottomNav.vue` shows Disbursements, Music, Worship for the right
      roles, but skips `/admin/roles`. Probably fine — it's a desktop-leaning
      admin task — but worth deciding explicitly.

13. **`MusicRoles.vue` — slim member view sees no link in nav, but server
    allows them to update their own preferences**
    - `set_member_roles` server-side honors `_require_self_or_leader`. The
      slim-member sidebar doesn't expose `/music/roles`, but a member could
      still navigate manually and the page would render the full team grid,
      where only their own row is editable. Either:
      - Hide the page from the URL for members (return 403 on render), or
      - Add a dedicated "My Roles" sub-view under `/music/profile` (already
        partially done — profile lets them edit skills + preferred role).
    - Currently it's `requiresLeader`, so members are redirected away. ✅
      No bug — listed for clarity.

### Missing tests / verification

14. There are no automated tests for the new endpoints (`confirm_assignment`,
    `request_swap`, `respond_swap`, `cancel_swap`, `set_worship_plan`,
    `list_swap_candidates`, `set_user_roles`). Manual smoke tests via
    `bench --site jbc-pasig.com execute …` confirmed the happy paths;
    edge cases (e.g. swap request when from-member isn't actually assigned)
    are unverified.

---

## Recommended next session

Highest-value fixes, in order:

1. **#1** — hide the lineup Publish button for non-leaders. ~2 lines.
2. **#5** — surface songs/practice on the member view (extend
   `my_assignments` to join Sunday Service Info, render on `MusicMember.vue`).
3. **#6** — leader swap-requests dashboard tab on `MusicUnavail.vue`.
4. **#2** — rename `confirm` → `confirmAssignment` in `MusicMember.vue`.
5. **#11** — wire the Songs/Practice quick-action buttons (or remove them).
