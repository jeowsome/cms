# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Church Management System for Jezreel Baptist Church Pasig. A Frappe framework custom app managing church accounting — collection of tithes, offerings, missions, benevolence funds, and recording of disbursements. Hosted on a Hostinger VPS.

**Author:** Jeomar Bayoguina
**Framework:** Frappe (Python/JS), with plans to add Vue 3 + Pinia Colada + Reka UI for Collection and Disbursement UIs
**Company abbreviation:** JBC (used in Account names like `General Cash - JBC`)
**Site:** `jbc-pasig.com`

## Common Commands

```bash
# Start development server
cd /home/frappe/frappe-bench && bench start

# Run migrations (also triggers after_migrate hooks: setup_accounting + populate_purpose)
bench --site jbc-pasig.com migrate

# Clear cache
bench --site jbc-pasig.com clear-cache

# Run a single test via bench console
bench --site jbc-pasig.com run-tests --doctype "Collection" --module "church_management"

# Run all tests for the app
bench --site jbc-pasig.com run-tests --app church_management

# Open Frappe console (use this to run test commands and quick queries)
bench --site jbc-pasig.com console

# Run a one-off migration script (e.g., data patches in church_management/)
bench --site jbc-pasig.com execute church_management.church_management.fix_fiscal_year.run

# Export fixtures (Roles, Workspace, Settings, Accounts)
bench --site jbc-pasig.com export-fixtures --app church_management
```

## Architecture

### Core Doctypes and Data Flow

**Collection** — Records a single church service's collections (morning/evening, auto-named by date+time). Contains child tables for tithes, offerings, and missions (each with cash/cashless splits). Has a denomination tally for physical cash verification. On submit, creates a **Journal Entry** posting debits to asset accounts (cash/cashless) and credits to income accounts, all mapped via `Church Management Settings`.

**Disbursement** — Monthly record of all church expenditures. Named `{month}-{year}`. Contains up to 5 weekly tabs (`disbursement_item_week_1..5` and `expense_item_week_1..5`) plus monthly tabs. Items track worker, purpose, source account, amount, and claim status. Journal Entry creation on submit is TODO.

**Disbursement Template** — Defines recurring disbursement patterns (weekly allowances, monthly expenses, mission support). `generate_disbursements()` creates Disbursement docs for selected months, distributing template items across weekly/monthly tabs.

**White Gift** — Annual special collection with cash/cashless split and tally verification. Creates Journal Entry on submit.

**Collection child tables:** `Tithes Collection`, `Offering Collection`, `Mission Collection`, `Collection Tally`, `Denomination`
**Disbursement child tables:** `Disbursement Week Item`, `Disbursement Week Expense Item`, `Monthly Disbursement Item`, `Monthly Expense Item`, `Weekly Allowance Item`, `Weekly Activity Item`, `Mission Support Item`
**Other doctypes:** `Church Member`, `Church Worker`, `Donation`/`Donation Item`, `Church Events`, `Disbursement Purpose`, `Church Cost Center Mapping`

### Accounting Integration

`Church Management Settings` (singleton) holds all account mappings — income accounts (tithes, offering, mission, benevolence, loose, sunday school, white gift), cash accounts, cashless accounts, default cost center, and default expense account. The `setup_accounting.execute()` after_migrate hook idempotently creates these accounts and cost centers under the default company.

`Disbursement Purpose` maps expense categories (Allowance, Transportation, Mission Support, etc.) to default GL accounts. Populated by `populate_purpose.execute()` after_migrate hook.

### Data Migration Scripts

Files in `church_management/church_management/` (e.g., `add_claim_button.py`, `add_company_and_filters.py`, `reorder_disbursement_fields.py`) are one-off schema migration scripts run via `bench execute`. They modify DocType field definitions programmatically.

### Reports

- `collections___year_to_date` — YTD collection summary
- `collection_vs_disbursement` — Collections vs disbursements comparison
- `disbursement_summary` / `disbursement_summary_tree` — Disbursement breakdowns
- `financial_summary_gl` — GL-based financial summary
- `year_end_collections` — Year-end collection report
- `church_members` — Member listing

### Web Pages

`church_management/www/financial_statement.html` + `.py` — Public-facing financial statement page with year/month filters and Excel export for disbursements.

### Fixtures

