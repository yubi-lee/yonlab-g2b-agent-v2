# YOnLab G2B Agent v2

Operational MVP for YOnLab-specific G2B/Narajangteo bid recommendation.

The app supports two deterministic pipelines:

- Fixture pipeline: local sample notices, enabled by default.
- Guarded real API pipeline: Public Data Portal/G2B HTTP client, blocked unless explicitly enabled and confirmed.

It normalizes procurement notices, evaluates YOnLab eligibility, detects risks, calculates a 100-point match score, ranks recommendations, and generates a Korean markdown report.

This repository is independent from the previous v1 project:

- Previous repository: `D:\Views\yonlab-bid-agent`
- Current repository: `D:\Views\yonlab-g2b-agent-v2`

## Current Status

- FastAPI MVP with fixture recommendations.
- Guarded real API client and request models.
- Real API calls are disabled by default.
- Real response capture is disabled by default and writes only sanitized JSON when enabled.
- First controlled real G2B smoke succeeded; real BidPublicInfoService fields are normalized into recommendation inputs.
- Real search/recommendation responses include a deterministic detail-analysis queue with notice detail URLs, attachment URL/file-name metadata, and risk metadata. Attachments are not downloaded.
- Text-based document risk analysis and PDF candidate planning are available through controlled, fixture-safe endpoints.
- PDF text extraction is disabled by default and only reads local PDF files when explicitly confirmed and enabled.
- Tests do not call any real G2B/Public Data Portal API.
- Korean UTF-8 regression tests cover fixture data, API responses, and report output.
- Local SQLite operations storage and a lightweight browser UI are available.
- Local operations v1.0 packaging adds safe package metadata plus launcher and validation scripts.
- Controlled real operations readiness can be inspected without calling the real API.
- MVP release candidate validation includes one successful controlled real operations run:
  `run_20260621_133936_840140`.
- No frontend build tooling, external database server, or LLM is required.

## Run Tests

```powershell
Set-Location D:\Views\yonlab-g2b-agent-v2
.\.venv\Scripts\Activate.ps1
python -m pytest -q
```

Or:

```powershell
.\scripts\run_tests.ps1
```

Preferred full local validation, including pytest, temporary local server startup, fixture smoke scripts, and shutdown:

```powershell
.\scripts\validate_local.ps1
```

## Start Server

```powershell
Set-Location D:\Views\yonlab-g2b-agent-v2
.\scripts\dev_start.ps1
```

Packaged local operations launcher:

```powershell
.\scripts\start_local_ops.ps1
```

Open:

```text
http://127.0.0.1:8000/ui
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/health
```

`GET /` redirects to `/ui`.

## Existing Endpoints

- `GET /`
- `GET /ui`
- `GET /health`
- `GET /ops/package-info`
- `GET /ops/real-readiness`
- `GET /profile/yonlab`
- `GET /fixtures/g2b/notices`
- `POST /notices/normalize`
- `POST /recommendations/score`
- `POST /recommendations/report`
- `POST /demo/recommendations`

## Operations UI and Storage

The lightweight operations dashboard is served by FastAPI with static HTML, CSS, and
vanilla JavaScript. It does not use React, Vue, Node, Streamlit, or a separate frontend app.

Open:

```text
http://127.0.0.1:8000/ui
```

From the dashboard you can:

- inspect safe system status from `/health`, `/g2b/config`, `/g2b/real-readiness`, and `/ops/real-readiness`.
- run a fixture recommendation job through `/ops/run-recommendations`.
- view recent saved runs from `/ops/runs`.
- view saved recommendations from `/ops/recommendations`.
- open saved markdown reports through `/ops/report-content/{run_id}/{notice_id}`.
- inspect enriched report metadata through `/ops/report-index` and aggregate quality state through `/ops/quality-summary`.
- review commercial candidates in Opportunity Inbox, then open or download a copy-ready
  Markdown detail report for internal bid review.
- use Daily Review Pack to summarize today's P1/P2/P3/Hold opportunities, actions,
  document checks, and risk counts, then download Markdown or CSV for bid review meetings.

