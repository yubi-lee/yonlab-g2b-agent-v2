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
