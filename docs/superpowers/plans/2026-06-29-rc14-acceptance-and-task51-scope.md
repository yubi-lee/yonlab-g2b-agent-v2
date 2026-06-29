# rc14 Acceptance and Task 51 Scope

> **For agentic workers:** This document records the accepted operator baseline for `v0.1.0-rc14` and defines the next documentation-first scope for Task 51. It does not authorize product-code changes by itself.

## 1. Purpose

This document does two things:

1. records `rc14` Review Board release acceptance from an operator perspective
2. defines the proposed scope for the next release line, `Task 51: Review Board to Decision Workflow`

This is a planning and release-documentation artifact only. It does not change application behavior, endpoints, or UI logic.

## 2. Current Repo Observations

- Repository: `D:\Views\yonlab-g2b-agent-v2`
- Branch at review time: `main`
- Current accepted Review Board release commit: `968ef48 docs: record rc14 review board release`
- Accepted release tag: `v0.1.0-rc14`
- Tag target provided by operator context: `968ef48bf6e3a1c0c5ba6eb3a1fd253525c144fb`
- Fresh deploy path: `D:\Deploy\yonlab-g2b-agent-v2-rc14`
- `tools/` directory does **not** exist in this repository, so the effective lint command is `ruff check app tests`

Relevant existing docs confirm that Review Board is now part of the local-safe operations workflow:

- `README.md`
- `docs/06_OPERATIONS_RUNBOOK.md`
- `docs/07_DEPLOYMENT_HANDOFF.md`
- `docs/99_DECISION_LOG.md`
- `docs/superpowers/specs/2026-06-29-review-board-workflow-design.md`
- `docs/superpowers/plans/2026-06-29-review-board-workflow-implementation-plan.md`

## 3. rc14 Acceptance Summary

`rc14` is accepted as the current Review Board release baseline from an operator perspective.

Accepted outcome:

- `GET /ops/review-board` works as a safe, local-only summary endpoint
- `/ui` renders Review Board at the top of the dashboard
- Review Board click-through updates Opportunity Inbox filtering as intended
- Review Board shows active-state-first status emphasis
- Review Board next actions are ordered deadline-first
- Daily Review Pack includes Review Board summary information
- local repo validation and fresh deploy no-real validation passed
- the release remained no-real by default and did not attempt a real G2B/API call

Operational meaning of acceptance:

- operators now have a safe dashboard-first review workflow
- Review Board is the entry surface for current review work
- Opportunity Inbox remains the execution surface
- Daily Review Pack remains the export/reporting surface
- `rc14` is good enough to use as the baseline for the next workflow layer rather than reopening Review Board scope itself

## 4. Validated Commands and Results

The accepted `rc14` baseline reflects the already-completed release flow described in repository docs and operator context.

### rc14 release/baseline results

| Validation item | Result | Note |
|---|---|---|
| `/ops/review-board` endpoint | PASS | Safe Review Board summary available |
| `/ui` Review Board rendering | PASS | Top-of-dashboard summary confirmed |
| Review Board click -> Inbox filter path | PASS | Operator flow validated |
| Deadline-first next actions | PASS | Present in Review Board output |
| Daily Review Pack Review Board summary | PASS | Included in report/export workflow |
| Local no-real validation | PASS | Completed without real API calls |
| Fresh deploy no-real validation | PASS | Completed on `D:\Deploy\yonlab-g2b-agent-v2-rc14` |
| `real_network_call_attempted` | FALSE | No real network call accepted in rc14 flow |
| `real_api_call_attempted` | FALSE | No real API call accepted in rc14 flow |

### Validation command note for future follow-up work

Because `tools/` does not exist in this repository, the correct lint command for this release line is:

```powershell
.\.venv\Scripts\python.exe -m ruff check app tests
```

Not:

```powershell
.\.venv\Scripts\python.exe -m ruff check app tests tools
```

## 5. No-Real Safety Confirmation

`rc14` is accepted only as a no-real release.

Safety-confirmed properties:

- no real G2B API call is required for Review Board behavior
- no `.env` change is required for Review Board behavior
- no secret or service key exposure is part of Review Board behavior
- no automatic real-call execution path was introduced
- local and fresh deployment validation both stayed within safe local/saved data boundaries

This means Review Board is now part of the deterministic operator workflow layer, not part of the guarded real-call layer.

## 6. Review Board Capabilities Now Available

The following capabilities are now available in `rc14`:

1. safe Review Board summary at `/ops/review-board`
2. top-level Review Board panel in `/ui`
3. active-state-first operational grouping
4. deadline-first next-action display
5. click-through from Review Board into Inbox review slices
6. Review Board summary carried into Daily Review Pack/export workflow
7. local/fresh deploy validation path for this workflow without real API usage

