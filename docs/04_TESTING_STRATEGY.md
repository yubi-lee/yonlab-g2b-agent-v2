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

The script runs `python -m pytest -q`, starts a temporary FastAPI server on `127.0.0.1:8000`, waits for `/health`, runs fixture smoke scripts, verifies the UI and operations fixture flow, verifies the real API guard-blocked smoke path, runs the Korean markdown report smoke check, and stops the server in a `finally` block.

## Real API Readiness Validation

Use one command before the first confirmed real smoke:

```powershell
.\scripts\validate_g2b_real_readiness.ps1
```

The script runs `scripts/check_no_secrets.ps1`, targeted offline tests, and `python -m app.integrations.g2b.readiness`. It does not call the real G2B/Public Data Portal API and does not print service key values.

## Swagger Testing Guide

Swagger examples should use practical fixture-safe request bodies, not generated placeholders.

Recommended `/demo/recommendations` compact fixture body:

```json
{
  "include_reports": false,
  "limit": 5
}
```

Recommended `/g2b/recommendations` fixture body:

```json
{
  "mode": "fixture",
  "keyword": "AI",
  "page_no": 1,
  "num_rows": 5,
  "active_only": false,
  "confirm_real_api_call": false,
  "include_reports": false
}
```

Recommended controlled real template:

```json
{
  "mode": "real",
  "keyword": "AI",
  "start_date": "2026-06-01",
  "end_date": "2026-06-20",
  "page_no": 1,
  "num_rows": 3,
  "active_only": false,
  "confirm_real_api_call": true,
  "include_reports": false
}
```

Placeholder strings such as `"string"` in G2B filter fields are treated as empty filters.
Placeholder notice objects such as `{"additionalProp1": {}}` in `/demo/recommendations`
are ignored; if no valid custom notice remains, fixtures are used. Attachment and PDF
planning endpoints are fixture-safe and do not download files.

Recommended `/g2b/document-risk-analysis` text body:

```json
{
  "source_name": "sample-rfp-text",
  "text": "AI 소프트웨어 개발, 최근 3년 유사 사업 수행실적, 공동수급불허, 기술평가 90점",
  "include_positive_signals": true
}
```

Recommended `/g2b/pdf-analysis-candidates` body:

```json
{
  "mode": "fixture",
  "keyword": "AI",
  "page_no": 1,
  "num_rows": 3,
  "confirm_real_api_call": false
}
```

## Current Test Coverage

- `tests/test_app_health.py`: health endpoint.
- `tests/test_yonlab_profile.py`: fixed YOnLab profile.
- `tests/test_g2b_normalizer.py`: fixture loading and field normalization.
- `tests/test_g2b_client.py`: guarded real client behavior using mocks only.
- `tests/test_g2b_endpoint_presets.py`: endpoint preset resolution and unknown-preset blocking.
- `tests/test_g2b_detail_analysis_queue.py`: real notice detail URL, attachment metadata, and risk metadata queue extraction without downloads.
- `tests/test_document_risk_analysis.py`: document keyword risk analysis, PDF candidates, blocked PDF text analysis, and disabled attachment download planning.
- `tests/test_g2b_pipeline_api.py`: `/g2b/config`, `/g2b/search`, `/g2b/recommendations`.
- `tests/test_g2b_readiness.py`: offline real API readiness summary without secrets.
- `tests/test_korean_utf8_pipeline.py`: Korean fixture/API/report encoding regression coverage.
- `tests/test_yonlab_eligibility.py`: eligibility and first-pass risk signals.
- `tests/test_score_engine.py`: 100-point scoring and risk penalty behavior.
- `tests/test_markdown_report.py`: deterministic Korean report sections.
- `tests/test_recommendation_api.py`: API contract for MVP endpoints.
- `tests/test_demo_recommendations.py`: ranked fixture demo recommendations.
- `tests/test_smoke_scripts.py`: smoke script and line-ending policy presence.
- `tests/test_operations_storage.py`: local SQLite operations storage, fixture run persistence, report artifact writing, and real operations guard behavior.
- `tests/test_operations_ui.py`: `/ui`, static assets, report-content safety, recommendation `run_id` filtering, UI smoke scripts, and duplicated Korean fixture artifact regression.

## Real API Test Rule

Tests must never call the real G2B/Public Data Portal API. Real API behavior is verified through:

- disabled-mode blocking.
- missing-confirmation blocking.
- missing-service-key blocking.
- mocked httpx success response.
- mocked empty response.
- mocked HTTP error, timeout, unsupported XML, and unexpected JSON shape.
- optional capture behavior with sanitized request metadata.
- guard-blocked smoke script execution through `scripts/validate_local.ps1`.
- sanitized real BidPublicInfoService service-search fixture normalization.
- active-only filtering and missing-deadline recommendation risk behavior.
- detail-analysis queue extraction from real list response fields without attachment downloads.
- document risk analysis from local fixture text only.
- PDF candidate planning from attachment metadata without downloads.
- blocked-by-default PDF text extraction and attachment download behavior.

## Rules

- Tests must not require `.env`, secrets, an external database server, frontend build tooling, or an LLM.
- SQLite tests must use isolated temporary storage paths and never call the real API.
- Tests must not download real attachments or require HWP/HWPX parsing.
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
- duplicated fixture fragments such as `서서울울`, `부부산산`, `지지역역`, `시시스스템템`, and `부부합합합니니다다` do not appear in fresh fixture operations output.
