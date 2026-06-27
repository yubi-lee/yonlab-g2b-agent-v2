# 07 Deployment Handoff

This handoff prepares YOnLab G2B Agent v2 MVP release candidate operations on a
local Windows machine. It is written for a deployment operator and intentionally
does not include real service keys, `.env` values, raw API responses, generated
databases, or generated reports.

## Purpose

- Run the local operations package safely.
- Validate the release candidate without calling the real G2B API.
- Prepare one controlled real operations run only when the operator explicitly
  enables the runtime gate and confirms the command.
- Keep local runtime artifacts outside Git.

## Prerequisites

- Windows PowerShell.
- Python 3.11 or compatible project runtime.
- Git.
- Network access only when intentionally pushing to GitHub or performing a
  controlled real G2B validation.
- A private local `.env` file created from `.env.example` when real validation is
  needed.

Use only the v2 project path:

```powershell
Set-Location D:\Views\yonlab-g2b-agent-v2
```

Do not use or modify the previous v1 project during this release handoff.

## Virtual Environment

Create and activate a virtual environment if one does not already exist:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

If the environment already exists:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

## Environment Configuration

Start from `.env.example` and create a private local `.env` only on the target
machine. Do not commit `.env`.

Required real-ops variable names are documented in `.env.example`:

- `G2B_ENABLE_REAL_API`
- `G2B_API_BASE_URL`
- `G2B_API_SERVICE_KEY`
- `G2B_LIST_ENDPOINT_PATH` or `G2B_ENDPOINT_PRESET`
- `G2B_CAPTURE_REAL_RESPONSES`
- `YONLAB_STORAGE_DB_PATH`
- `YONLAB_REPORT_DIR`
- `YONLAB_DEFAULT_RUN_MODE`
- `YONLAB_DEFAULT_KEYWORD`
- `YONLAB_DEFAULT_NUM_ROWS`
- `YONLAB_AUTO_RUN_REAL_API`

For routine local validation, keep:

```powershell
Remove-Item Env:\YONLAB_AUTO_RUN_REAL_API -ErrorAction SilentlyContinue
```

Do not set `YONLAB_AUTO_RUN_REAL_API=true` except inside a deliberate controlled
real operations validation window.

## Local Validation

Run the offline fixture-safe validation first:

```powershell
ruff check app tests
python -m pytest -q
.\scripts\check_real_ops_readiness.ps1
.\scripts\validate_real_ops_controlled.ps1
.\scripts\check_deploy_readiness.ps1
.\scripts\validate_local.ps1
```

`validate_real_ops_controlled.ps1` without `-ConfirmRealApiCall` is safe by
default and does not run a confirmed real API operation.

Do not run this command during offline release validation:

```powershell
.\scripts\validate_real_ops_controlled.ps1 -ConfirmRealApiCall
```

For one-command release closeout, run this from the development repo:

```powershell
.\scripts\run_release_closeout_harness.ps1 -ReleaseTag v0.1.0-rc5
```

The harness defaults to no real API call. It should end as `ready_after_env_fix` when the
fresh deployment has no `.env`, or `ready` when a prepared `.env` exists and an explicitly
confirmed controlled real run succeeds. The real run path requires both
`-RunControlledRealCall` and `-ConfirmRealApiCall`. Do not persist
`YONLAB_AUTO_RUN_REAL_API=true` in `.env`: the harness opens that runtime gate in process
scope only after base real configuration readiness is true, then closes it after the
controlled validation command.

Before a final confirmed real run, run the synthetic persistence check. It detects stale
absolute storage/report paths copied from an older deployment and verifies that
`/ops/quality-summary`, `/ops/report-index`, and `/ui` read the same deployment-local store
without making a real G2B API call.

## Run the UI

Start the packaged local operations app:

```powershell
.\scripts\start_local_ops.ps1
```

Open:

```text
http://127.0.0.1:8000/ui
http://127.0.0.1:8000/docs
```

The dashboard defaults to fixture operations. Keep real mode disabled unless the
operator is intentionally performing a controlled real validation.

## Safe Daily Scheduled Operations

