# Review Board Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the Task 50G Review Board workflow to the safe local operations dashboard, expose a safe `/ops/review-board` endpoint, strengthen Daily Review Pack/export behavior, and validate the result through the existing no-real rc14 release flow.

**Architecture:** Reuse the existing local-only workflow built around `review_status`, `opportunity_inbox`, `daily_review_pack`, and the `/ui` dashboard. Add a small server-side orchestration layer in `app/services/review_board.py`, expose it through `app/api/routes.py`, and let the dashboard consume it as a top-level operational summary that drives existing Inbox filters instead of inventing a second working surface.

**Tech Stack:** FastAPI, existing services under `app/services`, plain HTML/CSS/vanilla JS dashboard, pytest with `TestClient`, PowerShell validation scripts, local JSON review-status persistence, SQLite-backed saved ops storage only where already present.

---

## Current Repo Observations

### Current branch and baseline

- Repo path: `D:\Views\yonlab-g2b-agent-v2`
- Current branch: `main`
- Current HEAD at planning time: `94a2c80 docs: add Task 50G review board design spec`
- `main` is ahead of `origin/main` by the design-spec commit only.

### Existing implementation surfaces

- `app/services/review_status.py`
  - owns local JSON review-status persistence
  - already defines the full status vocabulary: `new`, `shortlisted`, `reviewing`, `go`, `hold`, `no_go`, `submitted`, `archived`
  - already merges status metadata into opportunity items
- `app/services/opportunity_inbox.py`
  - builds saved/demo opportunity items
  - already supports filters for `review_status`, `shortlisted_only`, and `hide_archived_no_go`
  - already returns review metadata merged into each item
- `app/services/daily_review_pack.py`
  - already groups by priority, exposes shortlist-related fields, builds markdown/CSV exports, and sanitizes export text
  - already excludes obvious path/service-key leakage
- `app/api/routes.py`
  - already exposes:
    - `GET /ops/review-status...`
    - `GET /ops/opportunity-inbox`
    - `GET /ops/daily-review-pack`
    - `GET /ops/daily-review-pack/markdown`
    - `GET /ops/daily-review-pack/csv`
    - `GET /ops/report-index`
    - `GET /ops/safe-daily-status`
- `app/ui/templates/dashboard.html`
  - already has a top-heavy operational dashboard layout with status, source mode, safe daily, daily review pack, Inbox, and detail panel
- `app/ui/static/dashboard.js`
  - already knows how to:
    - load Inbox, Daily Review Pack, safe daily, runs, recommendations
    - save and clear review status
    - download markdown/CSV exports
  - already uses `loadSection`, `safeText`, and `Promise.allSettled` for safe rendering

### Existing test coverage that should be extended, not replaced

- `tests/test_review_status.py`
  - local-only review-status CRUD
  - inbox merge and shortlist filtering
  - daily review export safety around note/path/secrets
- `tests/test_daily_review_pack.py`
  - pack grouping, markdown/CSV export shape, empty state, safe daily status
- `tests/test_operations_ui.py`
  - `/ui` HTML hooks
  - JS syntax and render safety
  - empty/loading fallback behavior
- `tests/test_real_ops_readiness.py`
  - no-real readiness contract remains safe and offline
- `tests/test_real_ops_runtime_readiness.py`
  - controlled real-call gating remains explicit and offline until confirmed
- `tests/test_smoke_scripts.py`
  - validation and smoke script presence/guardrails remain stable

### Planning implications

1. The new Review Board should be derived from already merged opportunity items, not from raw review-status records alone.
2. The safest insertion point is a new service layer plus one new route.
3. UI work should extend the existing dashboard lifecycle and filter controls rather than introducing a separate client-side store.
4. Export safety and no-real guarantees already have tests; new behavior should attach to those test files instead of scattering new coverage.

## Implementation Assumptions

These assumptions are implied by the Task 50G spec and should be implemented unless changed explicitly later.

1. **Board counts are item-based, not raw-record-based.**
   - `status_counts` should count currently visible opportunity items after review-status merge, not orphaned review-status records for notices absent from saved/demo opportunity data.

2. **`total_reviewed` means items with a non-default active status or any persisted review record.**
   - Proposed default: count items whose merged `review_status` is not `new`, plus any item with `review_status_persisted = true`.

3. **Active-state-first UI means `go`, `reviewing`, `shortlisted`, `hold` are visually primary.**
   - `new`, `submitted`, `no_go`, and `archived` still exist in `status_counts`.

