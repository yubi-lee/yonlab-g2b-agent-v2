# YOnLab G2B Agent v2

Fixture-based operational MVP for YOnLab-specific G2B/Narajangteo bid recommendation.

The app normalizes procurement notices, evaluates YOnLab eligibility, detects risks, calculates a deterministic 100-point match score, and generates a Korean markdown recommendation report.

This repository is independent from the previous v1 project:

- Previous repository: `D:\Views\yonlab-bid-agent`
- Current repository: `D:\Views\yonlab-g2b-agent-v2`

## Current Limitation

This is a fixture-based MVP. Real G2B/Public Data Portal API calls are disabled by default and are not used by tests, demo endpoints, or smoke scripts.

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

## Endpoints

- `GET /health`
- `GET /profile/yonlab`
- `GET /fixtures/g2b/notices`
- `POST /notices/normalize`
- `POST /recommendations/score`
- `POST /recommendations/report`
- `POST /demo/recommendations`

## Demo Recommendations

Compact output:

```powershell
$body = @{
  include_reports = $false
  limit = 5
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/demo/recommendations" `
  -ContentType "application/json; charset=utf-8" `
  -Body $body
```

Full output with reports:

```powershell
$body = @{
  include_reports = $true
  limit = 5
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/demo/recommendations" `
  -ContentType "application/json; charset=utf-8" `
  -Body $body
```

No body or `{}` also works and uses local fixture notices.

## Recommendation Report Example

```powershell
$body = @{
  "공고명" = "서울 AI 소프트웨어 개발"
  "수요기관" = "테스트기관"
  "추정가격" = "55,000,000원"
  "입찰마감일시" = "2026-07-20"
  "지역제한" = "서울특별시"
  "참가자격" = "소프트웨어사업자, 소기업, 창업기업 우대"
  "과업내용" = "AI Agent 정보시스템개발서비스 클라우드 시스템 구축"
} | ConvertTo-Json -Depth 5

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/recommendations/report" `
  -ContentType "application/json; charset=utf-8" `
  -Body $body
```

## Smoke Scripts

Start the server first with `.\scripts\dev_start.ps1`, then run in another terminal:

```powershell
.\scripts\smoke_demo.ps1
.\scripts\smoke_report.ps1
```

Set `YONLAB_G2B_BASE_URL` to target a non-default local URL.
