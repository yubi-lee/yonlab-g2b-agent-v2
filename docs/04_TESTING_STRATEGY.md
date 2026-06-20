# 04 Testing Strategy

## Baseline Command

```powershell
Set-Location D:\Views\yonlab-g2b-agent-v2
.\.venv\Scripts\Activate.ps1
python -m pytest -q
```

## Current Test Coverage

- `tests/test_app_health.py`: health endpoint.
- `tests/test_yonlab_profile.py`: fixed YOnLab profile.
- `tests/test_g2b_normalizer.py`: fixture loading and field normalization.
- `tests/test_g2b_client.py`: guarded real client behavior using mocks only.
- `tests/test_g2b_pipeline_api.py`: `/g2b/config`, `/g2b/search`, `/g2b/recommendations`.
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
