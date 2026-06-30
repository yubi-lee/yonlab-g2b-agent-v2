# rc16 Manual Decision Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement local manual Prepare / Review / Hold / Reject decision persistence and surface the saved decision consistently across Decision Memo, Operations UI, Daily Review Pack, and CSV export.

**Architecture:** Extend the existing local review_status.json persistence path with manual decision fields. Add a single POST route for saving manual decisions, then make the existing read surfaces prefer persisted manual decisions while preserving rc15 defaults when no manual decision exists.

**Tech Stack:** Existing Python app stack, existing test runner, existing local fixture/data patterns, existing Operations UI JavaScript/CSS/HTML patterns, existing PowerShell validation scripts.

---

## 1. Scope

- Add local manual decision persistence for known notice IDs using the existing `review_status.json` file.
- Support only these exact values:
  - `Prepare`
  - `Review`
  - `Hold`
  - `Reject`
- Keep `manual_decision_note` separate from the existing review-status `note`.
- Add one write route:
  - `POST /ops/manual-decision/{notice_id}`
- Make these existing read surfaces prefer the persisted manual decision when present:
  - `GET /ops/decision-memo/{notice_id}`
  - `/ui` Decision Memo panel
  - `GET /ops/daily-review-pack`
  - `GET /ops/daily-review-pack/markdown`
  - `GET /ops/daily-review-pack/csv`
- Preserve the current rc15 generated/default decision behavior when no persisted manual decision exists.
- Keep the entire workflow fixture-first, local-only, deterministic in tests, and free of real API calls.

## 2. Non-goals

- No real G2B API calls.
- No real network calls.
- No `.env` changes.
- No service key or secret exposure.
- No database schema changes.
- No SQLite dependency expansion.
- No new automatic runtime behavior.
- No replacement of the existing review-status workflow.
- No change to rc15 recommendation scoring rules.
- No broad UI redesign.
- No new export format beyond the existing markdown and CSV paths.

## 3. Existing code map

### Persistence and local operator state

- `app/services/review_status.py`
  - Owns `review_status.json` storage with `review_status_storage_path(db_path)`.
  - Defines `ReviewStatusUpdate`.
  - Defines current local-only CRUD helpers:
    - `build_default_review_status()`
    - `list_review_statuses()`
    - `get_review_status()`
    - `save_review_status()`
    - `delete_review_status()`
    - `merge_review_statuses()`
  - Sanitizes persisted text through `_sanitize_local_text()`.

- `tests/test_review_status.py`
  - Covers local-only CRUD behavior for `/ops/review-status/{notice_id}`.
  - Verifies invalid review-status values fail with `422`.
  - Verifies local-only safety and export-safe note handling.
  - Already uses temporary `review_status.json` storage under `tmp_path`.

### Decision Memo backend

- `app/services/decision_memo.py`
  - Builds the rc15 Decision Memo payload through:
    - `build_empty_decision_memo()`
    - `build_decision_memo()`
    - `_recommended_decision()`
  - Current response includes:
    - `recommended_decision.value`
    - `recommended_decision.rationale`
    - `export_blocks.markdown`
    - `export_blocks.short_summary`
  - Current behavior is generated-only with no persisted manual override.

- `tests/test_ops_decision_memo.py`
  - Covers known local notice success payload.
  - Covers unknown notice safe `not_found`.
  - Covers no-real guarantee by blocking `G2BClient`.

### API routes

- `app/api/routes.py`
  - Already exposes:
    - `GET /ops/decision-memo/{notice_id}`
    - `GET /ops/review-status`
    - `GET /ops/review-status/{notice_id}`
    - `POST /ops/review-status/{notice_id}`
    - `DELETE /ops/review-status/{notice_id}`
    - `GET /ops/opportunity-inbox/{notice_id}`
    - `GET /ops/daily-review-pack`
    - `GET /ops/daily-review-pack/markdown`
    - `GET /ops/daily-review-pack/csv`
  - Uses `get_opportunity_detail()` as the safe detail source for known local notice IDs.

