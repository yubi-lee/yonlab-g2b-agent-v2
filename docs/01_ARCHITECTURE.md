# 01 Architecture

## Layers

```text
FastAPI routes
  -> G2B fixture loader / normalizer
  -> domain models
  -> eligibility and risk analysis
  -> 100-point score engine
  -> deterministic markdown report
```

## Modules

- `app/domain/yonlab_profile.py`: fixed YOnLab profile.
- `app/domain/bid_notice.py`: normalized procurement notice model.
- `app/domain/recommendation.py`: eligibility, risk, score, report, and demo response models.
- `app/integrations/g2b/fixtures.py`: local fixture loader only.
- `app/integrations/g2b/normalizer.py`: Korean and G2B-like field mapping.
- `app/scoring/eligibility.py`: first-pass YOnLab eligibility signals.
- `app/scoring/risk_analyzer.py`: deterministic risk detection.
- `app/scoring/score_engine.py`: 100-point deterministic recommendation score.
- `app/reports/markdown_report.py`: Korean markdown report generator.
- `app/api/routes.py`: API endpoints for profile, fixtures, normalization, scoring, reports, and demo ranking.

## Data Flow

```text
raw notice JSON
-> normalize_g2b_notice
-> evaluate_eligibility + analyze_risks
-> score_notice
-> generate_markdown_report
-> API response
```

## Constraints

- No database is required.
- No frontend UI is required.
- No LLM calls are used.
- No real G2B/Public Data Portal call is made by default.
- Domain and scoring logic stay independent from FastAPI.
