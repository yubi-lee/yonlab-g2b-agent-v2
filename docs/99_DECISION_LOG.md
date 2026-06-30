# 99 Decision Log

## 2026-06-20

Decision: Keep v2 independent from `D:\Views\yonlab-bid-agent`.

Reason:

- Prevent v1/v2 code contamination.
- Keep Agent-first development testable from a clean baseline.
- Preserve fixture-first iteration before any real API smoke test.

## 2026-06-20 MVP Vertical Slice

Decision: Implement a complete deterministic MVP before real G2B API integration.

Included:

- Pydantic domain models.
- Local G2B-style fixtures.
- Korean/G2B-like normalizer.
- First-pass eligibility logic.
- Risk analyzer.
- 100-point scoring model.
- Korean markdown report generator.
- FastAPI endpoints for profile, fixtures, normalization, scoring, reports, and demo ranking.

## 2026-06-20 Guarded Dual Pipeline

Decision: Add real G2B client capability behind explicit safety gates while preserving fixture default.

Safety gates:

- `G2B_ENABLE_REAL_API=true`
- service key configured
- endpoint path configured
- request has `confirm_real_api_call=true`

Reason:

- The app can be exercised safely in fixture mode.
- Real API code can be tested with mocked responses.
- Service keys stay out of responses, logs, tests, and docs.

## 2026-06-20 Korean UTF-8 Regression

Decision: Add explicit UTF-8 handling to PowerShell smoke scripts and regression tests for Korean fixture/API/report output.

Reason:

- G2B/Narajangteo data contains Korean text in notice titles, agencies, qualification text, and descriptions.
- Fixture files were valid UTF-8, but Windows PowerShell response rendering could produce mojibake without explicit UTF-8 console/output and response-stream decoding.
- Smoke scripts now set UTF-8 output, use UTF-8 request bytes, decode API response streams as UTF-8, and print readable JSON or markdown.

## 2026-06-20 One-Command Local Validation

Decision: Add `scripts/validate_local.ps1` as the preferred local validation entrypoint.

Reason:

- Manual smoke validation required multiple terminal windows and repeated commands.
- The runner executes pytest, starts a temporary local FastAPI server, waits for `/health`, runs fixture and report smoke scripts, and stops the server reliably.
- This keeps Korean UTF-8 smoke validation repeatable without real G2B/Public Data Portal calls.

## 2026-06-20 Controlled Real G2B Smoke and Capture

Decision: Add explicit real API smoke templates and optional sanitized response capture while keeping all default validation fixture-only.

Reason:

- Real G2B/Public Data Portal calls must require enabled settings, a service key, endpoint path, real mode, and per-request confirmation.
- Guard-blocked smoke validation proves the safety gates work without calling the real network.
- Captured real responses can help future field mapping work, but captures are opt-in, UTF-8 JSON, secret-masked, and ignored by Git.

## 2026-06-20 Real G2B Readiness Guide and Endpoint Presets

Decision: Add endpoint presets, no-secret validation, and an offline real-readiness command before any confirmed Public Data Portal/G2B smoke.

Reason:

- First real integration needs repeatable local setup without weakening the default fixture-first safety model.
- The approved first-smoke base path is `/1230000/ad/BidPublicInfoService`.
- `G2B_ENDPOINT_PRESET=approved_bid_public_info_service` is available, but `.env.example`
  originally used `G2B_LIST_ENDPOINT_PATH=/1230000/ad/BidPublicInfoService` directly.
- Readiness validation must prove configuration safety without calling the real API or printing service keys.

## 2026-06-20 G2B Service Operation Path and Diagnostics

Decision: Use `/1230000/ad/BidPublicInfoService/getBidPblancListInfoServcPPSSrch` as the recommended first real service-search operation path.

Reason:

- The approved service base path alone can return HTTP/path errors for real list/search calls.
- Service search requires operation-compatible query parameters such as `ServiceKey`, `type=json`, `inqryDiv=1`, inquiry date range, and `bidNtceNm`.
- HTTP error responses should include safe diagnostics such as status code and endpoint path without exposing the service key.

## 2026-06-20 Real G2B Response Normalization Calibration

Decision: Calibrate normalization and recommendation behavior using a sanitized real BidPublicInfoService service-search sample after the first controlled smoke succeeded.

Reason:

- Real service-search responses include contract, service division, procurement category, joint-supply, industry-limit, and evaluation-ratio fields that improve YOnLab recommendation quality.
- `active_only` filtering keeps expired notices out of real recommendations by default while preserving missing-deadline notices with a medium risk signal.
- Successful real responses should return safe endpoint metadata without query parameters or service keys.

## 2026-06-20 Real G2B Detail Analysis Queue

Decision: Extract notice detail URLs, attachment URL/file-name metadata, and risk-related fields from real BidPublicInfoService list responses into a deterministic `detail_analysis_queue`.

Reason:

- Real list responses already include public `bidNtceDtlUrl`, `bidNtceUrl`, `ntceSpecDocUrl*`, and `ntceSpecFileNm*` fields needed for the next analysis step.
- Recommendation quality can improve by surfacing attachment and risk metadata before any attachment download feature exists.
- The queue is metadata-only: it does not download files, create local artifacts, or expose service keys.

## 2026-06-20 Swagger Placeholder Handling

Decision: Make Swagger examples practical and treat generated placeholder inputs as empty or ignorable for recommendation convenience paths.

Reason:

- Users may run Swagger-generated examples containing `"string"` or `{"additionalProp1": {}}`.
- G2B recommendation filter placeholders should behave like omitted filters so fixture recommendations still return useful results.
- Demo recommendation placeholder notices should be ignored, falling back to fixtures when no valid custom notice remains.
- Real API safety gates remain unchanged: real calls still require enabled settings, service key configuration, endpoint path, real mode, and explicit confirmation.

## 2026-06-20 Document Risk and PDF Planning Layer

Decision: Add deterministic text-based procurement risk analysis and controlled PDF planning without enabling real attachment downloads by default.

Reason:

- RFP text often contains eligibility, performance, consortium, evaluation, and document submission risks that are not visible in notice list metadata alone.
- PDF attachment metadata can be queued and filtered before any download or parsing feature is enabled.
- PDF text extraction must be local-file only, size-limited, explicitly confirmed, and disabled by default.
- HWP/HWPX parsing remains manual review until a controlled parser is selected.
- Local validation must remain fixture-only and must not call real G2B APIs or download attachments.

## 2026-06-21 Lightweight Operations UI

Decision: Add a no-framework browser dashboard served directly by FastAPI at `/ui`.

Reason:

- Operators need a simple local browser surface for fixture recommendation runs, saved run review, saved recommendation filtering, and markdown report viewing.
- A static HTML/CSS/vanilla JavaScript UI keeps the MVP compact and avoids frontend build tooling.
- The UI calls only safe API endpoints by default and keeps fixture mode as the default run mode.
- Report content is read through stored metadata only and is constrained to the configured report directory.
- Generated local operations data can be reset with `scripts/reset_local_ops_data.ps1` without touching `.env` or source fixtures.

## 2026-06-21 Local Operations v1.0 Package

Decision: Package the v2 app as a local operations v1.0 application with safe package
metadata, a local launcher, and package validation script.

Reason:

- Operators need a clear entrypoint beyond the development server script.
- `/ops/package-info` lets the UI and smoke scripts verify version, routes, scripts,
  capabilities, and safety flags without touching SQLite or real APIs.
- The package remains fixture-first by default and never returns service key values.

## 2026-06-21 Local Operations v1.0 Quality Gate

Decision: Add a read-only controlled real operations readiness summary and regression
guards for known Korean text artifacts.

Reason:

- Operators need to confirm real operations prerequisites before an intentional validation run.
- `/ops/real-readiness` reports readiness without calling the real API, connecting to SQLite,
  writing files, or returning service key values.
- Local validation should keep proving fixture-first behavior, no-secret handling, and clean
  Korean UTF-8 output before controlled real usage.

## 2026-06-21 Real Ops Quality Gate Finalization

Decision: Complete controlled real operations scripts and add safe local quality/report
smoke checks to the Local Operations v1.0 validation gate.

Reason:

- Operators need `/ops/quality-summary` and `/ops/report-index` to inspect saved local
  recommendation quality and report metadata without exposing service keys.
- `scripts/validate_local.ps1` should include only fixture-safe and read-only checks; it must
  not run confirmed real API templates.
- `scripts/run_ops_real_controlled.ps1` requires `-ConfirmRealApiCall` so a real operations
  run cannot start by accident.