### Daily Review Pack and CSV export

- `app/services/daily_review_pack.py`
  - Builds the pack payload through `build_daily_review_pack()`.
  - Builds the Decision Memo summary through `build_decision_memo_summary()`.
  - Builds markdown through `build_daily_review_markdown()`.
  - Builds CSV rows and text through:
    - `build_daily_review_csv_rows()`
    - `build_daily_review_csv()`
  - Current CSV field list is fixed in `CSV_FIELDS`.
  - Existing Decision Memo export fields already include:
    - `decision_memo_decision`
    - `decision_memo_rationale`
    - `decision_memo_fit_summary`
    - `decision_memo_risk_summary`
    - `decision_memo_deadline_urgency`
    - `decision_memo_next_action`
    - `decision_memo_preparation_actions`
    - `decision_memo_required_documents`
    - `decision_memo_short_summary`

- `tests/test_daily_review_pack.py`
  - Covers pack structure, markdown sections, CSV structure, empty state, and Decision Memo summary behavior.
  - Already asserts the presence of:
    - `## Decision Memo Summary`
    - `## Decision Memo Details`
    - `decision_memo_decision`
    - `decision_memo_fit_summary`

### Operations UI

- `app/ui/templates/dashboard.html`
  - Already contains the rc15 Decision Memo panel.
  - Existing Decision Memo DOM ids:
    - `decision-memo-notice-id`
    - `load-decision-memo`
    - `open-selected-decision-memo`
    - `decision-memo-status`
    - `decision-memo-decision`
    - `decision-memo-rationale`
    - `decision-memo-summary`
    - `decision-memo-fit-summary`
    - `decision-memo-risk-summary`
    - `decision-memo-next-action`
    - `decision-memo-preparation-actions`
    - `decision-memo-required-documents`
    - `decision-memo-copy-block`

- `app/ui/static/dashboard.js`
  - Already loads Decision Memo data with:
    - `loadDecisionMemo()`
    - `loadDecisionMemoFromInput()`
    - `openSelectedDecisionMemo()`
    - `renderDecisionMemo()`
    - `emptyDecisionMemo()`
  - Already has local-only save flow patterns through:
    - `saveOpportunityReviewStatus()`
    - `clearOpportunityReviewStatus()`
  - Already refreshes:
    - Opportunity Inbox
    - Review Board
    - Daily Review Pack

- `tests/test_operations_ui.py`
  - Verifies `/ui` HTML hooks.
  - Verifies dashboard JS parses.
  - Verifies Decision Memo hooks and Review Board click-through behavior.
  - Uses Node-based JS checks for DOM behavior without real browser/network dependence.

### Related safe local detail sources

- `app/services/opportunity_inbox.py`
  - Exposes `get_opportunity_detail()` used by the rc15 Decision Memo route.
  - Already merges review-status data into saved/demo opportunity items.

- `tests/test_opportunity_inbox.py`
  - Existing inbox behavior regression coverage.

## 4. Target data model

### Existing persisted record shape

`review_status.json` currently stores per-notice records keyed by `notice_id` under `items`.

Current per-notice fields in `app/services/review_status.py` are:

- `notice_id`
- `source_run_id`
- `review_status`
- `owner`
- `note`
- `next_action`
- `updated_at`

### rc16 persisted fields to add

Add these fields to each per-notice record without removing any existing fields:

- `manual_decision`
- `manual_decision_note`
- `manual_decision_updated_at`

### Value rules

- `manual_decision`
  - allowed values:
    - `Prepare`
    - `Review`
    - `Hold`
    - `Reject`
  - any other value must be rejected with `422`
- `manual_decision_note`
  - stored as a string
  - empty string when omitted
  - empty string when explicitly submitted as `""`
  - sanitized through the same local-safe text sanitizer used for other local text fields
