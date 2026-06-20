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
- `tests/test_yonlab_eligibility.py`: eligibility and first-pass risk signals.
- `tests/test_score_engine.py`: 100-point scoring and risk penalty behavior.
- `tests/test_markdown_report.py`: deterministic Korean report sections.
- `tests/test_recommendation_api.py`: API contract for profile, fixtures, normalize, score, report.
- `tests/test_demo_recommendations.py`: ranked fixture demo recommendations.

## Rules

- Tests must not call real G2B/Public Data Portal APIs.
- Tests must not require `.env`, secrets, a database, frontend UI, or an LLM.
- Add fixture cases before integrating real API behavior.
- `python -m pytest -q` must remain the standard validation command.