From an operator workflow perspective, `rc14` now supports:

- see what review work is active
- see what should be acted on first
- jump directly into the matching Inbox slice
- carry the summary into Daily Review Pack output

## 7. What rc14 Intentionally Does Not Solve

`rc14` intentionally stops before decision-writing workflow.

It does **not** yet provide:

- a Decision Memo or decision-ready operator summary for a selected notice
- a dedicated safe `/ops/decision-memo` endpoint
- a Decision Memo panel in `/ui`
- an export section focused on go/no-go rationale, not just review status and next action
- a release flow for a Decision Workflow baseline (`rc15`)

In short:

- `rc14` solves **review visibility and navigation**
- `rc14` does not yet solve **decision capture and decision communication**

## 8. Task 51 Problem Statement

Now that Review Board is accepted, the next operator problem is not "what should I open?" but "how do I record and communicate the decision once I open it?"

The next workflow gap is:

- operators can see active work and next actions
- operators can filter into Inbox
- operators can update review status
- but operators do not yet have a dedicated, safe, structured Decision Memo surface that explains whether the team should proceed, pause, or decline and why

Task 51 should therefore add a deterministic Decision Workflow layer on top of the accepted Review Board baseline.

## 9. Proposed Task 51 Scope

### 9.1 Review Board to Decision Memo

Add a workflow that lets operators move from Review Board / Inbox review state into a structured Decision Memo for a notice.

Purpose:

- convert safe recommendation and review metadata into a compact internal decision artifact
- support clearer go / hold / no-go communication inside the existing local operations flow
- stay deterministic and local-safe by default

### 9.2 Safe `/ops/decision-memo` Endpoint

Add a new safe endpoint:

- `GET /ops/decision-memo/{notice_id}` or equivalent final route shape decided in Task 51B

Expected characteristics:

- derived from existing safe local data only
- no real G2B API call
- no secret exposure
- no `.env` disclosure
- returns structured decision-ready fields rather than raw note bodies or raw source payloads

### 9.3 `/ui` Decision Memo Panel

Add a Decision Memo panel to `/ui`.

Expected purpose:

- show the selected notice's decision summary
- present decision framing such as fit, risks, required follow-up, and recommended operator action
- remain subordinate to the existing Opportunity Inbox/detail workflow rather than replacing it

### 9.4 Daily Review Pack / Export Enhancement

Extend Daily Review Pack/export behavior so the review workflow can carry a safe decision summary.

Expected additions:

- decision memo summary or decision-rationale fields
- safe export fields for internal review meetings
- no full private note leakage
- no path or secret leakage

### 9.5 rc15 No-Real Release Flow

Promote Task 51 only through another no-real release line.

Expected release target:

- `rc15`

Expected gate:

- local no-real validation passes
- fresh deploy no-real validation passes
- Decision Memo flow works from operator perspective
- no real API call is introduced or required

## 10. Proposed Follow-Up Tasks

### 51B Decision Memo spec

Goal:

- define the Decision Memo contract, fields, safety rules, and UX behavior before implementation

Expected output:

- a dedicated spec document for the Decision Workflow

### 51C Safe backend endpoint

Goal:

- implement the safe backend endpoint for Decision Memo generation from local/saved data only

Expected scope:

- service layer
- API contract
- tests for safe deterministic output

### 51D UI panel

Goal:

- add the Decision Memo panel in `/ui`

Expected scope:

- panel rendering
- interaction from Inbox/detail context
- safe empty/error states

### 51E Export enhancement

Goal:

- extend Daily Review Pack/export outputs with safe decision memo fields

Expected scope:

- markdown/csv payload updates
- export-safety regression coverage

### 51F rc15 release

Goal:

- validate and release the Decision Workflow as the next no-real release baseline

Expected scope:

- local validation
- fresh deployment validation
- release tag / deployment handoff update

## 11. Suggested Task 51 Acceptance Direction

Task 51 should be considered successful only when all of the following are true:

- operators can move from Review Board / Inbox into a Decision Memo workflow
- the Decision Memo is derived from safe local data only
- `/ui` exposes the Decision Memo clearly enough for internal review use
- Daily Review Pack/export can carry safe decision summary fields
- local and fresh deploy validation pass without any real API call
- `real_network_call_attempted=false`
- `real_api_call_attempted=false`

## 12. Recommended Next Task

Recommended immediate next task:

- `51B Decision Memo spec`

Reason:

- `rc14` already closes Review Board scope well enough
- the next risk is ambiguity around what a Decision Memo should contain
- defining the contract first will keep `51C` through `51F` smaller, safer, and easier to validate
