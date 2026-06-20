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