4. **Deadline-first next actions use parsed deadline ascending, with undated items last.**
   - Tie-breakers: active-state priority, then higher score, then stable `notice_id`.

5. **Inbox default behavior remains server-compatible and is applied from the UI.**
   - Proposed default UI state: `hide archived/no_go = on`.
   - Route default stays unchanged unless an implementation step intentionally changes the API default and updates tests.

6. **Board card clicks reuse the existing Inbox filter controls.**
   - Clicking a board card updates `#opportunity-review-filter`, optionally clears conflicting toggles, then calls `loadOpportunityInbox()`.

7. **Default exports remain private-note-safe.**
   - `note_preview` may appear in CSV and pack payloads.
   - full `note` must stay out of default markdown/CSV export content.

## Target User Flow

1. Operator opens `/ui`.
2. At the top of the page, the new Review Board loads:
   - active-state counts
   - top items per active state
   - deadline-first next action list
3. Operator clicks a board card such as `reviewing`.
4. The existing Opportunity Inbox filter controls update to reflect that state.
5. Inbox reloads with matching rows, while still honoring the default hidden `archived/no_go` behavior.
6. Operator clicks `Review` on one item.
7. Opportunity Detail opens with clearer review-status feedback, current status visibility, and better `next_action` guidance.
8. Operator saves or clears local review status.
9. Inbox and Daily Review Pack refresh to reflect the updated workflow state.
10. Daily Review Pack markdown/CSV exports include safe workflow fields (`review_status_ko`, `owner`, `next_action`, `note_preview`) without exposing full note content, paths, or secrets.

## Proposed `/ops/review-board` JSON Contract

```json
{
  "status": "success",
  "generated_at": "2026-06-29T12:00:00+00:00",
  "total_items": 12,
  "total_reviewed": 5,
  "status_counts": {
    "new": 7,
    "shortlisted": 2,
    "reviewing": 1,
    "go": 1,
    "hold": 1,
    "no_go": 0,
    "submitted": 0,
    "archived": 0
  },
  "board_groups": {
    "go": [
      {
        "notice_id": "NOTICE-001",
        "title": "AI support service",
        "review_status": "go",
        "review_status_ko": "go",
        "owner": "YOnLab",
        "next_action": "Prepare final go/no-go note",
        "deadline": "2026-07-01",
        "score": 88,
        "bid_priority": "P1"
      }
    ],
    "reviewing": [],
    "shortlisted": [],
    "hold": [],
    "secondary": {
      "new": [],
      "submitted": [],
      "no_go": [],
      "archived": []
    }
  },
  "next_actions": [
    {
      "notice_id": "NOTICE-001",
      "title": "AI support service",
      "review_status": "go",
      "review_status_ko": "go",
      "owner": "YOnLab",
      "next_action": "Prepare final go/no-go note",
      "deadline": "2026-07-01",
      "bid_priority": "P1",
      "score": 88
    }
  ],
  "service_key_exposed": false,
  "real_api_call_attempted": false
}
```

### Contract notes

- `status`
  - `success` when items exist
  - `empty` when no boardable opportunity data exists
- `total_items`
  - total merged opportunity items used to derive the board
- `total_reviewed`
  - count of items matching the implementation assumption above
- `status_counts`
  - always present with all known keys, even when values are `0`
- `board_groups`
  - primary groups should be `go`, `reviewing`, `shortlisted`, `hold`
  - secondary statuses may be grouped separately to keep the UI compact
- `next_actions`
  - only non-empty actionable items
- `service_key_exposed`
  - always `false`
- `real_api_call_attempted`
  - always `false`

## Data Derivation Approach

### Source of truth

Build Review Board from the same merged opportunity items that power Inbox and Daily Review Pack:

1. call `build_opportunity_inbox(...)`
2. read `payload["items"]`
3. derive Review Board summaries from those merged items

This avoids divergence between Inbox, Pack, and Board.

### Proposed new service

Create `app/services/review_board.py`.

Suggested functions:

- `ACTIVE_REVIEW_BOARD_STATUSES = ("go", "reviewing", "shortlisted", "hold")`
- `SECONDARY_REVIEW_BOARD_STATUSES = ("new", "submitted", "no_go", "archived")`
- `REVIEW_BOARD_STATUS_ORDER = {...}`
- `build_review_board(items: list[dict[str, Any]] | None) -> dict[str, Any]`
- `build_review_status_counts(items: list[dict[str, Any]] | None) -> dict[str, int]`
- `group_by_review_status(items: list[dict[str, Any]] | None) -> dict[str, list[dict[str, Any]]]`
- `build_next_action_board(items: list[dict[str, Any]] | None) -> list[dict[str, Any]]`
- `_safe_board_item(item: dict[str, Any]) -> dict[str, Any]`
- `_review_board_sort_key(item: dict[str, Any]) -> tuple[...]`
- `_next_action_sort_key(item: dict[str, Any]) -> tuple[...]`

### Derivation rules

#### Status counts

- start from merged Inbox items
- default missing status to `new`
- count all statuses in a fixed key set

#### Board groups

- group all items by merged `review_status`
- sort each group by:
  1. earliest deadline
  2. higher score
  3. stable `notice_id`
- truncate each primary group to 3-5 items for UI display

#### Next actions

- include only items where `next_action.strip()` is non-empty
- sort by:
  1. parsed deadline ascending
  2. active-state priority (`go`, `reviewing`, `shortlisted`, `hold`, then others)
  3. descending score
  4. stable `notice_id`

#### Safety

- keep only safe fields
- exclude:
  - full `note`
  - path-like fields
  - raw JSON/raw source
  - any service-key-like substrings

## UI Integration Approach

### Files to modify

- `app/ui/templates/dashboard.html`
- `app/ui/static/dashboard.js`
- `app/ui/static/dashboard.css`

### HTML changes

Insert a new top-level panel before Opportunity Inbox:

- `section.panel.review-board-panel`
- count cards area
- grouped active-state lists
- next action list

Suggested IDs/classes:

- `review-board-title`
- `refresh-review-board`
- `review-board-status`
- `review-board-total-items`
- `review-board-total-reviewed`
- `review-board-cards`
- `review-board-go`
- `review-board-reviewing`
- `review-board-shortlisted`
- `review-board-hold`
- `review-board-next-actions`
- `review-board-empty`
- `opportunity-review-status-badge`
- `opportunity-review-help`

### JavaScript changes

Add new client helpers:

- `loadReviewBoard()`
- `renderReviewBoard(payload)`
- `renderReviewBoardCards(statusCounts)`
- `renderReviewBoardGroup(elementId, items, fallback)`
- `renderNextActionBoard(items)`
- `applyReviewBoardFilter(reviewStatus)`
- `syncInboxDefaultFilters()`
- `renderOpportunityReviewFeedback(payload, mode)`

Expected behavior:

1. `DOMContentLoaded` includes `loadSection("review board", loadReviewBoard, [...])`
2. `refresh-review-board` reloads the board only
3. card click:
   - sets `#opportunity-review-filter`
   - ensures `#opportunity-hide-archived-no-go` defaults to checked
   - reloads Inbox
4. save/clear review status refreshes:
   - Review Board
   - Opportunity Inbox
   - Daily Review Pack

### CSS changes

Add compact operational styling only:

- board cards as low-radius dense cards
- active-state visual emphasis
- scroll-safe grouped lists
- next action list readable on desktop and mobile
- no oversized decorative treatment

## Inbox Filter State Approach

### Existing controls to reuse

Current controls already exist in `dashboard.html`:

- `#opportunity-review-filter`
- `#opportunity-shortlisted-only`
- `#opportunity-hide-archived-no-go`
- `#opportunity-sort`

### Proposed default

Apply on page load in JS:

- `hide archived/no_go = checked`
- no `review_status` selected
- `shortlisted only = unchecked`
- existing `sort = score_desc` remains

### Card-click rules

When clicking an active-state card:

1. set `review_status` to the clicked state
2. clear `shortlisted_only`
3. preserve `hide_archived_no_go = true`
4. leave keyword/source filters as-is
5. call `loadOpportunityInbox()`

### Optional future refinement

Do not add URL query persistence in Task 50I-J unless necessary. Keep this as a later enhancement candidate if operators ask for shareable filtered URLs.

## Daily Review Pack / Export Enhancement Approach

### Existing behavior to preserve

- current priority grouping
- current markdown/CSV endpoints
- current sanitization of local paths and service-key-like text
- no-real behavior

### Planned enhancements

#### `app/services/daily_review_pack.py`

- extend `build_daily_review_pack()` to include a dedicated review workflow summary block
- extend markdown generation to include:
  - active review status summary
  - next-action summary
