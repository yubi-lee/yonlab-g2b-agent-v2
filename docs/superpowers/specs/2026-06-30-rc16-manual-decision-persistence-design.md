# rc16 Manual Decision Persistence Design

## Goal

Add a narrow rc16 vertical slice that lets an operator save a manual bid decision for a
known notice and have that decision appear consistently across the safe local operations
workflow.

Supported manual decision values:

- `Prepare`
- `Review`
- `Hold`
- `Reject`

This workflow must remain local-only, deterministic enough for tests, and must not call the
real G2B API.

## Scope

This design covers:

- local persistence for manual decision overrides
- a safe API route for saving manual decisions
- Decision Memo read-path integration
- Decision Memo UI controls and save flow
- Daily Review Pack markdown integration
- CSV export integration
- no-real regression coverage

This design does not cover:

- authentication or multi-user workflow
- remote storage
- automatic decision generation changes
- replacing rc15 Review Board, Opportunity Inbox, or review status behavior
- real G2B API execution

## Current Repo Observations

The repository already has the right local-safe building blocks for this feature:

1. `app/services/review_status.py`
   - already persists local operator-owned state in `review_status.json`
   - already sanitizes secret-like text and returns deterministic local-safe payloads
2. `app/services/decision_memo.py`
   - already builds the Decision Memo payload and generated recommendation value
3. `app/services/daily_review_pack.py`
   - already derives Decision Memo summary and export fields from the Decision Memo builder
4. `app/ui/templates/dashboard.html`
   - already contains the Decision Memo panel
5. `app/ui/static/dashboard.js`
   - already loads Decision Memo payloads and connects Review Board and selected opportunity
     flows into the Decision Memo panel
6. `app/api/routes.py`
   - already exposes safe `/ops/decision-memo/{notice_id}` and local review-status routes

That means rc16 should extend existing local operator-state patterns rather than introduce a
second persistence system.

## Problem Statement

rc15 shows a generated Decision Memo, but the operator cannot save a manual final decision.

This leaves a workflow gap:

- the app can recommend `Prepare` or `Review`
- the operator can see the memo and export it
- but the operator cannot persist a human override such as `Hold` or `Reject`
- and the exported artifacts cannot reflect a saved human decision consistently

rc16 should close that gap without broad refactoring.

## Approaches Considered

### Approach 1: Extend `review_status.json`

Store manual decision fields alongside existing local review-status data.

Pros:

- smallest vertical slice
- reuses existing local JSON storage pattern
- reuses existing sanitization and persistence tests
- keeps all operator-owned local state keyed by `notice_id` in one file

Cons:

- review status and decision data share one persistence record

### Approach 2: Add `manual_decision.json`

Create a second local JSON store only for manual decisions.

Pros:

- clearer separation between review-state and decision-state concerns

Cons:

- more plumbing for rc16
- more merge logic
- more test surface for little operator value in this release

### Approach 3: Store manual decisions in SQLite

Pros:

- future-friendly structured persistence

Cons:

- too large for rc16
- changes persistence architecture more than this task requires

## Chosen Approach

Use **Approach 1**: extend `review_status.json`.

Also store a **separate manual decision note** instead of reusing the existing review note.

Why:

- it keeps the feature small
- it avoids duplicating local persistence patterns
- it keeps review notes and final decision rationale distinct
- it lets Daily Review Pack and CSV read one merged operator state source

## Persistence Design

File:

- derived from the existing `review_status_storage_path(db_path)`
- still stored beside the local ops DB path as `review_status.json`

Per-notice persisted fields added:

- `manual_decision`
- `manual_decision_note`
- `manual_decision_updated_at`

Existing review-status fields remain unchanged.

### Validation rules

- `manual_decision` must be one of:
  - `Prepare`
  - `Review`
  - `Hold`
  - `Reject`
- `manual_decision_note` is optional
- `manual_decision_note` should have a bounded length similar to other local text fields
- all persisted note text must pass the existing local sanitization rules

### Default state

If no manual decision exists for a notice:

- `manual_decision` is absent or empty internally
- response payloads should expose either:
  - a `persisted=false` manual-decision block, or
  - the generated Decision Memo value as the active decision while keeping manual-decision
    metadata empty

The generated rc15 behavior must remain the fallback path.

## API Design

### New route

- `POST /ops/manual-decision/{notice_id}`

Request body:

```json
{
  "decision": "Prepare",
  "note": "Strong fit and ready for proposal preparation."
}
```

Response shape:

```json
{
  "notice_id": "G2B-SAMPLE-2026-001",
  "decision": "Prepare",
  "note": "Strong fit and ready for proposal preparation.",
  "updated_at": "2026-06-30T10:00:00+00:00",
  "persisted": true,
  "service_key_exposed": false,
  "real_api_call_attempted": false
}
```

### Behavior rules

- unknown notice id:
  - return a safe `not_found` style response aligned with rc15 Decision Memo semantics
  - do not create a persisted record for an unknown notice
- invalid decision:
  - return a clear `4xx`
- valid save:
  - persist the decision
  - return the persisted decision state

### Optional read helper

A dedicated `GET /ops/manual-decision/{notice_id}` route is not required for rc16.

Reason:

- the main user-facing read path is `/ops/decision-memo/{notice_id}`
- the UI can refresh from the Decision Memo endpoint after save
- keeping rc16 to one new write route avoids unnecessary surface area

## Decision Memo Integration

The rc15 generated decision remains the base layer.

rc16 adds a manual override layer:

1. build generated Decision Memo as rc15 already does
2. read persisted manual decision for the same `notice_id`
3. if a manual decision exists:
   - expose it as the active Decision Memo decision value
   - preserve the generated decision as optional context if useful internally
4. if no manual decision exists:
   - preserve the current generated/default behavior exactly

