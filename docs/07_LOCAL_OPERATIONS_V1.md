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
```

This delegates to `scripts/validate_local.ps1`, which runs pytest, starts a temporary
local FastAPI server, executes fixture-safe API/UI/ops smoke checks, and stops the server.
It does not call the real G2B/Public Data Portal API.

## Inspect Package Metadata

```text
GET /ops/package-info
```

The response includes package version, safe route/script lists, enabled capabilities,
storage configuration status, and safety flags. It reports whether a service key is
configured but never returns the service key value.

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

## Real API Safety

Real API mode is not used by default. Use it only for controlled manual smoke checks with:

- local `.env` only
- `G2B_ENABLE_REAL_API=true`
- private `G2B_API_SERVICE_KEY`
- operation endpoint path configured
- small `num_rows`
- `confirm_real_api_call=true`

Do not run real mode repeatedly from the dashboard.