- `scripts/validate_real_ops_controlled.ps1` supports a safe default validation path and calls
  the controlled real runner only when the explicit confirmation flag is passed.

## 2026-06-21 YOnLab G2B Agent v2 Task 26

Decision: Treat this repository's next work item as v2 Task 26 and keep it separate from the
older `D:\Views\yonlab-bid-agent` task numbering.

Reason:

- Latest v2 baseline before this task was commit `5410627`, which finalized real operations
  validation scripts and the quality gate.
- Operators need one controlled real operations validation path plus clearer report-index and
  quality-summary metadata before routine real usage.
- Local validation must remain fixture-only; a real operations call is allowed only through
  `scripts\validate_real_ops_controlled.ps1 -ConfirmRealApiCall`.

## 2026-06-21 YOnLab G2B Agent v2 Task 27

Decision: Add an offline real operations runtime readiness diagnostic before retrying any
confirmed real operations call.

Reason:

- Task 26 showed `real_ops_disabled`: the confirm flag was present, but the separate
  `YONLAB_AUTO_RUN_REAL_API` operations runtime gate was disabled.
- Operators need a no-secret checklist that distinguishes real API master enablement,
  runtime gate enablement, service key presence, endpoint configuration, and explicit
  confirmation.
- The diagnostic must not call the real API, print `.env` values, write reports, or become
  part of `validate_local.ps1`.

## 2026-06-22 YOnLab G2B Agent v2 Task 28B

Decision: Finalize the MVP release candidate after preserving the successful controlled real
operations result from Task 28.

Reason:

- The controlled real call was already executed exactly once and succeeded as
  `run_20260621_133936_840140`.
- The run created 3 real report metadata records and was reflected in `/ops/report-index`
  and `/ops/quality-summary` with `summary_status=success_with_warnings`.
- The release candidate needs a safe deploy readiness script and documentation, but no
  additional real G2B API calls.
- Runtime artifacts, raw responses, SQLite databases, generated reports, `.env`, and secrets
  must remain out of commits.

## 2026-06-22 YOnLab G2B Agent v2 Task 29

Decision: Prepare release packaging, deployment handoff, GitHub push, and release candidate
tagging without making another real G2B API call.

Reason:

- Operators need a single Windows PowerShell handoff covering setup, offline validation,
  local UI startup, controlled real-run procedure, smoke tests, rollback criteria, and
  troubleshooting.
- `scripts/check_deploy_readiness.ps1` should treat the deployment handoff document as a
  required release artifact.
- The release candidate should be pushed to GitHub and tagged as `v0.1.0-rc1` only after
  fixture-safe validation passes and the working tree is clean.

## 2026-06-28 YOnLab G2B Agent v2 Task 32H

Decision: Add a release closeout harness and make real-ops readiness accept fresh deployment
repository paths based on project structure instead of folder name.

Reason:

- Fresh deployment folders such as `yonlab-g2b-agent-v2-rc2` are valid repository roots and
  should not fail `project_path_ok` merely because the folder name includes a release suffix.
- `.env` absence should block only controlled real readiness and should not be classified as
  a project path failure.
- The closeout harness should default to no real API call, publish the release candidate,
  validate a fresh deployment, and report `ready_after_env_fix` until an operator-provided
  `.env` is ready for one confirmed real run.

## 2026-06-28 YOnLab G2B Agent v2 Task 34H

Decision: Separate base real API configuration readiness from controlled execution readiness
and publish a new release candidate for the first production real run attempt.

Reason:

- `.env` can correctly contain the base real API settings while `YONLAB_AUTO_RUN_REAL_API`
  remains absent because it is a temporary runtime gate, not persistent configuration.
- The release harness should proceed to exactly one controlled real validation only when
  both `-RunControlledRealCall` and `-ConfirmRealApiCall` are present and base real
  configuration is ready.
- The harness must set `YONLAB_AUTO_RUN_REAL_API=true` only in process scope immediately
  before the confirmed call and remove it immediately afterward.

## 2026-06-28 YOnLab G2B Agent v2 Task 35H

Decision: Add deployment-local path consistency checks and a no-real synthetic persistence
check before retrying any controlled real operation.

Reason:

- Task 34H proved the real API call can succeed, but independent smoke returned empty
  because runtime validation and smoke checks could read different storage/report roots.
- `validate_local.ps1` intentionally sets process-level storage/report paths, so the release
  harness must override those values for each deployment folder before readiness, smoke, and
  persistence checks.
- A copied `.env` may contain stale absolute paths from another deployment; this must be
  detected or safely overridden before any additional real API call.
## 2026-06-28 YOnLab G2B Agent v2 Task 37H

Decision: Add routine operations scripts and Windows Task Scheduler helpers without adding
any automatic real API execution path.

Reason:

- The previous production-ready baseline used the Task 37H release candidate with final real run
  `run_20260627_175740_008807` and deployment status `ready`.
- Routine daily checks should verify readiness, quality summary, report index, and optional
  UI health while keeping `YONLAB_AUTO_RUN_REAL_API` removed.
- Windows Task Scheduler registration must point only to the safe daily script. A real G2B
  call remains a manual, explicitly confirmed operation.

## 2026-06-28 YOnLab G2B Agent v2 Task 40G

Decision: Resolve operational script deployment paths dynamically and publish rc7 for safe
scheduler registration.

Reason:

- A controlled real wrapper dry/default block in an rc6 deployment could still write under a
  stale deployment path because some script defaults pinned a specific release folder.
- Safe daily, controlled wrapper, and scheduler registration now resolve `-DeployPath` from
  explicit input first, then the script checkout's repo root, then the current repo root.
- Windows Task Scheduler must target only the active deployment's `run_ops_safe_daily.ps1`;
  the controlled real wrapper remains manual-only and requires explicit confirmation.

## 2026-06-28 YOnLab G2B Agent v2 Task 41G

Decision: Add a commercial Opportunity Inbox and YOnLab recommendation detail view to the
local operations dashboard while keeping all real API execution manually gated.

Reason:

- Operators need a practical bid intelligence screen, not only raw operations status.
- Safe metadata from saved runs can be transformed into deterministic commercial decision
  fields: fit summary, why now, bid strategy, required documents, risks, and next action.
- The dashboard must distinguish demo/fixture/synthetic/real/safe-daily source context and
  must not expose service keys, raw API responses, or `.env` values.

## 2026-06-28 YOnLab G2B Agent v2 Task 42G

Decision: Make the commercial dashboard resilient to frontend render failures and document
PowerShell UTF-8 display diagnostics for Korean operations text.

Reason:

- A malformed dashboard JavaScript template literal can leave `/ui` at `Loading` even when
  backend operations endpoints are healthy.
- Each dashboard section should render independently and show an explicit empty/error state
  when a single endpoint or field is missing.
- Saved opportunity metadata can remain valid UTF-8 while Windows PowerShell displays
  mojibake, so operators need a no-secret encoding check before treating data as corrupted.

## 2026-06-28 YOnLab G2B Agent v2 Task 43G

Decision: Add deterministic commercial decision fields to Opportunity Inbox and Markdown
reports without changing the real API safety model.

Reason:

- Operators need more than score and grade to decide whether to spend proposal-writing time.
- Priority, Go/No-Go, action plan, required documents, and risk categories convert saved
  recommendation metadata into a daily bid review checklist.
- The rules must remain deterministic, fixture/saved-metadata based, and no-real by default.

## 2026-06-28 YOnLab G2B Agent v2 Task 44G

Decision: Promote rc10 as the active production candidate and align the opportunity
Markdown report labels with the business review checklist.

Reason:

- The safe daily scheduler must target the active rc10 safe daily script only.
- Operators need visible `핵심 정보` and `입찰 준비 전략` sections when copying the
  opportunity report into business review notes.
- This remains a deterministic saved-metadata workflow and does not change real API gates.

## 2026-06-28 YOnLab G2B Agent v2 Task 46G

Decision: Add a Daily Review Pack service, API, and dashboard export workflow on top of
Opportunity Inbox data.

Reason:

- Operators need one daily bid review artifact that groups P1/P2/P3/Hold and No-Go notices,
  today actions, document checks, and risk summaries.
- Markdown and CSV exports should be generated from deterministic saved/demo opportunity
  metadata and must not include service keys, `.env` values, raw responses, or local paths.
- The workflow remains no-real by default and does not alter the existing guarded real API
  execution gates.