The dashboard JavaScript is intentionally section-safe: if one metadata endpoint fails, the
affected panel shows an explicit error or empty state instead of leaving every card stuck at
`Loading`. If `/ui` still shows persistent `Loading`, first check that
`/ui/static/dashboard.js` loads without browser-console syntax errors, then verify
`/ops/quality-summary`, `/ops/report-index`, and `/ops/opportunity-inbox` individually.

Default operations mode is fixture. Real API mode still requires `.env` configuration,
`confirm_real_api_call=true`, and the existing real API safety gates. Service key values are
never shown in the UI or operations responses.

Generated local operations data is ignored by Git:

```text
data/ops/
data/reports/
```

To reset generated local operations data without touching `.env` or source fixtures:

```powershell
.\scripts\reset_local_ops_data.ps1
```

The reset script removes only generated local operation data under `data/ops`,
`data/reports`, `data/downloaded`, and `data/extracted`.

Operations endpoints:

- `GET /ops/package-info`
- `GET /ops/real-readiness`
- `GET /ops/quality-summary`
- `GET /ops/report-index`
- `POST /ops/run-recommendations`
- `GET /ops/runs`
- `GET /ops/runs/{run_id}`
- `GET /ops/recommendations`
- `GET /ops/reports/{run_id}`
- `GET /ops/report-content/{run_id}/{notice_id}`
- `GET /ops/daily-review-pack`
- `GET /ops/daily-review-pack/markdown`
- `GET /ops/daily-review-pack/csv`

For the packaged local operations workflow, see `docs/07_LOCAL_OPERATIONS_V1.md`.
For release deployment handoff, see `docs/07_DEPLOYMENT_HANDOFF.md`.

## Production-Ready Operations Baseline

Current production-ready local deployment baseline:

- release candidate: `v0.1.0-rc7`
- commit: created from the Task 40G operational targeting fix
- previous controlled real run: `run_20260627_175740_008807`
- deployment status: `ready`

Routine operations should use the no-real safe daily script. In a deployment checkout,
omitting `-DeployPath` resolves to that checkout's repo root; scheduled registration should
still pass the active deployment path explicitly:

```powershell
.\scripts\run_ops_safe_daily.ps1 -DeployPath D:\Deploy\yonlab-g2b-agent-v2-rc7
```

Register the safe daily Windows scheduled task with a dry-run first:

```powershell
.\scripts\register_ops_safe_daily_task.ps1 `
  -DeployPath D:\Deploy\yonlab-g2b-agent-v2-rc7 `
  -WhatIf
```

The scheduled task targets `run_ops_safe_daily.ps1` only. It does not call the real G2B API.
The controlled real wrapper is manual-only and requires explicit operator confirmation; it
must not be registered as a daily task.
## G2B Endpoints

- `GET /g2b/config`
- `GET /g2b/endpoint-presets`
- `GET /g2b/real-readiness`
- `POST /g2b/search`
- `POST /g2b/recommendations`
- `POST /g2b/detail-links`
- `POST /g2b/detail-analysis-queue`
- `POST /g2b/attachment-download-plan`
- `POST /g2b/attachment-analysis-plan`
- `POST /g2b/document-risk-analysis`
- `POST /g2b/pdf-analysis-candidates`
- `POST /g2b/pdf-text-analysis`

## Swagger Testing Guide

Use `/docs` with practical fixture-safe examples instead of Swagger placeholders such as
`"string"` or `{"additionalProp1": {}}`.

`POST /demo/recommendations` fixture compact:

```json
{
  "include_reports": false,
  "limit": 5
}
```

`POST /demo/recommendations` fixture full:

```json
{
  "include_reports": true,
  "limit": 3
}
```

`POST /g2b/recommendations` fixture recommendation:

```json
{
  "mode": "fixture",
  "keyword": "AI",
  "page_no": 1,
  "num_rows": 5,
  "active_only": false,
  "confirm_real_api_call": false,
  "include_reports": false
}
```

`POST /g2b/recommendations` controlled real template:

```json
{
  "mode": "real",
  "keyword": "AI",
  "start_date": "2026-06-01",
  "end_date": "2026-06-20",
  "page_no": 1,
  "num_rows": 3,
  "active_only": false,
  "confirm_real_api_call": true,
  "include_reports": false
}
```

`POST /g2b/document-risk-analysis` text-only fixture example:

```json
{
  "source_name": "sample-rfp-text",
  "text": "AI 소프트웨어 개발, 최근 3년 유사 사업 수행실적, 공동수급불허, 기술평가 90점",
  "include_positive_signals": true
}
```

`POST /g2b/pdf-analysis-candidates` fixture example:

```json
{
  "mode": "fixture",
  "keyword": "AI",
  "page_no": 1,
  "num_rows": 3,
  "confirm_real_api_call": false
}
```

`POST /g2b/pdf-text-analysis` is local-file only and blocked unless
`confirm_pdf_analysis=true`. It never downloads from URLs. HWP/HWPX content extraction is
not implemented; those attachments remain manual review.

## Fixture Mode Example

```powershell
$body = @{
  mode = "fixture"
  keyword = "AI"
  page_no = 1
  num_rows = 10
  confirm_real_api_call = $false
} | ConvertTo-Json -Depth 5

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/g2b/search" `
  -ContentType "application/json; charset=utf-8" `
  -Body $body
```

Fixture recommendations:

```powershell
$body = @{
  mode = "fixture"
  keyword = "AI"
  include_reports = $false
  confirm_real_api_call = $false
} | ConvertTo-Json -Depth 5

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/g2b/recommendations" `
  -ContentType "application/json; charset=utf-8" `
  -Body $body
```

Set `active_only=true` on `/g2b/search` or `/g2b/recommendations` to filter out notices whose normalized deadline has already passed. Notices with missing deadlines are kept and receive a `deadline_missing` recommendation risk.

## Real API Safety Rules

Real API calls require all of the following:

- `G2B_ENABLE_REAL_API=true`
- `G2B_API_SERVICE_KEY` configured
- `G2B_LIST_ENDPOINT_PATH` configured, or `G2B_ENDPOINT_PRESET` set to a known preset
- request body includes `confirm_real_api_call=true`
- request `mode` is `real`

If any condition is missing, the API returns a controlled error response and does not call the network. The service key is never returned by `/g2b/config`, errors, tests, or docs.

## Controlled Real G2B Smoke

Fixture mode remains the default and recommended local path. A real G2B/Public Data Portal smoke should only be run from a local `.env` after you have configured a private service key and endpoint path.

Required local settings:

```env
G2B_ENABLE_REAL_API=true
G2B_API_SERVICE_KEY=<your local key>
G2B_LIST_ENDPOINT_PATH=/1230000/ad/BidPublicInfoService/getBidPblancListInfoServcPPSSrch
```

The approved service endpoint is `https://apis.data.go.kr/1230000/ad/BidPublicInfoService`. For real list/search calls, use a business-operation path such as `/1230000/ad/BidPublicInfoService/getBidPblancListInfoServcPPSSrch`.

Every real request must also include `confirm_real_api_call=true`. The template smoke scripts use `num_rows=3` and explicit `start_date`/`end_date` values for a small first real check.

Optional response capture:

```env
G2B_CAPTURE_REAL_RESPONSES=false
G2B_CAPTURE_DIR=data/captured/g2b
```

Captured responses are disabled by default. When enabled, captures are written as UTF-8 JSON with request secrets masked. `data/captured/` is ignored by Git.

Before the first confirmed smoke, run the offline readiness check:

```powershell
.\scripts\validate_g2b_real_readiness.ps1
.\scripts\validate_g2b_real_ops_readiness.ps1
.\scripts\check_real_ops_readiness.ps1
.\scripts\validate_real_ops_controlled.ps1
.\scripts\show_g2b_real_env_status.ps1
```

These checks cover no-secret rules, endpoint preset readiness, current endpoint path, controlled operations readiness, and relevant tests without calling the real API. Restart the FastAPI server after changing `.env` so the new endpoint path is loaded.

Task 26 produced `real_ops_disabled` because `confirm_real_api_call=true` was present but
the separate operations runtime gate was still disabled. A controlled real operations run
requires all of these conditions before the confirmed command is useful:

- `G2B_ENABLE_REAL_API=true`
- `G2B_API_SERVICE_KEY` present in local `.env`
- `G2B_API_BASE_URL` configured
- `G2B_LIST_ENDPOINT_PATH` or `G2B_ENDPOINT_PRESET` configured
- `YONLAB_AUTO_RUN_REAL_API=true` for the short controlled validation window only
- explicit confirmed command or request flag

