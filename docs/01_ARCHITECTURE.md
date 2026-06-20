# 01 Architecture

## Layers

```text
FastAPI routes
  -> G2B search mode router
  -> fixture loader or guarded real API client
  -> normalizer
  -> domain models
  -> eligibility and risk analysis
  -> 100-point score engine
  -> deterministic markdown report
```

## Modules

- `app/domain/yonlab_profile.py`: fixed YOnLab profile.
- `app/domain/bid_notice.py`: normalized procurement notice model.
- `app/domain/recommendation.py`: eligibility, risk, score, report, and demo response models.
- `app/domain/search.py`: G2B search and recommendation request/response models.
- `app/integrations/g2b/fixtures.py`: local fixture loader and deterministic filter.
- `app/integrations/g2b/normalizer.py`: Korean and G2B-like field mapping.
- `app/integrations/g2b/client.py`: guarded httpx client for real API calls.
- `app/integrations/g2b/capture.py`: optional sanitized real response capture.
- `app/integrations/g2b/errors.py`: sanitized client errors.
- `app/integrations/g2b/presets.py`: endpoint path preset definitions and resolver.
- `app/integrations/g2b/readiness.py`: offline real API readiness summary.
- `app/scoring/eligibility.py`: first-pass YOnLab eligibility signals.
- `app/scoring/risk_analyzer.py`: deterministic risk detection.
- `app/scoring/score_engine.py`: 100-point deterministic recommendation score.
- `app/reports/markdown_report.py`: Korean markdown report generator.
- `app/api/routes.py`: API endpoints for MVP and G2B dual pipeline.

## Data Flow

```text
/g2b/search
request mode
-> fixture filter or guarded real API client
-> normalize_g2b_notice
-> G2BSearchResponse

/g2b/recommendations
search result
-> score_notice
-> optional generate_markdown_report
-> ranked response
```

## Safety Constraints

- Fixture mode is default.
- Real API calls require enabled settings, a configured service key, endpoint path or known endpoint preset, and explicit request confirmation.
- Real response capture is opt-in and masks secret request fields before writing UTF-8 JSON.
- Captured real responses are written under ignored local paths such as `data/captured/g2b`.
- `scripts/validate_g2b_real_readiness.ps1` checks readiness without calling the real API.
- The service key is never returned in API responses.
- Tests and smoke fixture scripts do not call the real API.
- No database, frontend UI, or LLM is required.