## 2026-06-28 YOnLab G2B Agent v2 Task 47G

Decision: Review the rc11 operational workflow before adding more product behavior.

Reason:

- rc11 is ready for safe daily operations, but fresh deployments can show empty saved
  operations summaries beside demo Opportunity Inbox and Daily Review Pack data.
- Operators need clearer source-mode language, priority legends, scheduler status, and
  Korean business review labels before the next usability improvement.
- The next task should improve operator clarity only; it should not run a confirmed real G2B
  API call or change the real API safety gates.

## 2026-06-28 YOnLab G2B Agent v2 Task 48G

Decision: Improve operator clarity in `/ui` and Daily Review Pack exports without adding
any real API execution path.

Reason:

- Operators need clear source-mode messaging so demo, fixture, saved, and real data are not
  confused during daily bid review.
- P1/P2/P3/Hold priority meaning, safe daily status, Korean Daily Review Pack labels,
  executive summary, and grouped documents reduce review friction without changing scoring.
- Safe daily dashboard status must be based on latest local safe-log metadata only; it must
  not expose service keys, full local paths, raw logs, or query Windows Scheduler from the
  server.

Release history note:

- `v0.1.0-rc12` and `D:\Deploy\yonlab-g2b-agent-v2-rc12` remain part of the recorded
  release history and must not be rewritten.
- The exact `rc12` fresh deployment was later found to be incomplete for no-real validation:
  the deployment-local pytest suite fails on the safe-daily deployment-path assertion, and
  `validate_real_ops_controlled.ps1` fails before any confirmed real call.
- The corrected and validated Task 48G closeout artifact is `v0.1.0-rc12.1` with deployment
  path `D:\Deploy\yonlab-g2b-agent-v2-rc12.1`.

## 2026-06-29 YOnLab G2B Agent v2 Task 49G

Decision: Add local-only shortlist and review status workflow for saved/demo opportunity
review without changing the guarded real API path.

Reason:

- Operators need to mark notices as shortlisted, reviewing, go, hold, no_go, submitted, or
  archived after first-pass recommendation review.
- Owner and next action should be visible in Opportunity Inbox and Daily Review Pack so
  internal bid review can continue without a separate tracker.
- Full notes remain local-only; exports include status and next action but not private note
  contents, service keys, raw responses, or local absolute paths.

## 2026-06-29 YOnLab G2B Agent v2 Task 50M

Decision: Release the Review Board workflow as `v0.1.0-rc14` only after full no-real
validation, fresh deployment validation, and Review Board workflow smoke checks pass.

Reason:

- Task 50G through 50L added the Review Board summary endpoint, top-of-dashboard `/ui`
  workflow, Inbox filter click-through, Daily Review Pack/export summary, and explicit
  no-real validation coverage.
- The rc14 release should remain deterministic and local-safe: `/ops/review-board`, `/ui`,
  Daily Review Pack/export, and deployment validation must complete without any real G2B API
  call, service key exposure, or `.env` value disclosure.
- Fresh deployment validation should confirm the Review Board workflow from a clean
  deployment path before rc14 is treated as the next release candidate baseline.

## 2026-06-30 YOnLab G2B Agent v2 Task 51F

Decision: Prepare the Decision Memo workflow release as `v0.1.0-rc15` only after full
local no-real validation passes and the same no-real checks are repeated in a fresh
deployment at `D:\Deploy\yonlab-g2b-agent-v2-rc15`.

Release scope:

- safe backend endpoint: `GET /ops/decision-memo/{notice_id}`
- `/ui` Decision Memo panel
- Review Board click to Decision Memo load path
- Opportunity Inbox selected item to Decision Memo load path
- Daily Review Pack/export Decision Memo summary
- known safe fixture notice id: `G2B-SAMPLE-2026-001`

Local no-real validation result before tagging:

- `python -m pytest -q`: pass
- `ruff check app tests`: pass
- `scripts/check_deploy_readiness.ps1`: `deploy_ready=true`
- `scripts/validate_local.ps1`: pass
- `scripts/validate_ops_package.ps1`: pass

No-real safety confirmation:

- `real_api_call_attempted=false`
- `real_network_call_attempted=false`
- `service_key_exposed=false`

Known limitation:

- manual `Prepare` / `Review` / `Hold` / `Reject` persistence is not implemented in rc15
- Decision Memo values are generated from safe local data only