Exported via hooks.py: `Role` (Donation Creator/Editor), `Workspace` (JBC CMS), `DocType` (Donation/Donation Item), `Church Management Settings`, and specific `Account` records.

## Key Patterns

- Collection naming: `YYYY-MM-DD MORNING` or `YYYY-MM-DD EVENING` based on time
- Disbursement naming: `{MonthName}-{Year}` (e.g., `January-2026`)
- Cash vs Cashless is tracked separately throughout — most totals have a `_cls` counterpart field
- Account names follow `{Name} - {company_abbr}` convention (Frappe standard)
- All accounting flows go through Journal Entries, never direct GL writes
- `Church Management Settings` is the central config — read it via `frappe.get_single("Church Management Settings")`

## Dual-Graph Context Policy

This project uses a local dual-graph MCP server for efficient context retrieval.

### MANDATORY: Always follow this order

1. **Call `graph_continue` first** — before any file exploration, grep, or code reading.

2. **If `graph_continue` returns `needs_project=true`**: call `graph_scan` with the
   current project directory (`pwd`). Do NOT ask the user.

3. **If `graph_continue` returns `skip=true`**: project has fewer than 5 files.
   Do NOT do broad or recursive exploration. Read only specific files if their names
   are mentioned, or ask the user what to work on.

4. **Read `recommended_files`** using `graph_read` — **one call per file**.
   - `graph_read` accepts a single `file` parameter (string). Call it separately for each
     recommended file. Do NOT pass an array or batch multiple files into one call.
   - `recommended_files` may contain `file::symbol` entries (e.g. `src/auth.ts::handleLogin`).
     Pass them verbatim to `graph_read(file: "src/auth.ts::handleLogin")` — it reads only
     that symbol's lines, not the full file.

5. **Check `confidence` and obey the caps strictly:**
   - `confidence=high` -> Stop. Do NOT grep or explore further.
   - `confidence=medium` -> If recommended files are insufficient, call `fallback_rg`
     at most `max_supplementary_greps` time(s) with specific terms, then `graph_read`
     at most `max_supplementary_files` additional file(s). Then stop.
   - `confidence=low` -> Call `fallback_rg` at most `max_supplementary_greps` time(s),
     then `graph_read` at most `max_supplementary_files` file(s). Then stop.

### Token Usage

A `token-counter` MCP is available for tracking live token usage.

- To check how many tokens a large file or text will cost **before** reading it:
  `count_tokens({text: "<content>"})`
- To log actual usage after a task completes (if the user asks):
  `log_usage({input_tokens: <est>, output_tokens: <est>, description: "<task>"})`
- To show the user their running session cost:
  `get_session_stats()`

### Rules

- Do NOT use `rg`, `grep`, or bash file exploration before calling `graph_continue`.
- Do NOT do broad/recursive exploration at any confidence level.
- `max_supplementary_greps` and `max_supplementary_files` are hard caps - never exceed them.
- Do NOT dump full chat history.
- Do NOT call `graph_retrieve` more than once per turn.
- After edits, call `graph_register_edit` with the changed files. Use `file::symbol` notation when the edit targets a specific function, class, or hook.

### Context Store

Whenever you make a decision, identify a task, note a next step, fact, or blocker during a conversation, append it to `.dual-graph/context-store.json`.

**Entry format:**
```json
{"type": "decision|task|next|fact|blocker", "content": "one sentence max 15 words", "tags": ["topic"], "files": ["relevant/file.ts"], "date": "YYYY-MM-DD"}
```

**To append:** Read the file -> add the new entry to the array -> Write it back -> call `graph_register_edit` on `.dual-graph/context-store.json`.

**Rules:**
- Only log things worth remembering across sessions (not every minor detail)
- `content` must be under 15 words
- `files` lists the files this decision/task relates to (can be empty)
- Log immediately when the item arises — not at session end

### Session End

When the user signals they are done (e.g. "bye", "done", "wrap up", "end session"), proactively update `CONTEXT.md` in the project root with:
- **Current Task**: one sentence on what was being worked on
- **Key Decisions**: bullet list, max 3 items
- **Next Steps**: bullet list, max 3 items

Keep `CONTEXT.md` under 20 lines total. Do NOT summarize the full conversation — only what's needed to resume next session.
