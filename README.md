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
- Tests do not call any real G2B/Public Data Portal API.
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
- `G2B_LIST_ENDPOINT_PATH` configured
- request body includes `confirm_real_api_call=true`
- request `mode` is `real`

If any condition is missing, the API returns a controlled error response and does not call the network. The service key is never returned by `/g2b/config`, errors, tests, or docs.

## `.env.example` Guidance

Copy values from `.env.example` only when you are ready to configure a local environment. Do not commit `.env`.

Important defaults:

```env
G2B_ENABLE_REAL_API=false
G2B_API_SERVICE_KEY=
G2B_FIXTURE_MODE=true
```

## Smoke Scripts

Start the server first with `.\scripts\dev_start.ps1`, then run in another terminal:

```powershell
.\scripts\smoke_g2b_config.ps1
.\scripts\smoke_g2b_search_fixture.ps1
.\scripts\smoke_g2b_recommend_fixture.ps1
.\scripts\smoke_demo.ps1
.\scripts\smoke_report.ps1
```

Set `YONLAB_G2B_BASE_URL` to target a non-default local URL.