`scripts/check_real_ops_readiness.ps1` prints boolean/status fields only. It does not call
the real API, connect to the server, print service key values, or write reports.

Controlled real operations result for the MVP release candidate:

- run_id: `run_20260621_133936_840140`
- status: `success`
- real report metadata: 3 records
- `/ops/report-index`: reflected
- `/ops/quality-summary`: reflected
- summary status: `success_with_warnings`

Do not repeat confirmed real validation during routine local checks. Use `validate_local.ps1`
for offline validation, and open `YONLAB_AUTO_RUN_REAL_API=true` only in the current
operator-controlled PowerShell session for an intentional real validation window.

## MVP Release Candidate Checklist

Before packaging or handoff:

- Run `ruff check app tests`.
- Run `python -m pytest -q`.
- Run `scripts\check_real_ops_readiness.ps1`.
- Run `scripts\validate_real_ops_controlled.ps1` without `-ConfirmRealApiCall`.
- Run `scripts\check_deploy_readiness.ps1`.
- Run `scripts\validate_local.ps1`.
- Confirm `.env`, service keys, captured raw responses, SQLite DBs, and generated reports are not staged.
- Keep `YONLAB_AUTO_RUN_REAL_API` unset except during one controlled real validation window.

Required deployment environment variable names:

- `G2B_ENABLE_REAL_API`
- `G2B_API_BASE_URL`
- `G2B_API_SERVICE_KEY`
- `G2B_LIST_ENDPOINT_PATH` or `G2B_ENDPOINT_PRESET`
- `YONLAB_STORAGE_DB_PATH`
- `YONLAB_REPORT_DIR`
- `YONLAB_AUTO_RUN_REAL_API`

For one intentional controlled operations run, use:

```powershell
.\scripts\validate_real_ops_controlled.ps1 -ConfirmRealApiCall
```

Without `-ConfirmRealApiCall`, the controlled real ops validation exits before the real
operation step. With the flag, it performs one guarded real run and then checks whether the
new run is reflected in `/ops/quality-summary` and `/ops/report-index`. Service key values
stay in local `.env` only and are never shown by the UI, quality summary, report index, or
validation scripts.

Endpoint preset guidance:

- `custom`: use `G2B_LIST_ENDPOINT_PATH` from local `.env`.
- `approved_bid_public_info_service`: approved base path `/1230000/ad/BidPublicInfoService`.
- `approved_bid_public_info_service_base`: approved base path; useful for diagnostics.
- `servc_pps_search`: recommended first YOnLab service-search operation path.

For full setup steps, see `docs/05_REAL_G2B_SMOKE_CHECKLIST.md`.

## Release Closeout Harness

The release closeout harness packages the validated commit into a new release candidate,
pushes `main` and the tag, creates a fresh deployment clone, installs dependencies, runs
offline validation, and verifies `/ui`, `/ops/quality-summary`, and `/ops/report-index`.
By default it does not call the real G2B API:

```powershell
.\scripts\run_release_closeout_harness.ps1 -ReleaseTag v0.1.0-rc5
```

If the fresh deployment has no `.env`, the expected final status is
`ready_after_env_fix`. The readiness output separates base real configuration from
controlled execution readiness. Keep `YONLAB_AUTO_RUN_REAL_API=true` out of persistent
`.env`; the harness sets it only as a process variable during the confirmed controlled
window and removes it immediately afterward. A controlled real operation is allowed only
when both flags are present and base real configuration is ready:

```powershell
.\scripts\run_release_closeout_harness.ps1 `
  -ReleaseTag v0.1.0-rc5 `
  -RunControlledRealCall `
  -ConfirmRealApiCall
```

When copying `.env` between deployment folders, check storage/report path consistency before
any real call. Stale absolute `YONLAB_STORAGE_DB_PATH` or `YONLAB_REPORT_DIR` values can make
the real run and later smoke checks read different stores. Use the synthetic check first; it
does not call the real G2B API:

```powershell
.\scripts\run_release_closeout_harness.ps1 `
  -ReleaseTag v0.1.0-rc5 `
  -DeployFolderName yonlab-g2b-agent-v2-rc5 `
  -RunSyntheticPersistenceCheck `
  -SkipPush
