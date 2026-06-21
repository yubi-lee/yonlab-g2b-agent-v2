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
```

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

## Validation

```powershell
python -m pytest -q
.\scripts\validate_local.ps1
.\scripts\validate_ops_package.ps1
```

`validate_local.ps1` runs fixture-safe UI and operations smoke checks. It does not call the
real G2B/Public Data Portal API.