- extend CSV export row generation to populate:
  - `review_status_ko`
  - `owner`
  - `next_action`
  - `note_preview`

### Export safety rules

- `note_preview` may be exported
- full `note` must not be exported
- no local absolute paths
- no `serviceKey`/`.env` leakage

### Proposed pack additions

Add to pack payload:

- `review_status_summary`
- `next_action_summary`

These can be simple derived summaries to support both dashboard copy and tests.

## Requirement-to-Location Mapping

| Task 50G requirement | Primary implementation location | Primary test location |
|---|---|---|
| `/ui` top Review Board | `app/ui/templates/dashboard.html`, `app/ui/static/dashboard.js`, `app/ui/static/dashboard.css` | `tests/test_operations_ui.py` |
| Click Review Board -> Inbox filter | `app/ui/static/dashboard.js` | `tests/test_operations_ui.py`, `tests/test_review_status.py` |
| Active-state-first display | `app/services/review_board.py`, `dashboard.js` | `tests/test_review_status.py`, `tests/test_operations_ui.py` |
| Deadline-first next action board | `app/services/review_board.py` | `tests/test_review_status.py` |
| Safe `/ops/review-board` | `app/services/review_board.py`, `app/api/routes.py` | `tests/test_review_status.py` |
| Daily Review Pack enhancement | `app/services/daily_review_pack.py` | `tests/test_daily_review_pack.py`, `tests/test_review_status.py` |
| Safe markdown/CSV export | `app/services/daily_review_pack.py` | `tests/test_daily_review_pack.py`, `tests/test_review_status.py` |
| Detail review panel UX polish | `dashboard.html`, `dashboard.js`, `dashboard.css` | `tests/test_operations_ui.py` |
| No-real validation unchanged | no functional change except route/UI additions | `tests/test_real_ops_readiness.py`, `tests/test_real_ops_runtime_readiness.py`, `tests/test_smoke_scripts.py` |
| rc14 deployment flow | docs + existing scripts | manual validation checklist in follow-up task 50M |

## Test Plan

### Unit/API tests

#### `tests/test_review_status.py`

Add:

- `test_review_board_groups_items_by_active_status`
- `test_review_board_status_counts_cover_all_known_states`
- `test_review_board_next_actions_exclude_empty_values_and_sort_by_deadline`
- `test_review_board_api_is_local_only_and_secret_safe`
- `test_opportunity_inbox_default_hide_archived_no_go_behavior` (only if API/UI default changes require it)
- `test_review_board_card_target_status_matches_inbox_filter_contract` (API-side contract expectations only)

#### `tests/test_daily_review_pack.py`

Add:

- `test_daily_review_pack_includes_review_status_summary`
- `test_daily_review_pack_includes_next_action_summary`
- `test_daily_review_csv_populates_safe_review_workflow_fields`
- `test_daily_review_exports_exclude_full_note_body`

#### `tests/test_operations_ui.py`

Add:

- `test_dashboard_contains_review_board_ui_hooks`
- `test_dashboard_js_loads_review_board_endpoint`
- `test_dashboard_js_applies_review_board_filter_to_inbox_controls`
- `test_dashboard_review_panel_has_clearer_status_feedback_hooks`
- extend render helper test to verify Review Board empty-state fallbacks

### No-real and script-level regression checks

No new script files are required by Task 50G itself, but follow-up implementation should re-run:

- `tests/test_real_ops_readiness.py`
- `tests/test_real_ops_runtime_readiness.py`
- `tests/test_smoke_scripts.py`

These guard against accidental real-call enablement and validation-flow regressions.

## Validation Commands

### Development validation

```powershell
Set-Location D:\Views\yonlab-g2b-agent-v2
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check app tests tools
```

### Feature-focused validation during implementation

```powershell
Set-Location D:\Views\yonlab-g2b-agent-v2
.\.venv\Scripts\python.exe -m pytest -q tests\test_review_status.py -s
.\.venv\Scripts\python.exe -m pytest -q tests\test_daily_review_pack.py -s
.\.venv\Scripts\python.exe -m pytest -q tests\test_operations_ui.py -s
```

### No-real operational validation

```powershell
Set-Location D:\Views\yonlab-g2b-agent-v2
.\scripts\check_real_ops_readiness.ps1
.\scripts\validate_real_ops_controlled.ps1
.\scripts\smoke_ops_quality_summary.ps1
.\scripts\smoke_ops_report_index.ps1
.\scripts\check_deploy_readiness.ps1
.\scripts\validate_local.ps1
.\scripts\run_ops_safe_daily.ps1 -DeployPath D:\Deploy\yonlab-g2b-agent-v2-rc13
```

