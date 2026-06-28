# 08 Usability Review

## Review Summary

- Review date: 2026-06-28
- Active deployment path: `D:\Deploy\yonlab-g2b-agent-v2-rc11`
- Active tag: `v0.1.0-rc11`
- Active HEAD: `8bc1825`
- Latest completed task: Task 46G
- Review mode: no-real operational workflow audit
- Real API executed: no
- Additional real API call count: 0
- Service key exposed: false

This review checked the operator workflow from safe daily validation through the browser UI,
Opportunity Inbox, Opportunity Detail, Daily Review Pack, Markdown/CSV export, and scheduler
status. It did not run a confirmed real G2B API call.

## Tested Workflow

1. Confirmed rc11 deployment checkout and tag.
2. Removed the transient real API runtime gate from the current process.
3. Confirmed `.env` exists without printing its values.
4. Ran `scripts/run_ops_safe_daily.ps1` from the rc11 deployment.
5. Started FastAPI on `http://127.0.0.1:8016`.
6. Checked:
   - `/ops/quality-summary`
   - `/ops/report-index`
   - `/ops/opportunity-inbox`
   - `/ops/daily-review-pack`
   - `/ops/daily-review-pack/markdown`
   - `/ops/daily-review-pack/csv`
   - `/ui`
7. Opened the first Opportunity Inbox detail panel in the browser.
8. Confirmed the scheduler target points to rc11 safe daily, not a real API wrapper.

## What Works

- Safe daily succeeds and writes logs under the rc11 deployment.
- Scheduler points to `D:\Deploy\yonlab-g2b-agent-v2-rc11\scripts\run_ops_safe_daily.ps1`.
- Scheduler does not target the controlled real wrapper.
- `/ui` renders without getting stuck on `Loading`.
- System Status, Quality Summary, Local Operations Package, Opportunity Inbox, Opportunity
  Detail, and Daily Review Pack all load independently.
- Opportunity Inbox gives a useful first commercial screen: score, grade, decision, priority,
  risk, today action, source, and a detail action.
- Opportunity Detail loads required documents, risk categories, and a copy-ready markdown
  recommendation.
- Daily Review Pack gives a practical morning review artifact with top opportunities,
  today actions, required documents, risks, and downloadable Markdown/CSV.
- Markdown and CSV exports exclude `.env`, service key fields, local absolute paths, and raw
  source payloads.
- CSV output has stable columns and no unescaped formula-style row prefix in the audited data.

## Friction Points

- A fresh rc11 deployment can show `quality-summary: empty` and `report-index: empty` while
  Opportunity Inbox and Daily Review Pack show `demo` data. This is technically correct, but
  an operator may not immediately understand the difference between saved operations data and
  demo fallback data.
- The Run Recommendation form exposes fixture and real modes in the same compact panel. The
  guard text is present, but non-developers may still hesitate before using fixture-safe runs.
- Daily Review Pack uses English section headings with Korean business content. This is usable,
  but a fully Korean review pack would be easier to forward internally.
- The final recommended response bullets in the Daily Review Pack are generic and English.
- Required document lists are useful but dense; they can overwhelm the detail panel and the
  daily pack when a reviewer is trying to decide in under two minutes.
- Scheduler status is only checked through PowerShell. The UI does not yet surface last safe
  daily result, next scheduled run, or target deployment path.
- The UI shows source mode, but the business meaning of `demo`, `fixture`, `saved`, and `real`
  is not explained inline.
- Empty states are explicit, but they do not always recommend the next operator action.

## Operator Confusion Points

- `demo` opportunities are useful for a fresh deployment, but they can be mistaken for saved
  operational recommendations.
- `quality-summary: empty` beside populated demo opportunities can look inconsistent.
- The difference between safe daily, fixture run, guarded real run, and scheduler check is
  still script-oriented.
- `P1/P2/P3/Hold` is compact and effective after learning, but first-time operators may need
  a one-line legend.
- Go/No-Go labels and Korean decision labels are valuable, but they should be visually grouped
  closer to recommended action and risk level.

## Daily Review Pack Audit

Useful:

