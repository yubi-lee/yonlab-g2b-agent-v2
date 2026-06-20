# YOnLab G2B Agent v2

YOnLab-specific G2B/Narajangteo bid recommendation MVP.

This repository is independent from the previous v1 project:

- Previous repository: `D:\Views\yonlab-bid-agent`
- Current repository: `D:\Views\yonlab-g2b-agent-v2`

The MVP is fixture-first and deterministic. Real G2B/Public Data Portal API access is disabled by default and is not used by tests or demo endpoints.

## What It Does

```text
Raw procurement notice
-> normalized BidNotice
-> YOnLab eligibility analysis
-> risk analysis
-> 100-point match score
-> recommendation level
-> Korean markdown recommendation report
-> FastAPI endpoint response
```

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

## Key Endpoints

- `GET /health`
- `GET /profile/yonlab`
- `GET /fixtures/g2b/notices`
- `POST /notices/normalize`
- `POST /recommendations/score`
- `POST /recommendations/report`
- `POST /demo/recommendations`

## Example Report Request

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

## Fixture Rule

The app ships with local sample notices at `data/fixtures/g2b/sample_notices.json`. Default behavior never calls a real G2B/Public Data Portal API and does not require an API key, database, frontend, or LLM.