- `manual_decision_updated_at`
  - updated on every successful manual-decision save

### Default read shape

When a notice has no persisted manual decision, read-path helpers should return:

```json
{
  "manual_decision": {
    "decision": "",
    "note": "",
    "updated_at": "",
    "persisted": false
  }
}
```

This keeps the payload shape stable while leaving the active decision sourced from rc15 generated logic.

### Implementation assumption

rc16 should not add a second file such as `manual_decision.json`. The manual decision fields belong inside the existing `review_status.json` record because that is already the local operator-owned state store.

## 5. API contract

### New route

- `POST /ops/manual-decision/{notice_id}`

### Request body

```json
{
  "decision": "Prepare",
  "note": "Strong fit and ready for proposal preparation."
}
```

### Success response

```json
{
  "status": "success",
  "notice_id": "G2B-SAMPLE-2026-001",
  "manual_decision": {
    "decision": "Prepare",
    "note": "Strong fit and ready for proposal preparation.",
    "updated_at": "2026-06-30T12:00:00+00:00",
    "persisted": true
  },
  "service_key_exposed": false,
  "real_api_call_attempted": false
}
```

### Invalid decision response

- HTTP status: `422`
- Expected reason:
  - decision is outside the exact enum
  - lowercase aliases are invalid
  - Korean aliases are invalid
  - extra values are invalid

Example invalid request:

```json
{
  "decision": "prepare",
  "note": "invalid lowercase alias"
}
```

### Unknown notice response

- HTTP status: `200`
- Must follow the existing rc15 safe `not_found` pattern already used by `GET /ops/decision-memo/{notice_id}`.
- Must not create a `review_status.json` entry.

Expected safe response shape:

```json
{
  "status": "not_found",
  "notice_id": "UNKNOWN-NOTICE-ID",
  "manual_decision": {
    "decision": "",
    "note": "",
    "updated_at": "",
    "persisted": false
  },
  "service_key_exposed": false,
  "real_api_call_attempted": false
}
```

### Decision Memo response addition

`GET /ops/decision-memo/{notice_id}` should keep the existing rc15 payload shape and add a stable `manual_decision` block:

```json
{
  "manual_decision": {
    "decision": "Hold",
    "note": "Wait for team capacity confirmation.",
    "updated_at": "2026-06-30T12:10:00+00:00",
    "persisted": true
  }
}
```

When `manual_decision.persisted` is `true`:

- `recommended_decision.value` must equal the persisted manual decision.
- `recommended_decision.rationale` must use:
  - the persisted `manual_decision.note` when non-empty, otherwise
  - a deterministic override explanation such as `Manual operator decision saved in local workflow.`

## 6. Decision precedence rules

1. Resolve the known notice detail through the existing safe local path:
   - `get_opportunity_detail(db_path=..., notice_id=...)`
2. If the notice detail is missing:
   - return the existing safe `not_found` Decision Memo
   - manual decision save route must also return safe `not_found`
3. If a persisted `manual_decision` exists for the same notice:
   - it becomes the active decision for:
     - Decision Memo response
     - Decision Memo UI summary
     - Daily Review Pack markdown
     - Daily Review Pack CSV
4. If no persisted `manual_decision` exists:
   - keep the current rc15 generated/default decision behavior unchanged
5. `manual_decision_note` does not replace the existing review-status `note`.
   - review note remains review workflow context
   - manual decision note remains final decision rationale
6. Saving a manual decision for the same `notice_id` overwrites only:
   - `manual_decision`
   - `manual_decision_note`
   - `manual_decision_updated_at`
7. Saving a manual decision must preserve existing review-status fields:
   - `review_status`
   - `owner`
   - `note`
   - `next_action`
   - `source_run_id`
   - `updated_at`

## 7. Test plan

### Persistence tests

Add storage-level and route-level assertions proving:

- each valid value saves:
  - `Prepare`
  - `Review`
  - `Hold`
  - `Reject`
- overwrite works:
  - save `Prepare`
  - save `Review`
  - persisted result becomes `Review`
- `manual_decision_note` stays separate from review-status `note`
- omitted note becomes `""`
- explicit empty-string note remains `""`
- invalid decision returns `422`
- unknown notice does not create a record

### Decision Memo tests

Add assertions proving:

- saved manual decision appears in `manual_decision.persisted`
- saved manual decision overrides `recommended_decision.value`
- saved note overrides `recommended_decision.rationale` when non-empty
- rc15 fallback behavior remains when no saved manual decision exists
- unknown notice still returns rc15-safe `not_found`

### Daily Review Pack tests

Add assertions proving:

- Decision Memo Summary still exists
- Decision Memo Details still exists
- persisted manual decision appears in the memo summary/detail output
- when no persisted decision exists, output still matches rc15 generated/default behavior

### CSV tests

Add assertions proving:

- `decision_memo_decision` remains present
- `decision_memo_fit_summary` remains present
- `decision_memo_decision` reflects the persisted manual decision when present
- no local paths or secrets leak
- free-text private review note remains excluded

### UI tests

Add assertions proving:

- Decision Memo panel contains visible:
  - `Prepare`
  - `Review`
  - `Hold`
  - `Reject`
- Decision Memo panel contains:
  - manual decision note input
  - manual decision save button
  - local-only save status message
- JS contains the `POST /ops/manual-decision/` save hook
- after a simulated save, the Decision Memo area refreshes
- Review Board click -> Decision Memo load still works
- selected Opportunity -> Decision Memo load still works

### No-real safety tests

Keep or extend assertions proving:

- `real_api_call_attempted=false`
- `real_network_call_attempted=false`
- `service_key_exposed=false`

## 8. Implementation tasks

### Task 1: Persistence tests and data model

**Goal:** Add failing tests that lock the rc16 persistence behavior before changing implementation.

**Files to modify/create:**
- Modify: `tests/test_review_status.py`

**Test file(s):**
- `tests/test_review_status.py`

**Specific test cases:**
- `test_manual_decision_persists_all_valid_values_locally`
- `test_manual_decision_overwrites_previous_value_and_updates_timestamp`
- `test_manual_decision_note_is_separate_from_review_note`
- `test_manual_decision_defaults_note_to_empty_string`

**Implementation steps:**
- [ ] Add a test that saves a normal review status first, then checks the review note remains unchanged after manual decision saves.
- [ ] Add a test that posts the four valid values to the new planned route:
  - `Prepare`
  - `Review`
  - `Hold`
  - `Reject`
- [ ] Add a test that inspects the generated `review_status.json` file directly and asserts:
  - `manual_decision` is written
  - `manual_decision_note` is written
  - `manual_decision_updated_at` is written
- [ ] Add a test that saves one decision twice for the same `notice_id` and verifies the second value replaces the first.
- [ ] Add a test that omits `note` and verifies the persisted value is `""`.
- [ ] Add a test that saves `note=""` and verifies the persisted value remains `""`.

**Validation command(s):**
- `python -m pytest -q tests/test_review_status.py -k manual_decision`

**Commit message recommendation:**
- `test: add rc16 manual decision persistence coverage`

### Task 2: Persistence implementation

**Goal:** Extend `review_status.json` handling to support manual decision fields without breaking existing review-status behavior.

**Files to modify/create:**
- Modify: `app/services/review_status.py`

**Test file(s):**
- `tests/test_review_status.py`

**Specific test cases:**
- Task 1 tests must pass without changing existing review-status tests.

**Implementation steps:**
- [ ] Add a new exact enum type in `app/services/review_status.py`:
  - `ManualDecisionValue = Literal["Prepare", "Review", "Hold", "Reject"]`
