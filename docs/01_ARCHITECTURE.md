# 01 Architecture

## Layers

```text
FastAPI routes
  -> G2B search mode router
  -> fixture loader or guarded real API client
  -> normalizer
  -> domain models
  -> eligibility and risk analysis
  -> optional document/PDF text risk analysis
  -> 100-point score engine
  -> deterministic markdown report
```

## Modules

- `app/domain/yonlab_profile.py`: fixed YOnLab profile.
- `app/domain/bid_notice.py`: normalized procurement notice model.
- `app/domain/recommendation.py`: eligibility, risk, score, report, and demo response models.
- `app/domain/search.py`: G2B search and recommendation request/response models.
- `app/domain/document_analysis.py`: document risk, PDF extraction, and attachment planning models.
- `app/integrations/g2b/fixtures.py`: local fixture loader and deterministic filter.
- `app/integrations/g2b/normalizer.py`: Korean and G2B-like field mapping.
- `app/integrations/g2b/client.py`: guarded httpx client for real API calls.
- `app/integrations/g2b/capture.py`: optional sanitized real response capture.
- `app/integrations/g2b/detail_queue.py`: deterministic real-notice detail and attachment metadata queue builder; no downloads.
- `app/integrations/g2b/errors.py`: sanitized client errors.
- `app/integrations/g2b/presets.py`: endpoint path preset definitions and resolver.
- `app/integrations/g2b/readiness.py`: offline real API readiness summary.
- `app/scoring/eligibility.py`: first-pass YOnLab eligibility signals.
- `app/scoring/risk_analyzer.py`: deterministic risk detection.
- `app/scoring/score_engine.py`: 100-point deterministic recommendation score.
- `app/services/document_risk_analyzer.py`: deterministic procurement/RFP keyword analysis.
- `app/services/pdf_text_extractor.py`: controlled local PDF text extraction with dependency fallback.
- `app/services/attachment_downloader.py`: blocked-by-default attachment download planning.
- `app/services/attachment_analysis_planner.py`: PDF/HWP/HWPX analysis planning from attachment metadata.
- `app/reports/markdown_report.py`: Korean markdown report generator.
- `app/api/routes.py`: API endpoints for MVP and G2B dual pipeline.
- `data/fixtures/g2b/real_servc_search_sample.json`: sanitized observed real service-search response sample for offline tests.

## Data Flow

```text
/g2b/search
request mode
-> fixture filter or guarded real API client
-> normalize_g2b_notice
-> optional active_only deadline filter
-> real-mode detail_analysis_queue metadata extraction
-> G2BSearchResponse

/g2b/recommendations
search result
-> score_notice
-> optional generate_markdown_report
-> carry detail_analysis_queue forward
-> ranked response

/g2b/document-risk-analysis
provided text
-> deterministic keyword rules
-> risk and positive signal summary

/g2b/pdf-analysis-candidates
fixture or guarded real search
-> detail_analysis_queue attachment metadata
-> PDF-only candidate list
```

## Safety Constraints

- Fixture mode is default.
- Real API calls require enabled settings, a configured service key, endpoint path or known endpoint preset, and explicit request confirmation.
- Real response capture is opt-in and masks secret request fields before writing UTF-8 JSON.
- Captured real responses are written under ignored local paths such as `data/captured/g2b`.
- Detail-analysis queue extraction records public detail and attachment metadata only; it does not download attachment files.
- Attachment download planning is disabled by default and does not create files.
- PDF text extraction is disabled by default, local-file only, size-limited, and controlled by explicit confirmation.
- HWP/HWPX content extraction is not implemented; those files remain manual review.
- `scripts/validate_g2b_real_readiness.ps1` checks readiness without calling the real API.
- The service key is never returned in API responses.
- Tests and smoke fixture scripts do not call the real API.
- No database, frontend UI, or LLM is required.
