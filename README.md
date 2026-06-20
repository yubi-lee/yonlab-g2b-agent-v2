# YOnLab G2B Agent v2

YOnLab-specific G2B/Narajangteo AI bid recommendation application.

This repository is a new Agent-first implementation and must remain independent from the previous repository:

- Previous repository: `D:\Views\yonlab-bid-agent`
- Current repository: `D:\Views\yonlab-g2b-agent-v2`

## Current phase

Phase 1: Initial FastAPI baseline.

Implemented:

- Minimal FastAPI app
- `GET /health`
- pytest health test
- project guidance files
- initial docs and scripts

Not implemented yet:

- G2B API integration
- G2B fixtures
- bid normalizer
- YOnLab eligibility engine
- scoring engine
- recommendation report generator
- database
- UI

## Quick start

```powershell
Set-Location D:\Views\yonlab-g2b-agent-v2
.\.venv\Scripts\Activate.ps1
python -m pytest -q
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "app": "YOnLab G2B Agent v2"
}
```

## Development rule

Fixture-first. Test-first. No real API call unless explicitly confirmed.