### Expected response additions

Decision Memo payload should include a stable manual-decision block such as:

```json
{
  "manual_decision": {
    "decision": "Hold",
    "note": "Wait for team capacity confirmation.",
    "updated_at": "2026-06-30T10:00:00+00:00",
    "persisted": true
  }
}
```

Active decision behavior:

- `recommended_decision.value` should reflect the persisted manual decision when present
- `recommended_decision.rationale` should reflect the manual note when present, otherwise a
  safe deterministic override explanation

This keeps downstream consumers simple because they can continue reading the existing
Decision Memo decision field.

## UI Design

Location:

- existing Decision Memo panel in `/ui`

New controls:

- `Prepare` button
- `Review` button
- `Hold` button
- `Reject` button
- one note input or textarea for manual decision rationale
- one save button

### UI flow

1. operator opens a known Decision Memo
2. operator chooses one of the four decision buttons
3. operator optionally enters a manual decision note
4. UI posts to `POST /ops/manual-decision/{notice_id}`
5. on success:
   - UI refreshes the Decision Memo from `/ops/decision-memo/{notice_id}`
   - persisted decision becomes visible immediately
   - existing Review Board -> Decision Memo and selected opportunity -> Decision Memo flows
     remain intact

### UI constraints

- no heavy frontend dependency
- keep existing panel layout
- avoid broad visual redesign
- preserve rc15 loading and empty-state behavior

## Daily Review Pack Integration

Daily Review Pack already reads Decision Memo-derived output.

rc16 should preserve:

- `Decision Memo Summary`
- `Decision Memo Details`

Behavior change:

- when a manual decision exists, the displayed decision in those sections must use the
  persisted manual value
- when no manual decision exists, preserve rc15 generated/default behavior

The markdown should show the persisted decision explicitly enough for operator review and
meeting notes.

## CSV Export Integration

Required rc15 fields remain:

- `decision_memo_decision`
- `decision_memo_fit_summary`

rc16 behavior:

- `decision_memo_decision` reflects the persisted manual decision when present
- otherwise it reflects the rc15 generated/default decision

Optional enhancement:

- add a `decision_memo_manual_note` field only if it fits current CSV patterns cleanly

For rc16 minimalism, this field is optional. The key requirement is that the exported
decision column reflects the persisted manual value.

## Error Handling

### Unknown notice id

- save route returns safe `not_found`
- Decision Memo continues to return safe `not_found`
- no persistence side effect

### Invalid decision

- reject with `4xx`
- no file write

### Corrupted local JSON

- follow the current local JSON pattern:
  - read as empty when parsing fails
  - continue to return safe local defaults

### Secret/path safety

- do not expose `.env`
- do not expose service keys
- sanitize local note text with the same redaction approach already used in
  `review_status.py`

## Testing Plan

Tests should be added before implementation changes are completed, following the existing
repository pattern.

### Storage/API tests

- save each valid decision:
  - `Prepare`
  - `Review`
  - `Hold`
  - `Reject`
- invalid decision returns `4xx`
- unknown notice id returns safe `not_found`
- persisted decision survives separate calls in the same local repo state

### Decision Memo tests

- saved decision appears in `/ops/decision-memo/{notice_id}`
- saved decision replaces prior saved decision value
- generated fallback remains when no manual decision exists

### Daily Review Pack tests

- persisted decision appears in pack payload
- persisted decision appears in markdown
- existing `Decision Memo Summary` and `Decision Memo Details` sections remain present

### CSV tests

- existing CSV fields remain present
- `decision_memo_decision` reflects persisted manual decision
- `decision_memo_fit_summary` remains present

### UI tests

- Decision Memo panel contains visible:
  - `Prepare`
  - `Review`
  - `Hold`
  - `Reject`
  - decision note input
  - save hook
- save flow updates the Decision Memo display
- existing rc15 hooks do not regress:
  - Review Board -> Decision Memo
  - selected opportunity -> Decision Memo

### No-real safety tests

- no real API calls attempted
- no real network calls attempted
- no secret exposure

## Validation Commands

Required validation after implementation:

```powershell
python -m pytest -q
python -m ruff check app tests
scripts/check_deploy_readiness.ps1
scripts/validate_local.ps1
scripts/validate_ops_package.ps1
```

Required explicit smoke checks:

- `GET /ops/decision-memo/G2B-SAMPLE-2026-001` returns success
- save `Prepare`, re-read, confirm `Prepare`
- save `Review`, re-read, confirm replacement
- save `Hold`, re-read, confirm replacement
- save `Reject`, re-read, confirm replacement
- invalid decision returns `4xx`
- `UNKNOWN-NOTICE-ID` returns safe `not_found`
- `/ui` returns `200`
- UI contains visible manual decision controls
- UI JS contains the save hook
- Daily Review Pack markdown contains:
  - `Decision Memo Summary`
  - `Decision Memo Details`
  - persisted manual decision
- CSV contains:
  - `decision_memo_decision`
  - `decision_memo_fit_summary`
  - persisted manual decision

## Non-Goals

rc16 does not:

- add authentication
- add user identity
- add multi-user concurrency rules
- add real G2B API behavior
- replace generated scoring logic
- redesign the UI broadly
- introduce a new database-backed persistence layer

## Recommended Implementation Plan Boundary

This spec is intentionally sized as one narrow rc16 vertical slice:

1. extend local review-status persistence schema
2. add manual decision write route
3. merge manual decision into Decision Memo read path
4. add UI controls and save hook
5. let Daily Review Pack and CSV reflect the overridden Decision Memo decision
6. update `docs/99_DECISION_LOG.md` after validation

If implementation pressure appears beyond that scope, stop and split the follow-up rather
than broadening rc16.
