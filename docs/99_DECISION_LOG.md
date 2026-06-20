# 99 Decision Log

## 2026-06-20

Decision: Keep v2 independent from `D:\Views\yonlab-bid-agent`.

Reason:

- Prevent v1/v2 code contamination.
- Keep Agent-first development testable from a clean baseline.
- Preserve fixture-first iteration before any real API smoke test.

## 2026-06-20 MVP Vertical Slice

Decision: Implement a complete deterministic MVP before real G2B API integration.

Included:

- Pydantic domain models.
- Local G2B-style fixtures.
- Korean/G2B-like normalizer.
- First-pass eligibility logic.
- Risk analyzer.
- 100-point scoring model.
- Korean markdown report generator.
- FastAPI endpoints for profile, fixtures, normalization, scoring, reports, and demo ranking.

## 2026-06-20 Guarded Dual Pipeline

Decision: Add real G2B client capability behind explicit safety gates while preserving fixture default.

Safety gates:

- `G2B_ENABLE_REAL_API=true`
- service key configured
- endpoint path configured
- request has `confirm_real_api_call=true`

Reason:

- The app can be exercised safely in fixture mode.
- Real API code can be tested with mocked responses.
- Service keys stay out of responses, logs, tests, and docs.
