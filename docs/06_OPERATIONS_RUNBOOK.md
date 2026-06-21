# 06 Operations Runbook

## Start the App

```powershell
Set-Location D:\Views\yonlab-g2b-agent-v2
.\.venv\Scripts\Activate.ps1
.\scripts\dev_start.ps1
```

Open:

```text
http://127.0.0.1:8000/ui
```

`GET /` redirects to `/ui`.

For the packaged v1.0 local operations launcher:

```powershell
.\scripts\start_local_ops.ps1
```

Inspect safe package metadata:

```text
GET /ops/package-info
GET /ops/real-readiness
GET /ops/quality-summary
GET /ops/report-index
```

`/ops/quality-summary` and `/ops/report-index` include operator-friendly run metadata:
latest run time, run mode, recommendation counts, quality labels, warning/error counts, and
safe report references. They do not expose service keys.

## Run a Fixture Recommendation Job

The dashboard defaults to fixture mode with keyword `AI`, page `1`, and `num_rows=5`.
Keep `confirm_real_api_call` unchecked for routine local testing.

Click `Run fixture-safe job`. The dashboard shows:

- `run_id`
- status
- source count
- recommendation count
- report count
- message

Generated operations data is stored locally under ignored paths:

```text
data/ops/
data/reports/
```

## View Saved Runs and Recommendations

Use the dashboard sections:

- `Saved Runs`: recent `/ops/runs` entries with a view action.
- `Saved Recommendations`: recent `/ops/recommendations` entries with optional `min_score` and label filters.
- `Run Details and Report Viewer`: recommendations and markdown reports for the selected run.

The report viewer reads markdown through:

```text
GET /ops/report-content/{run_id}/{notice_id}
```

The endpoint only uses stored report metadata and rejects report paths outside the configured
`YONLAB_REPORT_DIR`.

## Reset Generated Local Ops Data

```powershell
.\scripts\reset_local_ops_data.ps1
```

This deletes `data/ops` and `data/reports`. It does not touch `.env` or source fixtures.

## Real API Safety

Default operations mode is fixture. Do not use real mode for repeated testing.

Real API operations require local `.env` configuration, existing G2B safety gates, and
`confirm_real_api_call=true`. Service key values are never displayed by `/ui`, `/g2b/config`,
or operations endpoints.

Before a controlled real operations validation, run:

```powershell
.\scripts\validate_g2b_real_ops_readiness.ps1
.\scripts\check_real_ops_readiness.ps1
.\scripts\validate_real_ops_controlled.ps1
```

The readiness endpoint and default controlled validation are read-only and do not call the
real API.

`real_ops_disabled` means the request reached the operations runner but
`YONLAB_AUTO_RUN_REAL_API` was not enabled. This is separate from the G2B master flag and
separate from `confirm_real_api_call=true`.

Controlled real operations checklist:

- `G2B_ENABLE_REAL_API=true`
- `G2B_API_SERVICE_KEY` is present in local `.env`
- `G2B_API_BASE_URL` is configured
- `G2B_LIST_ENDPOINT_PATH` or `G2B_ENDPOINT_PRESET` is configured
- `YONLAB_AUTO_RUN_REAL_API=true` only for the controlled validation window
- the operator explicitly confirms the controlled real command

MVP release candidate controlled real result:

- run_id: `run_20260621_133936_840140`
- status: `success`
- real report metadata count: 3
- `/ops/report-index`: reflected
- `/ops/quality-summary`: reflected
- summary status: `success_with_warnings`

After any controlled real validation, remove the session runtime gate:

```powershell
Remove-Item Env:\YONLAB_AUTO_RUN_REAL_API -ErrorAction SilentlyContinue
```

Keep these modes distinct:

- `validate_local.ps1`: fixture-safe local validation; no confirmed real call.
- `validate_real_ops_controlled.ps1`: safe by default; no confirmed real call without the flag.
- `YONLAB_AUTO_RUN_REAL_API`: runtime gate that allows operations runner real mode.
- confirmed real network call: only after the runtime gate and explicit confirmation are both present.

For one intentional controlled real operations run:

```powershell
.\scripts\validate_real_ops_controlled.ps1 -ConfirmRealApiCall
```

Without `-ConfirmRealApiCall`, the controlled validation exits before the real operation step.
With the flag, it performs one small real operations run through the guarded runner, then
checks `/ops/quality-summary` and `/ops/report-index` for persisted report metadata. Service
key values are never printed by the controlled scripts.

## Validation

```powershell
python -m pytest -q
.\scripts\check_deploy_readiness.ps1
.\scripts\validate_local.ps1
.\scripts\validate_ops_package.ps1
.\scripts\validate_g2b_real_ops_readiness.ps1
.\scripts\validate_real_ops_controlled.ps1
```

`validate_local.ps1` runs fixture-safe UI and operations smoke checks. It does not call the
real G2B/Public Data Portal API.
