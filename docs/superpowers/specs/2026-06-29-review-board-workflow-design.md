# Task 50G Review Board Workflow Design

## Goal

Add a Review Board workflow to `D:\Views\yonlab-g2b-agent-v2` so operators can see active shortlist/review states, next actions, and quick entry points into the existing Opportunity Inbox and Daily Review Pack without triggering any real G2B API call.

## Scope

This design covers:

- a safe `GET /ops/review-board` summary endpoint
- a top-of-dashboard Review Board section on `/ui`
- Opportunity Inbox filter linking from Review Board cards
- a next-action list sorted by nearest deadline
- Daily Review Pack summary/export updates for review workflow fields
- review status panel UX polish in the existing opportunity detail area
- development validation, rc14 release candidate tagging, fresh deployment, and no-real smoke verification

This design does not cover:

- any new real G2B API behavior
- any external AI/LLM call
- any `.env` generation or secret exposure
- changes to `D:\Views\yonlab-bid-agent`
- replacing existing `/readiness`, `/recommendations`, or real-run runtime behavior

## Current Context

The current `main` head is `33af5e0`, which is a docs-only clarification after the already validated `v0.1.0-rc13` release. The application already has:

- local JSON-backed review status persistence
- `/ops/review-status` CRUD endpoints
- Opportunity Inbox merge of review status fields
- Daily Review Pack reflection of shortlist/review state
- `/ui` dashboard with inbox, detail panel, safe daily status, and export hooks
- no-real validation and safe-daily scripts

Because these pieces already exist, the most conservative approach is to add a small orchestration layer for Review Board summaries instead of inventing a new data model or moving logic into the browser.

## Chosen Approach

Use a new service module, `app/services/review_board.py`, to build Review Board payloads from already available opportunity items plus local review status metadata.

Why this approach:

- it keeps grouping, counting, sorting, and safety flags on the server
- it avoids making `daily_review_pack.py` or `dashboard.js` absorb too much new logic
- it allows deterministic TDD around one focused service boundary
- it preserves the existing Inbox and Daily Review Pack as downstream execution surfaces

Rejected alternatives:

1. Expand `daily_review_pack.py` to also own Review Board data.
   - Rejected because it would blur the line between a daily report package and the top-level operational board.

2. Compute the whole Review Board in `dashboard.js`.
   - Rejected because it would duplicate sorting/filter logic in the UI and weaken API-level tests.

## UX Design

### Review Board placement

The Review Board sits near the top of `/ui`, above Opportunity Inbox.

It serves as the operator's entry point for "what needs attention now," while Inbox remains the working list and Opportunity Detail remains the action surface.

### Review Board default emphasis

The board emphasizes active states first:

- `go`
- `reviewing`
- `shortlisted`
- `hold`

`new` remains visible in Inbox, but it is not the first thing emphasized in the board. `no_go`, `submitted`, and `archived` are kept as lower-emphasis counts or secondary groups rather than the primary operational focus.

### Card behavior

Review Board status cards are clickable.

Clicking a card updates Opportunity Inbox filters and reloads the inbox so the board acts as a direct navigation control, not just a static summary. This keeps the user inside the existing workflow instead of creating a competing detail surface.

### Next Action Board

The board includes a `next_action` section that only shows items with a non-empty `next_action`.

These items are ordered by:

1. nearest deadline first
2. higher-priority review state when deadlines tie
3. higher score when both deadline and state tie

This is intentionally deadline-first because the operator's immediate risk is missing a time-sensitive action, not failing to inspect every status bucket evenly.

### Inbox default filters

Opportunity Inbox keeps `new` opportunities visible by default.

The default filter state is:

- `hide archived/no_go = on`
- no forced `review_status` filter
- no forced `shortlisted only`

This preserves discovery of new candidates while removing the least actionable states from the default view.

### Review detail polish

The existing opportunity detail review panel will be improved with:

- a visible current status badge/label
- clearer save success and clear success feedback
- explicit save/clear error messages
- better placeholder/help text for `next_action`
- note guidance that reinforces local-only persistence and export safety

## Data Design

### New Review Board payload

`GET /ops/review-board` returns only safe metadata:

- `status`
- `generated_at`
- `total_reviewed`
- `status_counts`
- `board_groups`
- `next_actions`
- `service_key_exposed = false`
- `real_api_call_attempted = false`

#### `status_counts`

Counts by review state for the board, including at least:

- `new`
- `shortlisted`
- `reviewing`
- `go`
- `hold`
- `no_go`
- `submitted`
- `archived`

Each count is derived only from locally available opportunity items plus review status merge results.

#### `board_groups`

Grouped summaries for the main board sections. Each group contains up to 3-5 top items. Group priority is:

1. `go`
2. `reviewing`
3. `shortlisted`
4. `hold`

Secondary groups may include `no_go`, `submitted`, or `archived`, but the UI should visually de-emphasize them.

Each item summary should stay compact and safe:

- `notice_id`
- `title`
- `review_status`
- `review_status_ko`
- `owner`
- `next_action`
- `deadline`
- `score`
- `bid_priority`

No raw note body, no absolute local path, no secret-bearing config.

#### `next_actions`

This is a flat list of actionable items where `next_action` is present and non-empty.

Each item includes:

- `notice_id`
- `title`
- `review_status`
- `review_status_ko`
- `owner`
- `next_action`
- `deadline`
- `bid_priority`

Private full notes are excluded here as well.

## Service Design

### `app/services/review_board.py`

Add a focused orchestration module with functions along these lines:

- `build_review_board(opportunities, statuses=None)`
- `build_review_status_counts(items)`
- `group_by_review_status(items)`
- `build_next_action_board(items)`

Responsibilities:

- merge/sanitize safe item summaries for the board
- count review statuses
- order groups by operational priority
- filter next-action items to non-empty values only
- sort next-action items by deadline-first rules
- always stamp safe metadata flags

This service should not perform:

- network calls
- `.env` reads beyond existing settings access patterns
- any write other than existing local review status persistence already triggered elsewhere

### `app/services/opportunity_inbox.py`

Keep the inbox service as the authoritative working list, but ensure it cleanly supports the board-linked filter flow and default hiding behavior already chosen for Task 50G.

Potential adjustments:

- make default `hide_archived_no_go` behavior available from the UI state
- preserve review status merged fields needed by both board and inbox

### `app/services/daily_review_pack.py`

Extend, do not rewrite.

Required changes:

- include review workflow summary data that reflects shortlist/review/go states
- include next-action-oriented summaries
- include CSV fields:
  - `review_status_ko`
  - `owner`
  - `next_action`
  - `note_preview`
- exclude full private note body from default markdown and CSV exports
- continue blocking absolute local paths and secret-like substrings

## API Design

### New endpoint

Add:

- `GET /ops/review-board`

This endpoint must:

- operate without any real G2B API call
- use existing local opportunity/review status data only
- return `service_key_exposed = false`
- return `real_api_call_attempted = false`

### Existing endpoints

The following stay behaviorally compatible:

- `GET /ops/opportunity-inbox`
- `GET/POST/DELETE /ops/review-status`
- `GET /ops/daily-review-pack`
- `GET /ops/daily-review-pack/markdown`
- `GET /ops/daily-review-pack/csv`

The goal is to enrich the workflow, not replatform it.

## UI Design

### Files

Update only these UI files:

- `app/ui/templates/dashboard.html`
- `app/ui/static/dashboard.js`
- `app/ui/static/dashboard.css`

### New UI sections

Add a top-level `Review Board` section with:

- status count cards
- grouped top items
- next action list

### Interaction rules

- clicking a status card updates the existing inbox filter controls and reloads Inbox
- board empty states must render explicitly and never leave "Loading" stuck
- the detail panel keeps save/clear actions local-only

### Styling goals

- preserve the current utilitarian operations-dashboard tone
- do not introduce decorative hero/card-heavy marketing patterns
- keep visual density readable for repeated daily use

## Testing Strategy

Use TDD in this order.

### 1. `tests/test_review_status.py`

Add failing tests for:

- review board groups by status
- status counts are correct
- next action board excludes empty `next_action`
- archived/no-go filtering behavior is respected
- opportunity inbox filtering still works with review status-linked views
- review board payload remains local-only and safe

### 2. `tests/test_daily_review_pack.py`

Add failing tests for:

- review status summary appears in the pack
- next action summary reflects local review workflow
- CSV export contains `review_status_ko`, `owner`, `next_action`, `note_preview`
- full note body is excluded from default export
- no secret exposure and no local absolute path leakage

### 3. `tests/test_operations_ui.py`

Add failing tests for:

- Review Board HTML hooks exist
- JS includes filter-link behavior for board cards
- board empty state falls back safely
- detail review panel shows clearer status/save/clear messaging hooks
- no lingering `Loading` expectation

## Documentation Updates

Update these files with concise additions only:

- `README.md`
- `docs/06_OPERATIONS_RUNBOOK.md`
- `docs/07_DEPLOYMENT_HANDOFF.md`
- `docs/08_USABILITY_REVIEW.md`
- `docs/99_DECISION_LOG.md`

Document:

- what Review Board is for
- how shortlist/review/go/hold workflow is used
- how next actions surface daily work
- that exports include safe workflow fields only
- that persistence remains local-only by default
- that no-real behavior remains the default runtime mode

## Validation and Release Flow

### Development repo validation

Run, without enabling any real API gate:

- `ruff check app tests`
- `python -m pytest -q`
- `scripts\\check_real_ops_readiness.ps1`
- `scripts\\validate_real_ops_controlled.ps1`
- `scripts\\smoke_ops_quality_summary.ps1`
- `scripts\\smoke_ops_report_index.ps1`
- `scripts\\check_deploy_readiness.ps1`
- `scripts\\validate_local.ps1`
- `scripts\\run_ops_safe_daily.ps1 -DeployPath D:\\Deploy\\yonlab-g2b-agent-v2-rc13`

### Release candidate

If development validation passes:

- commit on `main`
- push `main`
- create `v0.1.0-rc14`
- deploy fresh to `D:\Deploy\yonlab-g2b-agent-v2-rc14`
- install venv and requirements
- copy `.env` from rc13 deployment safely without printing values
- rerun the no-real validation set on rc14
- run UI/API smoke on port `8019`
- smoke review-board workflow with local review-status POST/GET/DELETE
- update scheduler target to rc14 only if all rc14 checks pass

## Risks and Guardrails

Primary risks:

- board logic drifting from inbox/pack logic
- export fields accidentally including private note body or path-like text
- UI filter linking leaving stale state or empty-state confusion

Guardrails:

- keep grouping/counting logic server-side and tested
- reuse existing sanitization/export safety patterns
- reuse existing Inbox filters instead of inventing a second filter state model
- never call any real G2B API in tests or validation for this task

## Success Criteria

Task 50G is complete when:

- `GET /ops/review-board` exists and is safe
- `/ui` has a top Review Board section
- Review Board cards drive Inbox filtering
- next-action items are visible and deadline-first
- Daily Review Pack reflects review workflow fields
- markdown/CSV exports contain safe review fields only
- full private note body is excluded from default export
- no real API call occurs during implementation validation
- no-secret validation passes
- rc14 fresh deployment validates successfully
- scheduler points to rc14 safe daily only after rc14 passes
