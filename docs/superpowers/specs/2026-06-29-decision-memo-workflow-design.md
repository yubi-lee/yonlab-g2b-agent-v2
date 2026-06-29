# Task 51B Decision Memo Workflow Design

## Goal

Add a safe Review Board to Decision Memo workflow to `D:\Views\yonlab-g2b-agent-v2` so an
operator can move from an active Review Board item to a concise, YOnLab-ready bid decision
memo without calling the real G2B API.

## Scope

This design covers:

- the target operator workflow from Review Board into a Decision Memo
- the safe input contract from a selected Review Board card or Opportunity Inbox item
- required Decision Memo fields and formatting rules
- recommended decision values: `Prepare`, `Review`, `Hold`, `Reject`
- a safe `/ops/decision-memo` endpoint concept
- a `/ui` Decision Memo panel concept
- Daily Review Pack and export inclusion concepts
- no-real safety requirements
- a small-slice implementation path toward rc15

This design does not cover:

- any new real G2B API behavior
- any `.env` generation or secret handling changes
- any external AI/LLM summarization
- background automation that writes memos automatically
- replacing Review Board, Opportunity Inbox, or existing opportunity report behavior

## Current Context

After rc14, the application already has:

- a safe `GET /ops/review-board` endpoint
- `/ui` Review Board rendered above Opportunity Inbox
- click-through from Review Board cards into Inbox filtering
- local-only review status persistence with owner and next action
- Daily Review Pack summary and export support
- deterministic opportunity detail and markdown report generation
- no-real validation coverage for Review Board and Daily Review Pack

That means the missing operator capability is no longer "what should I inspect next?".
The missing capability is "how do I turn this reviewed item into a small internal decision
memo that helps YOnLab decide whether to spend proposal effort now?".

## Problem Statement

Review Board gives a good operational summary, but it does not yet assemble the selected
notice into a stable decision artifact.

Operators still need to manually gather:

- why the notice fits YOnLab
- what the major risks are
- what deadline pressure exists
- what next action is required
- whether the immediate recommendation is `Prepare`, `Review`, `Hold`, or `Reject`

Task 51 should add this memo layer without changing any real-run gate.

## Chosen Approach

Use a server-led Decision Memo builder derived from the same local-safe opportunity data that
already powers Review Board, Opportunity Inbox, Daily Review Pack, and the existing
opportunity report.

Why this approach:

- it keeps decision rules deterministic and testable
- it avoids duplicating memo logic in browser JavaScript
- it lets `/ui`, API consumers, and export flows share one safe memo payload
- it preserves the current no-real operating model

Rejected alternatives:

1. Build the whole memo only in the browser.
   - Rejected because it would duplicate formatting and decision rules outside API tests.

2. Reuse the full opportunity markdown report as the memo.
   - Rejected because the report is richer and longer than the operator needs for a
     go/review/hold/reject checkpoint.

3. Add an AI-generated memo.
   - Rejected because this workflow must stay deterministic, local-safe, and easy to validate.

## Target Operator Workflow

1. The operator opens `/ui`.
2. Review Board shows active-state-first cards and deadline-first next actions.
3. The operator clicks a Review Board card or a next-action row.
4. Opportunity Inbox filters update and the relevant notice list loads.
5. The operator opens one notice in Opportunity Detail.
6. The operator requests a Decision Memo for that selected notice.
7. The app shows a concise memo with:
   - YOnLab fit summary
   - risk summary
   - deadline and next-action summary
   - recommended decision value
8. The operator uses that memo for:
   - internal bid triage
   - go/review/hold/reject discussion
   - Daily Review Pack/export inclusion

The Decision Memo should help a human decide quickly. It should not replace the human
decision.

## Input from Review Board Card

The Decision Memo must be buildable from an item selected through the existing safe workflow.

Minimum input path:

1. Review Board card click or next-action click supplies a `notice_id`
2. the app loads the selected Opportunity Inbox item or Opportunity Detail
3. the memo builder derives its content from already merged, local-safe fields

Required upstream item fields:

- `notice_id`
- `title`
- `agency`
- `deadline`
- `score`
- `grade`
- `risk_level`
- `review_status`
- `review_status_ko`
- `owner`
- `next_action`
- `decision_label`
- `decision_label_ko`
- `bid_priority`
- `go_no_go_recommendation`
- `go_no_go_recommendation_ko`
- `reasons`
- `risks`
- `required_documents`
- `required_documents_grouped`
- `source_type`
- `source_run_id`