- [ ] Add a new Pydantic payload model:
  - `ManualDecisionUpdate`
  - fields:
    - `decision: ManualDecisionValue`
    - `note: str = Field(default="", max_length=1200)`
- [ ] Extend `build_default_review_status()` to include:
  - `manual_decision`
  - `manual_decision_note`
  - `manual_decision_updated_at`
  - `manual_decision_persisted`
- [ ] Extend `_record_response()` so read responses always expose the manual decision fields in a stable shape.
- [ ] Add a new helper:
  - `save_manual_decision(db_path: str | Path, notice_id: str, payload: ManualDecisionUpdate, *, now: datetime | None = None) -> dict[str, Any]`
- [ ] In `save_manual_decision()`:
  - load the existing record if present
  - preserve review-status fields
  - overwrite only manual decision fields
  - set `manual_decision_note` to `payload.note.strip()`
  - set `manual_decision_updated_at` to a deterministic ISO timestamp
- [ ] Add a timestamp helper or `now` injection path so tests can assert overwrite ordering without flaky second-level timing.
- [ ] Keep `_load_records()` and `_save_records()` backwards compatible when `review_status.json` does not yet exist.

**Validation command(s):**
- `python -m pytest -q tests/test_review_status.py`
- `python -m ruff check app/services/review_status.py tests/test_review_status.py`

**Commit message recommendation:**
- `feat: extend review status storage with manual decision fields`

### Task 3: Manual decision API tests

**Goal:** Add failing API tests for the new manual-decision write route and its Decision Memo integration.

**Files to modify/create:**
- Modify: `tests/test_ops_decision_memo.py`
- Modify: `tests/test_review_status.py`

**Test file(s):**
- `tests/test_ops_decision_memo.py`
- `tests/test_review_status.py`

**Specific test cases:**
- `test_manual_decision_api_accepts_each_valid_value_for_known_notice`
- `test_manual_decision_api_rejects_invalid_decision_with_422`
- `test_manual_decision_api_returns_safe_not_found_for_unknown_notice`
- `test_manual_decision_save_then_decision_memo_read_reflects_override`

**Implementation steps:**
- [ ] In `tests/test_ops_decision_memo.py`, add a known-notice round-trip test using fixture-backed saved ops data:
  - run fixture recommendations
  - get a known `notice_id`
  - `POST /ops/manual-decision/{notice_id}`
  - `GET /ops/decision-memo/{notice_id}`
  - assert the saved decision is returned
- [ ] Add one explicit invalid-value test with `decision="prepare"` and assert `422`.
- [ ] Add one explicit unknown-ID test with `UNKNOWN-NOTICE-ID` and assert:
  - route returns safe `not_found`
  - no `review_status.json` entry is created
- [ ] Add a no-real guard test that monkeypatches `routes.G2BClient` to a failing stub and proves manual decision save does not construct it.

**Validation command(s):**
- `python -m pytest -q tests/test_ops_decision_memo.py tests/test_review_status.py -k manual_decision`

**Commit message recommendation:**
- `test: add rc16 manual decision api coverage`

### Task 4: Manual decision API implementation

**Goal:** Add the new write route using the existing local-safe route conventions.

**Files to modify/create:**
- Modify: `app/api/routes.py`
- Modify: `app/services/review_status.py`

**Test file(s):**
- `tests/test_ops_decision_memo.py`
- `tests/test_review_status.py`

**Specific test cases:**
- Task 3 tests must pass.

**Implementation steps:**
- [ ] Import `ManualDecisionUpdate` and `save_manual_decision` into `app/api/routes.py`.
- [ ] Add:
  - `@router.post("/ops/manual-decision/{notice_id}")`
- [ ] Before saving, validate the notice exists through:
  - `get_opportunity_detail(db_path=settings.yonlab_storage_db_path, notice_id=notice_id)`
- [ ] If no detail exists:
  - return a safe `not_found` payload
  - do not call `save_manual_decision()`
