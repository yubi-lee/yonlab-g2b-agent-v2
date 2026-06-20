# 04 Testing Strategy

## Baseline Command

```powershell
Set-Location D:\Views\yonlab-g2b-agent-v2
.\.venv\Scripts\Activate.ps1
python -m pytest -q
```

## Preferred Local Validation

Use one command for local end-to-end validation:

```powershell
.\scripts\validate_local.ps1
```

The script runs `python -m pytest -q`, starts a temporary FastAPI server on `127.0.0.1:8000`, waits for `/health`, runs fixture smoke scripts, runs the Korean markdown report smoke check, and stops the server in a `finally` block.

## Current Test Coverage

- `tests/test_app_health.py`: health endpoint.
- `tests/test_yonlab_profile.py`: fixed YOnLab profile.
- `tests/test_g2b_normalizer.py`: fixture loading and field normalization.
- `tests/test_g2b_client.py`: guarded real client behavior using mocks only.
- `tests/test_g2b_pipeline_api.py`: `/g2b/config`, `/g2b/search`, `/g2b/recommendations`.
- `tests/test_korean_utf8_pipeline.py`: Korean fixture/API/report encoding regression coverage.
- `tests/test_yonlab_eligibility.py`: eligibility and first-pass risk signals.
- `tests/test_score_engine.py`: 100-point scoring and risk penalty behavior.
- `tests/test_markdown_report.py`: deterministic Korean report sections.
- `tests/test_recommendation_api.py`: API contract for MVP endpoints.
- `tests/test_demo_recommendations.py`: ranked fixture demo recommendations.
- `tests/test_smoke_scripts.py`: smoke script and line-ending policy presence.

## Real API Test Rule

Tests must never call the real G2B/Public Data Portal API. Real API behavior is verified through:

- disabled-mode blocking.
- missing-confirmation blocking.
- missing-service-key blocking.
- mocked httpx success response.
- mocked empty response.

## Rules

- Tests must not require `.env`, secrets, a database, frontend UI, or an LLM.
- Add fixture cases before expanding real API behavior.
- `python -m pytest -q` must remain the standard validation command.

## Korean UTF-8 Regression Rule

Korean UTF-8 regression tests are included because G2B/Narajangteo data contains Korean text in notice titles, agencies, qualification text, and descriptions.

PowerShell smoke scripts are UTF-8 guarded because Windows PowerShell can otherwise corrupt Korean-heavy G2B/Narajangteo JSON and markdown output.

The regression suite checks:

- fixture files are valid UTF-8 without BOM.
- fixture loader preserves Korean titles.
- `/g2b/search` and `/g2b/recommendations` preserve Korean response fields.
- `/recommendations/report` preserves Korean markdown headings.
- common mojibake fragments do not appear in Korean content fields.