- Top items and P1/Hold grouping make a morning review meeting possible.
- Today actions and required documents are directly usable.
- Risk summary correctly highlights the high-risk regional/performance example.
- Markdown export is readable and safe for copy/paste.
- CSV export is practical for spreadsheet review.

Issues:

- P2/P3 counts can be zero in demo mode, which makes the summary feel less representative.
- English headings and generic English response bullets reduce internal forwarding quality.
- Required document lines are long and may need grouping into eligibility, tax/legal, proposal,
  and technical/security buckets.
- The exported report does not yet include a short executive summary such as "today pursue 2,
  hold 1, no no-go".

Export quality:

- Markdown: HTTP 200, correct content type, expected title/actions/documents/risk sections.
- CSV: HTTP 200, correct content type, expected header, 3 audited rows.
- Export safety: no `.env`, no service key field, no local absolute path, no raw response.

## Opportunity Inbox Audit

Useful:

- Score, grade, priority, risk, and today action are visible in one row.
- Detail panel loads enough evidence for a first-pass bid decision.
- Markdown detail report is useful for internal notes.
- Required documents and risk categories support practical review.

Issues:

- Detail panel is dense and currently reads more like a structured data dump than an operator
  checklist.
- Table columns are broad; on smaller screens, the most important fields can be pushed right.
- Decision label, priority, Go/No-Go, risk, and today action should be visually grouped.
- The source column needs a clearer explanation of demo versus saved versus real.
- There is no single "next action" command after reviewing a notice, such as mark for review,
  copy detail markdown, or add to daily pack.

Decision quality:

- Strong AI/SW and startup/small-business fit is clear for top demo opportunities.
- High-risk regional/performance restrictions are visible for the hold item.
- The current deterministic rules are good enough for triage, but not yet enough for final
  bid/no-bid approval.

## Improvement Backlog

P0: must fix before daily operation

- None found. rc11 is usable for safe daily operations and no-real bid review.

P1: high-value usability improvement

- Add a dashboard data source banner explaining `demo`, `fixture`, `saved`, and `real`.
- Add a one-line P1/P2/P3/Hold/No-Go legend near Daily Review Pack and Opportunity Inbox.
- Add a safe daily scheduler card to `/ui`: target deployment, next run, last result, and
  real-wrapper-not-registered status.
- Add clearer empty-state next actions: "Run fixture-safe job", "Review demo only", or
  "Open saved runs".
- Convert Daily Review Pack headings and recommended response bullets to Korean business
  review language.
- Group required documents into categories to reduce reading load.
- Add an executive summary line to Daily Review Pack exports.

P2: nice-to-have

- Add compact badges or color treatments for priority, risk, Go/No-Go, and source mode.
- Add column visibility or a compact mobile layout for Opportunity Inbox.
- Add CSV Korean header option for internal sharing.
- Add "download current opportunity detail markdown" closer to the selected notice content.
- Add export filenames with date and source mode.
- Add a dashboard link to the latest safe daily log path without exposing log contents.

Later: future commercial feature

- Add operator annotations such as reviewed, owner, deadline owner, and next meeting decision.
- Add saved shortlists for "today pursue", "partner needed", and "monitor".
- Add document checklist completion tracking.
- Add controlled attachment download and local document analysis workflow integration.
- Add business value/risk calibration from actual win/loss or review outcomes.

## Recommended Next Task Scope

Recommended Task 48G:

Improve operator clarity in the local operations UI without changing real API behavior.

Suggested scope:

- Add source-mode and priority legends.
- Add a scheduler/safe-daily status card.
- Improve Daily Review Pack Korean labels and executive summary.
- Improve empty states with next action prompts.
- Keep all changes deterministic and no-real by default.

Do not include:

- Confirmed real G2B API call.
- New external integrations.
- Database schema changes unless strictly needed for display.
- Large visual redesign.

## No-Real And No-Secret Confirmation

- Confirmed real API command was not executed.
- `YONLAB_AUTO_RUN_REAL_API=true` was not set.
- Real API wrapper was not registered in the scheduler.
- Service key values and `.env` contents were not printed.
- Runtime DB, logs, raw responses, and generated reports were not committed.