## Release / rc14 Checklist

- [ ] Product code changes complete on `main`
- [ ] `ruff check app tests tools` passes
- [ ] `python -m pytest -q` passes
- [ ] no-real validation scripts pass in dev repo
- [ ] commit created for implementation work
- [ ] push `main`
- [ ] create tag `v0.1.0-rc14`
- [ ] clone fresh deployment to `D:\Deploy\yonlab-g2b-agent-v2-rc14`
- [ ] checkout `v0.1.0-rc14`
- [ ] create `.venv`
- [ ] install requirements
- [ ] copy `.env` safely from rc13 deployment without printing contents
- [ ] run no-real validation set in rc14 deployment
- [ ] run `/ops/opportunity-inbox`, `/ops/review-status`, `/ops/review-board`, `/ops/daily-review-pack`, `/ui` smoke on port `8019`
- [ ] perform review-status functional smoke against rc14
- [ ] promote scheduler target to rc14 only after all rc14 checks pass

## Proposed Follow-up Tasks

### Task 50I: Review Board service and API contract

**Purpose:** Build the new server-side `review_board` service and expose `GET /ops/review-board`.

**Files:**

- Create: `app/services/review_board.py`
- Modify: `app/api/routes.py`
- Test: `tests/test_review_status.py`

**Deliverables:**

- `build_review_board()`
- `build_review_status_counts()`
- `group_by_review_status()`
- `build_next_action_board()`
- `GET /ops/review-board`
- no-real and no-secret guarantees in payload

### Task 50J: Dashboard Review Board UI and Inbox filter linking

**Purpose:** Add the top Review Board section to `/ui` and wire card clicks into the existing Inbox filters.

**Files:**

- Modify: `app/ui/templates/dashboard.html`
- Modify: `app/ui/static/dashboard.js`
- Modify: `app/ui/static/dashboard.css`
- Test: `tests/test_operations_ui.py`

**Deliverables:**

- Review Board panel
- count cards
- grouped lists
- next action list
- click-to-filter behavior
- safe empty states

### Task 50K: Daily Review Pack and export workflow enhancement

**Purpose:** Extend pack summaries and exports with safe review workflow data.

**Files:**

- Modify: `app/services/daily_review_pack.py`
- Test: `tests/test_daily_review_pack.py`
- Regression test: `tests/test_review_status.py`

**Deliverables:**

- review status summary in pack
- next action summary
- CSV fields populated for safe workflow data
- full note still excluded from default markdown/CSV

### Task 50L: Opportunity detail review UX polish and docs updates

**Purpose:** Improve review-status save/clear feedback in the detail panel and update operator-facing docs.

**Files:**

- Modify: `app/ui/templates/dashboard.html`
- Modify: `app/ui/static/dashboard.js`
- Modify: `app/ui/static/dashboard.css`
- Modify: `README.md`
- Modify: `docs/06_OPERATIONS_RUNBOOK.md`
- Modify: `docs/07_DEPLOYMENT_HANDOFF.md`
- Modify: `docs/08_USABILITY_REVIEW.md`
- Modify: `docs/99_DECISION_LOG.md`
- Test: `tests/test_operations_ui.py`

**Deliverables:**

- clearer current-status badge/label
- improved save/clear messages
- updated placeholder/help copy
- concise workflow/runbook documentation

### Task 50M: No-real validation, rc14 tag, fresh deployment, and scheduler promotion

**Purpose:** Validate the completed feature, release `v0.1.0-rc14`, deploy it fresh, and promote the safe-daily scheduler target if all checks pass.

**Files:**

- No new product-code files expected
- Possibly docs-only deployment notes if needed

**Deliverables:**

- full dev validation pass
- `v0.1.0-rc14` tag
- fresh deployment at `D:\Deploy\yonlab-g2b-agent-v2-rc14`
- rc14 UI/API smoke
- rc14 review-status smoke
- scheduler updated to rc14 safe daily target

## Execution Order Recommendation

1. `50I` - server-side contract first
2. `50J` - board UI and Inbox linking
3. `50K` - pack/export enhancements
4. `50L` - review UX polish and docs
5. `50M` - validation, release, deployment, scheduler

This order keeps TDD tight and ensures the UI has a stable API contract before wiring behavior.