- [ ] If the detail exists:
  - call `save_manual_decision()`
  - return the saved state with:
    - `status`
    - `notice_id`
    - `manual_decision`
    - `service_key_exposed`
    - `real_api_call_attempted`
- [ ] Preserve the current no-real behavior by keeping the route local-only and free of any G2B client construction.

**Validation command(s):**
- `python -m pytest -q tests/test_ops_decision_memo.py tests/test_review_status.py`
- `python -m ruff check app/api/routes.py app/services/review_status.py tests/test_ops_decision_memo.py tests/test_review_status.py`

**Commit message recommendation:**
- `feat: add manual decision write route`

### Task 5: Decision Memo integration

**Goal:** Make the Decision Memo read path prefer persisted manual decisions while keeping rc15 fallback behavior intact.

**Files to modify/create:**
- Modify: `app/services/decision_memo.py`
- Modify: `app/api/routes.py`
- Modify: `tests/test_ops_decision_memo.py`

**Test file(s):**
- `tests/test_ops_decision_memo.py`

**Specific test cases:**
- `test_decision_memo_exposes_manual_decision_block`
- `test_decision_memo_recommended_decision_uses_persisted_manual_value`
- `test_decision_memo_uses_generated_default_when_manual_decision_missing`

**Implementation steps:**
- [ ] Add a helper in `app/services/review_status.py` for reading the manual decision portion of a record in a normalized shape.
- [ ] In `app/api/routes.py`, after resolving `detail` for `ops_decision_memo()`, merge in the local manual decision state before building the response, or pass the manual decision state into `build_decision_memo()`.
- [ ] Update `build_empty_decision_memo()` to include an empty `manual_decision` block.
- [ ] Update `build_decision_memo()` to include a `manual_decision` block on all responses.
- [ ] Update the active `recommended_decision` calculation:
  - use persisted manual value when `manual_decision.persisted` is `true`
  - use persisted note as rationale when non-empty
  - otherwise keep the rc15 generated decision and rationale

**Validation command(s):**
- `python -m pytest -q tests/test_ops_decision_memo.py`
- `python -m ruff check app/services/decision_memo.py app/api/routes.py tests/test_ops_decision_memo.py`

**Commit message recommendation:**
- `feat: prefer persisted manual decision in decision memo`

### Task 6: Operations UI

**Goal:** Add visible manual decision controls to the existing Decision Memo panel and wire them to the new local-only API.

**Files to modify/create:**
- Modify: `app/ui/templates/dashboard.html`
- Modify: `app/ui/static/dashboard.js`
- Modify: `tests/test_operations_ui.py`

**Test file(s):**
- `tests/test_operations_ui.py`

**Specific test cases:**
- `test_dashboard_contains_manual_decision_controls_and_save_hook`
- `test_dashboard_manual_decision_save_flow_refreshes_decision_memo`
- `test_dashboard_review_board_click_still_loads_decision_memo_after_rc16_changes`

**Implementation steps:**
- [ ] In `dashboard.html`, add to the existing Decision Memo panel:
  - four decision buttons:
    - `Prepare`
    - `Review`
    - `Hold`
    - `Reject`
  - one note input or textarea
  - one save button
  - one local-only message element
- [ ] Use explicit DOM ids in the plan and implementation:
  - `decision-memo-manual-prepare`
  - `decision-memo-manual-review`
  - `decision-memo-manual-hold`
  - `decision-memo-manual-reject`
  - `decision-memo-manual-note`
  - `save-manual-decision`
  - `decision-memo-manual-message`
- [ ] In `dashboard.js`, extend `state` with the currently selected manual decision value.
- [ ] Add helpers:
  - `selectManualDecision(value)`
  - `saveManualDecision()`
  - `renderManualDecision(payload)`
- [ ] `saveManualDecision()` should:
  - require `state.currentDecisionMemoId`
  - POST to `/ops/manual-decision/{notice_id}`
  - send `{ decision, note }`
  - refresh the Decision Memo through `loadDecisionMemo(noticeId)`
  - refresh Daily Review Pack through `loadDailyReviewPack()`