## 2026-06-30 YOnLab G2B Agent v2 rc16 manual decision persistence

Decision: Accept the rc16 manual decision persistence scope as ready for release-candidate
tagging after full local and fresh-deployment no-real validation passes.

Release scope:

- local-only `POST /ops/manual-decision/{notice_id}`
- persisted manual decision enum:
  - `Prepare`
  - `Review`
  - `Hold`
  - `Reject`
- `GET /ops/decision-memo/{notice_id}` prefers persisted manual decisions when present
- `/ui` Decision Memo controls save and reload persisted manual decisions
- Daily Review Pack markdown/summary and CSV export reflect persisted manual decisions

Validation result:

- local `python -m pytest -q`: pass
- local `ruff check app tests`: pass
- local `scripts/check_deploy_readiness.ps1`: `deploy_ready=true`
- local `scripts/validate_local.ps1`: pass
- local `scripts/validate_ops_package.ps1`: pass
- fresh deploy path: `D:\Deploy\yonlab-g2b-agent-v2-rc16`
- fresh deploy `ruff check app tests`: pass
- fresh deploy pytest rc16 subset: pass
- fresh deploy `scripts/check_deploy_readiness.ps1`: `deploy_ready=true`
- fresh deploy `scripts/validate_local.ps1`: pass
- explicit local/deploy smoke:
  - known notice Decision Memo load: pass
  - `Prepare` -> `Review` -> `Hold` -> `Reject` persistence overwrite flow: pass
  - invalid decision returns 4xx: pass
  - unknown notice returns safe `not_found`: pass
  - `/ui` Decision Memo controls and JS save hook visible: pass
  - Daily Review Pack and CSV export reflect persisted manual decision: pass

No-real safety confirmation:

- `real_api_call_attempted=false`
- `real_network_call_attempted=false`
- `service_key_exposed=false`

Fallback behavior preserved:

- when no persisted manual decision exists, rc15 generated/default Decision Memo behavior
  remains the active fallback
- private manual-decision note content is not added as a dedicated CSV column

## 2026-07-01 YOnLab G2B Agent v2 rc17 validation environment hardening

Decision: Accept the rc17 validation environment hardening scope as ready for the
next release-candidate tag after wrapper-based local and fresh-deploy no-real
validation passes.

Release scope:

- add `scripts/validate_release.ps1` as the preferred Windows release validation entrypoint
- resolve the repo root from the wrapper script location
- require repo-local Python at `.venv\Scripts\python.exe`
- run `pytest` and `ruff` through the repo-local interpreter
- delegate to `scripts/check_deploy_readiness.ps1`
- delegate to `scripts/validate_local.ps1`
- delegate to `scripts/validate_ops_package.ps1`
- document the wrapper in README, testing strategy, operations runbook, and deployment handoff

Validation result:

- local wrapper `powershell -ExecutionPolicy Bypass -File scripts/validate_release.ps1`: pass
- local direct `python -m pytest -q`: failed on the machine-global Python because `pytest`
  was not installed outside the repo-local virtual environment
- local direct `python -m ruff check app tests`: failed on the machine-global Python because
  `ruff` was not installed outside the repo-local virtual environment
- local direct `.ps1` invocation without explicit bypass remained subject to the machine
  PowerShell execution policy
- fresh deploy path: `D:\Deploy\yonlab-g2b-agent-v2-rc17`
- fresh deploy `.env`: absent by design
- fresh deploy `.venv` strategy: junction to the validated development virtual environment
- fresh deploy wrapper `powershell -ExecutionPolicy Bypass -File scripts/validate_release.ps1`: pass
- fresh deploy `powershell -ExecutionPolicy Bypass -File scripts/check_deploy_readiness.ps1`:
  `deploy_ready=true`
- fresh deploy `powershell -ExecutionPolicy Bypass -File scripts/validate_local.ps1`: pass
- fresh deploy `powershell -ExecutionPolicy Bypass -File scripts/validate_ops_package.ps1`: pass

No-real safety confirmation:

- `real_api_call_attempted=false`
- `real_network_call_attempted=false`
- `service_key_exposed=false`

Behavior preservation:

- rc16 manual decision persistence behavior remains unchanged
- product code was not changed during the final rc17 validation/decision-log step
