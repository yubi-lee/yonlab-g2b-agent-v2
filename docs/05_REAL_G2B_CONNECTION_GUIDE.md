# 05 Real G2B Connection Guide

This guide prepares the first controlled Public Data Portal/G2B smoke test for YOnLab G2B Agent v2.

Do not run a confirmed real smoke until the offline readiness command passes.

## Default Safety

- Fixture mode is the default.
- Real API calls are disabled by default.
- `.env.example` contains placeholders only.
- `.env` must stay local and ignored by Git.
- Service keys must not be pasted into scripts, docs, tests, issue comments, or reports.
- Captured real responses are optional, sanitized, and ignored under `data/captured/`.

## Endpoint Presets

The app supports endpoint path presets to reduce copy/paste errors while preparing the first smoke.

```env
G2B_ENDPOINT_PRESET=approved_bid_public_info_service
```

Known presets:

| Preset | Operation Guidance | YOnLab Use |
| --- | --- | --- |
| `custom` | Use `G2B_LIST_ENDPOINT_PATH` from `.env` | Manual endpoint path |
| `approved_bid_public_info_service` | `/1230000/ad/BidPublicInfoService` | Approved service base path |
| `approved_bid_public_info_service_base` | `/1230000/ad/BidPublicInfoService` | Diagnostic base path preset |
| `servc_pps_search` | `/1230000/ad/BidPublicInfoService/getBidPblancListInfoServcPPSSrch` | Recommended first YOnLab AI/SW service search |

`G2B_LIST_ENDPOINT_PATH` overrides `G2B_ENDPOINT_PRESET` when both are set.

Before a confirmed real call, verify the selected operation and endpoint path in the Public Data Portal service page. Treat presets as safe local configuration helpers, not as proof that the external operation is currently active.

## Operation Selection

Start with `/1230000/ad/BidPublicInfoService/getBidPblancListInfoServcPPSSrch` because real list/search calls need a business-operation path under the approved G2B BidPublicInfoService base endpoint.

If a confirmed real smoke returns HTTP/path errors, confirm the exact operation path in the Public Data Portal Swagger before changing the endpoint.

## First-Real-Smoke Checklist

1. Confirm the Public Data Portal API service is approved for the local key.
2. Keep `.env` local and untracked.
3. Set `G2B_ENABLE_REAL_API=true`.
4. Set `G2B_API_SERVICE_KEY` in `.env` only.
5. Set `G2B_LIST_ENDPOINT_PATH=/1230000/ad/BidPublicInfoService/getBidPblancListInfoServcPPSSrch`.
6. Keep `G2B_CAPTURE_REAL_RESPONSES=false` for the first connection attempt unless capture is intentionally needed.
7. Run `.\scripts\validate_g2b_real_readiness.ps1`.
8. Restart the local FastAPI server after changing `.env`.
9. Run `.\scripts\smoke_g2b_real_confirmed_template.ps1`.
10. If search succeeds, optionally run `.\scripts\smoke_g2b_real_recommend_template.ps1`.

The first real smoke should use:

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

## Offline Readiness

Run:

```powershell
.\scripts\validate_g2b_real_readiness.ps1
```

The command:

- validates `.env.example` and template scripts contain placeholders only.
- confirms `.env` and `data/captured/` remain ignored by Git.
- runs relevant offline tests.
- prints a sanitized readiness summary.
- does not call the real G2B/Public Data Portal API.

## No-Secret Validation

Run only the no-secret check:

```powershell
.\scripts\check_no_secrets.ps1
```

Expected result:

```text
No-secret check completed successfully.
```

If it fails, fix the reported placeholder or ignore-rule problem before running any real smoke.