```

## `.env.example` Guidance

Copy values from `.env.example` only when you are ready to configure a local environment. Do not commit `.env`.

Important defaults:

```env
G2B_ENABLE_REAL_API=false
G2B_API_SERVICE_KEY=
G2B_LIST_ENDPOINT_PATH=/1230000/ad/BidPublicInfoService/getBidPblancListInfoServcPPSSrch
G2B_FIXTURE_MODE=true
G2B_CAPTURE_REAL_RESPONSES=false
G2B_CAPTURE_DIR=data/captured/g2b
```

## Smoke Scripts

For routine local validation, prefer:

```powershell
.\scripts\validate_local.ps1
```

For manual smoke checks, start the server first with `.\scripts\dev_start.ps1`, then run in another Windows PowerShell terminal:

```powershell
Set-Location D:\Views\yonlab-g2b-agent-v2
.\.venv\Scripts\Activate.ps1
.\scripts\smoke_g2b_config.ps1
.\scripts\smoke_g2b_endpoint_presets.ps1
.\scripts\smoke_g2b_real_readiness.ps1
.\scripts\smoke_ops_real_readiness.ps1
.\scripts\smoke_ops_quality_summary.ps1
.\scripts\smoke_ops_report_index.ps1
.\scripts\smoke_g2b_search_fixture.ps1
.\scripts\smoke_g2b_recommend_fixture.ps1
.\scripts\smoke_ui_health.ps1
.\scripts\smoke_ops_ui_flow.ps1
.\scripts\smoke_g2b_real_guard_blocked.ps1
.\scripts\smoke_demo.ps1
.\scripts\smoke_report.ps1
```

The smoke scripts set console output to UTF-8 and decode API response streams as UTF-8 so Korean text such as `서울 AI 기반 행정지원 업무 자동화 시스템 구축`, `적극 추천`, and `와이온랩 맞춤 추천 공고` prints correctly.

Set `YONLAB_G2B_BASE_URL` to target a non-default local URL.

Real API templates are provided for explicit manual use only:

```powershell
.\scripts\smoke_g2b_real_confirmed_template.ps1
.\scripts\smoke_g2b_real_recommend_template.ps1
```

Do not add service keys to these scripts. Keep keys in local `.env` only.

## Korean UTF-8 Regression Coverage

Korean UTF-8 regression tests are included because G2B/Narajangteo data contains Korean text in notice titles, agencies, qualification text, and descriptions.

If Korean text looks corrupted only in Windows PowerShell while browser/API bytes are valid,
set the console output encoding before smoke checks:

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
```

## Commercial Opportunity Inbox

The local `/ui` dashboard now includes an Opportunity Inbox for commercial bid review.
It summarizes saved operations recommendations, or shows clearly badged demo opportunities
when no local run data exists. Operators can filter by keyword, grade, risk level, and
source badge, then open a copy-ready YOnLab recommendation detail report in Markdown.

Commercial decision fields are deterministic and metadata-only:

- Decision Label: `strong_recommend`, `recommend`, `consider`, `hold`, `not_recommended`.
- Bid Priority: `P1`, `P2`, `P3`, or `Hold` for daily review ordering.
- Go/No-Go: `Go`, `Go after RFP review`, `Review with partner`, `Hold`, or `No-Go`.
- Risk Categories: deadline, eligibility, scope, budget, evidence, and consortium risk.

Use `P1` and `Go` items for immediate review, `P2/P3` items for RFP confirmation, and
`Hold` or `No-Go` items for low-priority monitoring. These fields do not trigger real API
calls and do not expose service keys.

The opportunity Markdown report includes `핵심 정보`, `입찰 준비 전략`, required
documents, risk categories, and recommended action so it can be used directly in business
review notes.

Safe metadata endpoints:

- `GET /ops/opportunity-inbox`
- `GET /ops/opportunity-inbox/{notice_id}`
- `GET /ops/opportunity-report/{notice_id}`

These endpoints do not trigger real G2B API calls and never include `.env` values, service
keys, raw API responses, or runtime DB contents beyond safe recommendation metadata.