- [ ] Preserve existing hooks:
  - Review Board item click still loads Decision Memo
  - selected Opportunity still opens Decision Memo

**Validation command(s):**
- `python -m pytest -q tests/test_operations_ui.py`
- `python -m ruff check app/ui/static/dashboard.js tests/test_operations_ui.py`

**Commit message recommendation:**
- `feat: add manual decision controls to decision memo ui`

### Task 7: Daily Review Pack integration

**Goal:** Ensure markdown and pack payloads reflect the persisted manual decision while preserving rc15 defaults when absent.

**Files to modify/create:**
- Modify: `app/services/daily_review_pack.py`
- Modify: `tests/test_daily_review_pack.py`
- Modify: `tests/test_review_status.py`

**Test file(s):**
- `tests/test_daily_review_pack.py`
- `tests/test_review_status.py`

**Specific test cases:**
- `test_daily_review_pack_uses_persisted_manual_decision_in_decision_memo_summary`
- `test_daily_review_markdown_contains_persisted_manual_decision`
- `test_daily_review_pack_preserves_rc15_generated_decision_when_no_manual_override_exists`

**Implementation steps:**
- [ ] Keep `build_decision_memo_summary()` as the pack source of truth for Decision Memo export data.
- [ ] Ensure the summary reads the updated `build_decision_memo()` payload so `recommended_decision` already reflects the override.
- [ ] In markdown output, preserve:
  - `## Decision Memo Summary`
  - `## Decision Memo Details`
- [ ] In detail lines, ensure the visible decision and rationale reflect the manual override when present.
- [ ] Do not add any new real-network or storage side effects.

**Validation command(s):**
- `python -m pytest -q tests/test_daily_review_pack.py tests/test_review_status.py -k decision_memo`
- `python -m ruff check app/services/daily_review_pack.py tests/test_daily_review_pack.py tests/test_review_status.py`

**Commit message recommendation:**
- `feat: reflect manual decision in daily review pack`

### Task 8: CSV export integration

**Goal:** Make the existing CSV export fields reflect persisted manual decisions without adding unnecessary new export surface.

**Files to modify/create:**
- Modify: `app/services/daily_review_pack.py`
- Modify: `tests/test_daily_review_pack.py`

**Test file(s):**
- `tests/test_daily_review_pack.py`

**Specific test cases:**
- `test_daily_review_csv_uses_persisted_manual_decision_value`
- `test_daily_review_csv_preserves_existing_decision_memo_columns`
- `test_daily_review_csv_does_not_export_manual_review_note_or_local_paths`

**Implementation steps:**
- [ ] Keep the current `CSV_FIELDS` list unchanged unless a strict need emerges during implementation.
- [ ] Ensure `decision_memo_decision` uses the value from the updated Decision Memo summary.
- [ ] Keep `decision_memo_fit_summary` unchanged.
- [ ] Keep private free-text note exclusion behavior:
  - do not export the full review note
  - do not add `manual_decision_note` as a CSV column in rc16
- [ ] Preserve formula escaping and path redaction behavior.

**Validation command(s):**
- `python -m pytest -q tests/test_daily_review_pack.py -k csv`
- `python -m ruff check app/services/daily_review_pack.py tests/test_daily_review_pack.py`

**Commit message recommendation:**
- `feat: reflect manual decision in daily review csv`

### Task 9: Full validation and decision log

**Goal:** Run the full no-real validation gate and then record the rc16 result in the decision log.

**Files to modify/create:**
- Modify: `docs/99_DECISION_LOG.md`

**Test file(s):**
- Full suite only; no new tests in this task.

**Specific test cases:**
- Full regression pass across app, tests, and scripts.
- Explicit smoke proving repeated manual-decision replacement works.