If any of these are missing, the memo should degrade safely using empty-state or fallback text
instead of failing.

## Required Decision Memo Fields

The memo should be compact, operator-facing, and copy-friendly.

Minimum memo payload:

- `status`
- `generated_at`
- `notice_id`
- `title`
- `agency`
- `source_type`
- `source_run_id`
- `review_status`
- `review_status_ko`
- `decision_value`
- `decision_value_ko`
- `matching_score`
- `bid_priority`
- `yonlab_fit_summary`
- `risk_summary`
- `deadline_summary`
- `next_action_summary`
- `document_summary`
- `memo_lines`
- `service_key_exposed = false`
- `real_api_call_attempted = false`

### Field intent

#### `decision_value`

One of:

- `Prepare`
- `Review`
- `Hold`
- `Reject`

This is the main output the operator uses in a triage meeting.

#### `decision_value_ko`

Suggested operator-facing Korean labels should map 1:1 to these values and remain UTF-8-safe
using the same conventions as the existing dashboard and report flows.

Example mapping keys:

- `Prepare` -> `prepare_label_ko`
- `Review` -> `review_label_ko`
- `Hold` -> `hold_label_ko`
- `Reject` -> `reject_label_ko`

#### `memo_lines`

A compact ordered list of 4-8 human-readable lines suitable for direct display or export.

The memo lines should be stable and deterministic, not free-form AI text.

## YOnLab-Fit Summary Format

The memo should explicitly answer: "Why is this notice a fit for YOnLab right now?"

Recommended structure:

- one lead sentence
- two to four bullet reasons

Lead sentence pattern:

`This notice is a [strong/moderate/limited] fit for YOnLab because it aligns with [core fit themes].`

Preferred fit themes should derive from existing scoring and YOnLab profile:

- software business eligibility
- AI/SW or information-system scope
- Seoul location fit
- startup or small-business preference
- Device Farm, AI/SW verification, AI Agent, cloud-system relevance

Example shape:

- `YOnLab fit: strong`
- `AI/SW system scope matches YOnLab core delivery capability.`
- `Software business qualification supports baseline eligibility.`
- `Small-business or startup preference improves practical competitiveness.`

## Risk Summary Format

The risk summary should answer: "What could block or delay a bid decision?"

Recommended structure:

- overall risk level
- one-line operator summary
- one to three specific blockers or watch items

Preferred risk topics:

- region restriction
- recent performance requirement
- manpower or on-site burden
- hardware-heavy mismatch
- unclear qualification text
- short deadline or missing next action

Example shape:

- `Risk level: medium`
- `Main concern: recent performance evidence may be required.`
- `Watch item: deadline is near and supporting document readiness is not confirmed.`

The memo should prefer operator clarity over exhaustive detail.

## Deadline and Next-Action Format

The memo should answer: "When do we need to act, and what is the immediate next step?"

Recommended fields:

- `deadline_summary`
- `next_action_summary`

`deadline_summary` should include:

- raw deadline value when present
- normalized urgency label such as `overdue`, `due_soon`, `upcoming`, or `unknown`

`next_action_summary` should include:

- owner when present
- next action text when present
- fallback text when no saved next action exists

Example shape:

- `Deadline: 2026-07-15 (due_soon)`
- `Next action: owner not set; confirm eligibility and document readiness today.`

## Recommended Decision Values

Decision values must be deterministic and easy to explain.

### `Prepare`

Use when:

- fit is strong
- risk is manageable
- deadline is actionable
- current state suggests proposal preparation can start

Typical signals:

- high score
- `go` or strong `reviewing`
- low or medium risk
- clear AI/SW fit

### `Review`

Use when:

- fit is promising
- one or more material questions remain open
- operator review should continue before proposal commitment

Typical signals:

- medium-to-high score
- `reviewing` or `shortlisted`
- open qualification or document questions

### `Hold`

Use when:

- the notice is not a current preparation target
- timing, staffing, or uncertainty suggests waiting
- the item should stay visible but not consume immediate bid effort

Typical signals:

- `hold` review status
- later deadline
- unclear priority versus stronger candidates

### `Reject`

Use when:

- fit is weak
- risk is structurally high
- hard blockers make YOnLab a poor candidate now

Typical signals:

- region mismatch
- heavy recent-performance constraint
- H/W-heavy scope with weak AI/SW fit
- existing no-go style decision fields

## Safe `/ops/decision-memo` Endpoint Concept

Recommended initial shape:

- `GET /ops/decision-memo/{notice_id}`

Why notice-scoped first:

- it matches the current Opportunity Detail selection model
- it avoids introducing a second search/filter contract
- it is easy to call from `/ui` and easy to test

Required behavior:

- reads only local-safe opportunity/detail data
- performs no real G2B API call
- returns safe empty state if the notice does not exist
- redacts local paths, `.env` references, and service-key-like substrings

Suggested response shape:

```json
{
  "status": "success",
  "generated_at": "2026-06-29T12:00:00+00:00",
  "notice_id": "NOTICE-001",
  "title": "AI support service",
  "agency": "Agency A",
  "review_status": "reviewing",
  "review_status_ko": "reviewing_label_ko",
  "decision_value": "Review",
  "decision_value_ko": "review_label_ko",
  "matching_score": 88,
  "bid_priority": "P1",
  "yonlab_fit_summary": {
    "fit_level": "strong",
    "summary": "AI/SW scope and software-business eligibility align with YOnLab.",
    "reasons": [
      "AI/SW system scope matches YOnLab capability.",
      "Software business eligibility is aligned.",
      "Startup or small-business conditions are favorable."
    ]
  },
  "risk_summary": {
    "risk_level": "medium",
    "summary": "Recent performance evidence may require confirmation.",
    "items": [
      "Check whether recent project evidence is mandatory."
    ]
  },
  "deadline_summary": {
    "deadline": "2026-07-15",
    "urgency": "due_soon",
    "summary": "Deadline is near enough to require same-day review."
  },
  "next_action_summary": {
    "owner": "YOnLab",
    "next_action": "Confirm eligibility and proposal readiness.",
    "summary": "Owner should confirm eligibility and documents today."
  },
  "document_summary": {
    "required_count": 4,
    "groups": {
      "eligibility": ["software business certificate"]
    }
  },
  "memo_lines": [
    "Decision: Review",
    "YOnLab fit is strong because the notice is AI/SW-oriented and eligible.",
    "Main risk is recent performance evidence.",
    "Deadline is due soon; confirm eligibility and document readiness today."
  ],
  "service_key_exposed": false,
  "real_api_call_attempted": false
}
```

## `/ui` Decision Memo Panel Concept

The UI should not introduce a separate decision page first.

Recommended placement:

- in the existing Opportunity Detail area
- beside or below the current markdown report controls

Recommended panel contents:

- decision value badge
- score and priority
- YOnLab fit summary
- risk summary
- deadline and next action summary
- copy-ready memo lines

Recommended controls:

- `Load Decision Memo`
- `Copy Decision Memo`
- optional `Download Markdown`

The panel should remain safe when:

- no notice is selected
- the notice exists but saved review metadata is sparse
- the endpoint returns `empty`

## Daily Review Pack and Export Inclusion Concept

Task 51 should not replace the existing Daily Review Pack summary.
It should add a small Decision Memo layer to it.

Recommended pack additions:

- per-top-item `decision_value`
- per-top-item `decision_value_ko`
- compact memo summary line
- optional decision memo section for top reviewed notices

Recommended export behavior:

- markdown export can include a `Decision Memo Summary` section
- CSV export can include:
  - `decision_value`
  - `decision_value_ko`
  - `yonlab_fit_level`
  - `risk_summary_short`
  - `deadline_urgency`
  - `decision_next_action`

Full private notes should remain excluded from export.

## No-Real Safety Requirements

The Decision Memo workflow must keep the same safety model as rc14 Review Board.

Required guarantees:

- no real G2B/Public Data Portal API call
- no `.env` mutation
- no secret or service-key exposure
- no raw local path leakage in memo payloads
- no auto-write behavior outside existing local-safe patterns
- deterministic content only from saved/demo/fixture-safe data

Validation should explicitly verify:

- `service_key_exposed = false`
- `real_api_call_attempted = false`
- memo rendering works with empty and partial data

## Non-Goals

Task 51 is not intended to:

- decide autonomously whether YOnLab must bid
- replace the richer full markdown opportunity report
- generate long proposal text
- store a new persistent approval system yet
- trigger emails, scheduler actions, or real API jobs

## Small-Slice Implementation Path

This spec is designed to be implemented in small vertical slices:

1. backend-only memo contract
2. `/ui` Decision Memo panel
3. Daily Review Pack/export additions
4. rc15 no-real release closeout

That sequence preserves the current local-safe workflow while making each step testable and
reviewable on its own.
