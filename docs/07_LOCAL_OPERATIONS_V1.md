# 07 Local Operations v1.0

YOnLab G2B Agent v2 local operations v1.0 packages the FastAPI server, Swagger API,
browser dashboard, fixture recommendations, guarded real API path, local SQLite storage,
and saved markdown report viewer into a practical local application.

## Start

```powershell
Set-Location D:\Views\yonlab-g2b-agent-v2
.\.venv\Scripts\Activate.ps1
.\scripts\start_local_ops.ps1
```

Open:

```text
http://127.0.0.1:8000/ui
```

Use another port when needed:

```powershell
.\scripts\start_local_ops.ps1 -Port 8010
```

## Validate

```powershell
.\scripts\validate_ops_package.ps1
.\scripts\validate_g2b_real_ops_readiness.ps1
.\scripts\validate_real_ops_controlled.ps1
```

This delegates to `scripts/validate_local.ps1`, which runs pytest, starts a temporary
local FastAPI server, executes fixture-safe API/UI/ops smoke checks, and stops the server.
It does not call the real G2B/Public Data Portal API.

## Inspect Package Metadata

```text
GET /ops/package-info
GET /ops/real-readiness
GET /ops/quality-summary
GET /ops/safe-daily-status
GET /ops/report-index
```

The response includes package version, safe route/script lists, enabled capabilities,
storage configuration status, and safety flags. It reports whether a service key is
configured but never returns the service key value.

`/ops/real-readiness` summarizes whether controlled real operations are configured. The
endpoint is read-only: it does not call the real API, connect to SQLite, write files, or
return service key values.

`/ops/quality-summary` summarizes saved local recommendation runs and label counts.
`/ops/report-index` lists recent saved report metadata constrained to the configured report
directory. Neither endpoint returns service key values.
`/ops/safe-daily-status` powers the dashboard safe daily card from latest local log metadata
only. It avoids full path exposure and does not call the real API or query the Windows
Scheduler from the server.

## Operator Clarity Dashboard

The `/ui` dashboard includes a source-mode banner, P1/P2/P3/Hold priority legend, safe daily
status card, Korean Daily Review Pack labels, executive summary, and grouped document
checklist. Demo and fixture data are labeled as non-real; controlled real runs remain
script-only and require explicit operator confirmation.

## Fixture Operations Flow

1. Open `/ui`.
2. Keep mode as `fixture`.
3. Keep `confirm_real_api_call` unchecked.
4. Run a recommendation job.
5. Open saved runs, recommendations, and report markdown from the dashboard.

Generated local data is ignored by Git:

```text
data/ops/
data/reports/
```

Reset generated local ops data:

```powershell
.\scripts\reset_local_ops_data.ps1
```

This removes generated data under `data/ops`, `data/reports`, `data/downloaded`, and
`data/extracted`. It does not touch `.env` or source fixtures.

## Real API Safety

Real API mode is not used by default. Use it only for controlled manual smoke checks with:

- local `.env` only
- `G2B_ENABLE_REAL_API=true`
- private `G2B_API_SERVICE_KEY`
- operation endpoint path configured
- small `num_rows`
- `confirm_real_api_call=true`

Do not run real mode repeatedly from the dashboard.

Before a controlled real operations validation, run:

```powershell
.\scripts\validate_g2b_real_ops_readiness.ps1
.\scripts\validate_real_ops_controlled.ps1
.\scripts\run_ops_real_controlled.ps1 -ConfirmRealApiCall
```

Run `run_ops_real_controlled.ps1` only for one intentional real operations validation.
Without `-ConfirmRealApiCall`, it exits without calling `/ops/run-recommendations`.