The production-ready local deployment is `D:\Deploy\yonlab-g2b-agent-v2-rc7`, based on
`v0.1.0-rc7`. Task 36H completed the previous controlled real run
`run_20260627_175740_008807`; Task 40G keeps real API execution manual-only and leaves the
safe daily deployment status as `ready`.

Routine scheduled operations must use the safe daily script only. In a deployment checkout,
the operational scripts resolve an omitted `-DeployPath` to the script's repo root; scheduler
registration should still pass the active deployment path explicitly:

```powershell
.\scripts\run_ops_safe_daily.ps1 -DeployPath D:\Deploy\yonlab-g2b-agent-v2-rc7
```

Preview Windows Task Scheduler registration:

```powershell
.\scripts\register_ops_safe_daily_task.ps1 `
  -DeployPath D:\Deploy\yonlab-g2b-agent-v2-rc7 `
  -WhatIf
```

The safe daily task does not call the real G2B API. It writes logs under
`logs/ops/YYYYMMDD/`. The controlled real wrapper is for manual operator use only and must
not be registered as an automatic daily task.

## Controlled Real Run Procedure

Use this only after offline validation passes and the operator has approved one
small real run.

1. Configure private `.env` values locally.
2. Run readiness checks:

   ```powershell
   .\scripts\check_real_ops_readiness.ps1
   .\scripts\validate_real_ops_controlled.ps1
   ```

3. Enable the runtime gate only for the validation window:

   ```powershell
   $env:YONLAB_AUTO_RUN_REAL_API = "true"
   ```

4. Run exactly one confirmed validation:

   ```powershell
   .\scripts\validate_real_ops_controlled.ps1 -ConfirmRealApiCall
   ```

5. Remove the runtime gate:

   ```powershell
   Remove-Item Env:\YONLAB_AUTO_RUN_REAL_API -ErrorAction SilentlyContinue
   ```

6. Check saved metadata through:

   ```text
   GET /ops/quality-summary
   GET /ops/report-index
   ```

The successful MVP release candidate real run from Task 28B was:

- `run_id`: `run_20260621_133936_840140`
- `status`: `success`
- `real_call_executed`: `true`
- real report metadata count: `3`
- quality summary status: `success_with_warnings`

Do not repeat real calls for routine smoke testing.

## Deployment Smoke Test

After starting the app locally:

```powershell
.\scripts\smoke_ops_quality_summary.ps1
.\scripts\smoke_ops_report_index.ps1
.\scripts\validate_ops_package.ps1
```

Expected safe endpoints:

- `GET /health`
- `GET /ops/package-info`
- `GET /ops/real-readiness`
- `GET /ops/quality-summary`
- `GET /ops/report-index`

These checks must not expose service keys.

## Rollback Criteria

Stop deployment and roll back to the last known good commit or tag if any of the
following occurs:

- `python -m pytest -q` fails.
- `scripts\validate_local.ps1` fails.
- `scripts\check_deploy_readiness.ps1` reports `deploy_ready=false`.
- A secret, `.env` value, raw response, database, or generated report would be
  committed.
- The app requires a real API call for routine local validation.
- `/ui`, `/health`, or operations metadata endpoints fail after startup.

## Troubleshooting

- If a port is already in use, start with another port:

  ```powershell
  .\scripts\start_local_ops.ps1 -Port 8010
  ```

- If generated local data should be cleared:

  ```powershell
  .\scripts\reset_local_ops_data.ps1
  ```

- If real operations are blocked, check:

  ```powershell
  .\scripts\check_real_ops_readiness.ps1
  ```

- If the runtime gate was accidentally left in the process:

  ```powershell
  Remove-Item Env:\YONLAB_AUTO_RUN_REAL_API -ErrorAction SilentlyContinue
  ```

## Known Limitations

- The release candidate is a local operations package, not a hosted production
  deployment.
- Real G2B calls are guarded and manual; they are not scheduled background jobs.
- Attachment download and heavy document processing remain controlled local
  flows.
- Generated SQLite data and markdown reports are local runtime artifacts and are
  intentionally ignored by Git.
