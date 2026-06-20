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
- Tests do not call any real G2B/Public Data Portal API.
- Korean UTF-8 regression tests cover fixture data, API responses, and report output.
- No database, frontend, or LLM is required.

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

Open:

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/health
```

## Existing Endpoints

- `GET /health`
- `GET /profile/yonlab`
- `GET /fixtures/g2b/notices`
- `POST /notices/normalize`
- `POST /recommendations/score`
- `POST /recommendations/report`
- `POST /demo/recommendations`

## G2B Endpoints

- `GET /g2b/config`
- `GET /g2b/endpoint-presets`
- `GET /g2b/real-readiness`
- `POST /g2b/search`
- `POST /g2b/recommendations`

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
.\scripts\show_g2b_real_env_status.ps1
```

It checks no-secret rules, endpoint preset readiness, current endpoint path, and relevant tests without calling the real API. Restart the FastAPI server after changing `.env` so the new endpoint path is loaded.

Endpoint preset guidance:

- `custom`: use `G2B_LIST_ENDPOINT_PATH` from local `.env`.
- `approved_bid_public_info_service`: approved base path `/1230000/ad/BidPublicInfoService`.
- `approved_bid_public_info_service_base`: approved base path; useful for diagnostics.
- `servc_pps_search`: recommended first YOnLab service-search operation path.

For full setup steps, see `docs/05_REAL_G2B_SMOKE_CHECKLIST.md`.

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
.\scripts\smoke_g2b_search_fixture.ps1
.\scripts\smoke_g2b_recommend_fixture.ps1
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