**Implementation steps:**
- [ ] Run the full validation commands listed in section 9 below.
- [ ] Run the explicit smoke checks listed in section 9 below.
- [ ] Only after all checks pass, update `docs/99_DECISION_LOG.md` with:
  - rc16 manual decision persistence scope
  - no-real confirmation
  - release-safe summary
- [ ] Do not update the decision log before validation passes.

**Validation command(s):**
- `python -m pytest -q`
- `python -m ruff check app tests`
- `powershell -ExecutionPolicy Bypass -File scripts/check_deploy_readiness.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/validate_local.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/validate_ops_package.ps1`

**Commit message recommendation:**
- `docs: record rc16 manual decision persistence validation`

## 9. Validation commands

Run from:

`D:\Views\yonlab-g2b-agent-v2`

### Required full validation

- `python -m pytest -q`
- `python -m ruff check app tests`
- `powershell -ExecutionPolicy Bypass -File scripts/check_deploy_readiness.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/validate_local.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/validate_ops_package.ps1`

### Required focused validation during development

- `python -m pytest -q tests/test_review_status.py`
- `python -m pytest -q tests/test_ops_decision_memo.py`
- `python -m pytest -q tests/test_daily_review_pack.py`
- `python -m pytest -q tests/test_operations_ui.py`

### Required explicit smoke checks

- `GET /ops/decision-memo/G2B-SAMPLE-2026-001` returns success.
- `POST /ops/manual-decision/G2B-SAMPLE-2026-001` with `Prepare` succeeds.
- Re-read `GET /ops/decision-memo/G2B-SAMPLE-2026-001` and confirm `Prepare` is present.
- `POST Review` and confirm it replaces `Prepare`.
- `POST Hold` and confirm it replaces `Review`.
- `POST Reject` and confirm it replaces `Hold`.
- Invalid decision returns `4xx`.
- `UNKNOWN-NOTICE-ID` returns safe `not_found`.
- `/ui` returns HTTP `200`.
- UI contains visible `Prepare / Review / Hold / Reject` controls.
- UI JS contains the `POST /ops/manual-decision` save hook.
- Daily Review Pack markdown contains:
  - `Decision Memo Summary`
  - `Decision Memo Details`
  - the persisted manual decision
- CSV export contains:
  - `decision_memo_decision`
  - `decision_memo_fit_summary`
  - the persisted manual decision
- `real_api_call_attempted=false`
- `real_network_call_attempted=false`
- `service_key_exposed=false`

## 10. Release notes / decision log update

- Update only `docs/99_DECISION_LOG.md` after the full validation gate passes.
- Record:
  - rc16 scope
  - the decision to extend `review_status.json`
  - the exact manual decision enum
  - the no-real validation result
  - the fact that rc15 generated/default behavior remains the fallback path when no manual decision exists
- Do not record rc16 as complete before:
  - full pytest passes
  - full ruff passes
  - deploy readiness passes
  - local validation passes
  - ops package validation passes

## 11. Self-review checklist

- [ ] The plan uses exact repository paths that exist today or are intentionally proposed as new files.
- [ ] The plan does not rely on `D:\Views\yonlab-bid-agent`.
- [ ] The plan keeps manual decision persistence inside `review_status.json`.
- [ ] The plan keeps `manual_decision_note` separate from the existing review note.
- [ ] The plan adds only one write API route: `POST /ops/manual-decision/{notice_id}`.
- [ ] The plan preserves rc15 generated/default decision behavior when no manual decision exists.
- [ ] The plan keeps the workflow local-only and no-real.
- [ ] The plan covers Decision Memo, UI, Daily Review Pack, and CSV export.
- [ ] The plan includes explicit invalid-value and unknown-notice handling.
- [ ] The plan includes the required full validation commands.
- [ ] The plan includes the required explicit smoke checks.
- [ ] The plan postpones `docs/99_DECISION_LOG.md` updates until after validation succeeds.
