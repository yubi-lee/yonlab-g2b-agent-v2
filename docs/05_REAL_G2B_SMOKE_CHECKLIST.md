# 05 Real G2B Smoke Checklist

Use this checklist before the first controlled Public Data Portal/G2B smoke test.

Do not paste, commit, print, or ask for the service key.

## Safe Defaults

- Fixture mode is default.
- Real API calls are disabled by default.
- `.env` is local only and ignored by Git.
- `.env.example` keeps `G2B_API_SERVICE_KEY=` empty.
- Captured real responses must not contain the service key and stay under `data/captured/`.
- Attachment download is disabled by default with `G2B_ENABLE_ATTACHMENT_DOWNLOAD=false`.
- PDF text extraction is disabled by default with `G2B_ENABLE_PDF_TEXT_EXTRACTION=false`.
- The operations dashboard at `/ui` defaults to fixture mode and never displays service key values.
- Local validation does not download real attachments or parse HWP/HWPX contents.

## Approved Endpoint

The approved endpoint base is:

```text
https://apis.data.go.kr/1230000/ad/BidPublicInfoService
```

Use:

```env
G2B_API_BASE_URL=https://apis.data.go.kr
G2B_LIST_ENDPOINT_PATH=/1230000/ad/BidPublicInfoService/getBidPblancListInfoServcPPSSrch
```

The approved service endpoint is the base path above. For real list/search calls, use a business-operation path such as `/1230000/ad/BidPublicInfoService/getBidPblancListInfoServcPPSSrch`.

## Presets

Available local presets:

- `custom`: use `G2B_LIST_ENDPOINT_PATH` from `.env`.
- `approved_bid_public_info_service`: approved G2B BidPublicInfoService endpoint base path.
- `approved_bid_public_info_service_base`: approved base path; not usually sufficient for search calls.
- `servc_pps_search`: recommended first operation for YOnLab AI/SW service search.

Inspect locally:

```powershell
.\scripts\smoke_g2b_endpoint_presets.ps1
```

## Readiness

Inspect safe readiness locally:

```powershell
.\scripts\smoke_g2b_real_readiness.ps1
```

Inspect local `.env` status without printing the service key:

```powershell
.\scripts\show_g2b_real_env_status.ps1
```

Run the offline validation bundle:

```powershell
.\scripts\validate_g2b_real_readiness.ps1
.\scripts\validate_g2b_real_ops_readiness.ps1
```

This validates no-secret rules and targeted offline tests. It does not call the real API.

## First Real Smoke

Before running a confirmed real smoke:

1. Create `.env` locally from `.env.example`.
2. Set `G2B_ENABLE_REAL_API=true`.
3. Set `G2B_API_SERVICE_KEY` manually in `.env` only.
4. Keep `G2B_LIST_ENDPOINT_PATH=/1230000/ad/BidPublicInfoService/getBidPblancListInfoServcPPSSrch`.
5. Keep `G2B_CAPTURE_REAL_RESPONSES=false` unless intentionally capturing sanitized response samples.
6. Run `.\scripts\check_no_secrets.ps1`.
7. Run `.\scripts\smoke_g2b_real_guard_blocked.ps1`.
8. Restart the FastAPI server after changing `.env`.
9. Start with `num_rows=3`.
10. Include `confirm_real_api_call=true`.

First request shape:

```json
{
  "mode": "real",
  "keyword": "AI",
  "start_date": "2026-06-01",
  "end_date": "2026-06-20",
  "page_no": 1,
  "num_rows": 3,
  "confirm_real_api_call": true
}
```

Then run the confirmed template only after the checklist passes:

```powershell
.\scripts\smoke_g2b_real_confirmed_template.ps1
```

The first controlled real smoke has succeeded. For recommendation calibration, use:

```powershell
.\scripts\smoke_g2b_real_recommend_template.ps1
```

Real responses now include safe endpoint metadata and can use `active_only=true` to exclude already-closed notices. Service keys remain local-only and are not printed.

Do not use the `/ui` real mode for repeated testing. If you use it for a controlled smoke,
confirm that `.env` is configured locally, keep `num_rows` small, and check
`confirm_real_api_call=true` only for the intentional run.

Before a controlled real operations run through `/ui` or `/ops/run-recommendations`, inspect:

```text
GET /ops/real-readiness
```

The endpoint is read-only and does not call the real API, connect to SQLite, write files, or
return the service key value.

## Attachment and PDF Follow-up

After a successful real list smoke, use fixture-safe planning endpoints first:

```powershell
.\scripts\smoke_g2b_document_risk_analysis.ps1
.\scripts\smoke_g2b_pdf_analysis_candidates_fixture.ps1
.\scripts\smoke_g2b_pdf_text_analysis_fixture.ps1
```

These scripts do not call the real API and do not download attachments. HWP/HWPX files
remain manual review until a controlled parser is implemented. The next integration step is
controlled PDF download into ignored local storage, followed by extracted-text integration
into recommendation reports.
