# rc17 Validation Environment Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reproducible Windows release validation entrypoint that uses repo-local Python and preserves the existing validation scripts.

**Architecture:** Add a narrow PowerShell wrapper at `scripts/validate_release.ps1` that resolves the repo root, validates `.venv\Scripts\python.exe`, runs pytest and ruff through that interpreter, then delegates to the existing validation scripts. Keep product behavior unchanged and update release documentation only after validation passes.

**Tech Stack:** PowerShell, repo-local Python virtual environment, pytest, ruff, existing validation scripts, existing docs/decision-log process.

---

## 1. Scope

This rc17 work is a validation-process hardening release, not a product feature release.

In scope:

- create `scripts/validate_release.ps1` as the canonical Windows release validation entrypoint
- make the wrapper resolve the repository root from the script location
- make the wrapper require and use `.\.venv\Scripts\python.exe`
- run `pytest` and `ruff` through repo-local Python instead of relying on global `python`
- invoke:
  - `scripts/check_deploy_readiness.ps1`
  - `scripts/validate_local.ps1`
  - `scripts/validate_ops_package.ps1`
- stop on the first failed step and return a non-zero exit code
- print concise `==> step` plus `PASS`/failure output without exposing `.env` contents or secrets
- keep the existing validation scripts directly runnable on their own
- update the operator/developer documentation that currently advertises validation commands
- add or extend narrow script/documentation tests where the existing repository patterns support them
- validate the wrapper both in the development checkout and in a fresh deploy checkout

Implementation assumption to keep explicit:

- The wrapper will intentionally call both `scripts/validate_local.ps1` and `scripts/validate_ops_package.ps1` even though `validate_ops_package.ps1` already delegates to `validate_local.ps1`. This duplicates one validation run, but it preserves the agreed rc17 requirement that the wrapper composes the existing scripts instead of changing their semantics.

## 2. Non-goals

Out of scope for rc17:

- no product/API/UI behavior changes under `app/`
- no model, service, or route changes for recommendation, review board, decision memo, or manual decision persistence behavior
- no new real G2B/Public Data Portal call path
- no new network behavior from the application
- no `.env` schema expansion
- no CI/CD redesign
- no replacement of `scripts/validate_local.ps1`, `scripts/validate_ops_package.ps1`, or `scripts/check_deploy_readiness.ps1`
- no update to `docs/99_DECISION_LOG.md` during the implementation tasks before validation is complete
- no secrets, tokens, service keys, `.env` values, or credentials exposed in scripts, docs, tests, or command output

## 3. Existing code map

### Current repo observations

- Repo path: `D:\Views\yonlab-g2b-agent-v2`
- Planning baseline branch: `main`
- Planning-time status: `## main...origin/main [ahead 1]`
- Planning-time HEAD: `602f994 docs: add rc17 validation environment hardening design`
- rc16 release baseline tag: `v0.1.0-rc16 -> 02482d3322bd94abb6ebacf069e827eb439e9ccb`

### Validation scripts already present

- `scripts/check_deploy_readiness.ps1`
  - resolves repo root via `Split-Path -Parent $PSScriptRoot`
  - switches to repo root with `Set-Location`
  - reads `.env` only as boolean presence/true checks
  - does not call `Invoke-WebRequest`
  - returns JSON with `deploy_ready`, `real_network_call_attempted = false`, and `service_key_exposed = false`
- `scripts/validate_local.ps1`
  - resolves repo root via `Split-Path -Parent $PSScriptRoot`
  - dot-sources `.venv\Scripts\Activate.ps1` if present
  - prefers `.venv\Scripts\python.exe`, falls back to `python` if missing
  - runs `check_no_secrets.ps1`
  - runs `python -m pytest -q`
  - starts local `uvicorn` with `Start-Job`
  - runs fixture-safe smoke scripts and stops the server in `finally`
- `scripts/validate_ops_package.ps1`
  - prints a package validation banner
  - delegates directly to `scripts/validate_local.ps1`
- `scripts/check_no_secrets.ps1`
  - already enforces no-secret validation and should stay part of the `validate_local.ps1` path
- `scripts/run_release_closeout_harness.ps1`
  - already orchestrates a broader release flow and should remain separate from the new narrow wrapper

### Existing docs that mention validation entrypoints

- `README.md`
  - documents `python -m pytest -q`
  - documents `.\scripts\validate_local.ps1`
  - documents `ruff check app tests` in the MVP release checklist
- `docs/04_TESTING_STRATEGY.md`
  - calls `.\scripts\validate_local.ps1` the preferred local end-to-end validation command
  - says `python -m pytest -q` remains the standard validation command
- `docs/06_OPERATIONS_RUNBOOK.md`
  - contains a `Validation` section listing pytest and the PowerShell validation scripts
- `docs/07_DEPLOYMENT_HANDOFF.md`
  - contains the operator-facing local validation sequence
- `docs/99_DECISION_LOG.md`
  - records rc15 and rc16 validation acceptance and should be updated only after rc17 implementation validation passes

### Existing app and test files that will likely be touched

- `app/services/local_ops_package.py`
  - publishes package metadata and script lists through `/ops/package-info`
  - currently lists:
    - `scripts/validate_local.ps1`
    - `scripts/validate_ops_package.ps1`
    - `scripts/check_deploy_readiness.ps1`
  - currently reports `validation["pytest"] = "python -m pytest -q"`
- `tests/test_local_ops_package.py`
  - checks package script presence, safe documentation references, and package metadata
- `tests/test_smoke_scripts.py`
  - checks script existence and exact string-level validation/safety characteristics

### Existing file paths confirmed present

- `README.md`
- `pyproject.toml`
- `scripts/check_deploy_readiness.ps1`
- `scripts/validate_local.ps1`
- `scripts/validate_ops_package.ps1`
- `scripts/check_no_secrets.ps1`
- `docs/04_TESTING_STRATEGY.md`
- `docs/06_OPERATIONS_RUNBOOK.md`
- `docs/07_DEPLOYMENT_HANDOFF.md`
- `docs/99_DECISION_LOG.md`
- `app/services/local_ops_package.py`
- `tests/test_local_ops_package.py`
- `tests/test_smoke_scripts.py`

### Files not found

- no additional top-level developer runbook outside `README.md` and `docs/04_TESTING_STRATEGY.md`, `docs/06_OPERATIONS_RUNBOOK.md`, `docs/07_DEPLOYMENT_HANDOFF.md`
- no `tools/` directory is required for the rc17 validation command set

## 4. Target wrapper behavior

Create `scripts/validate_release.ps1` with the following behavior:

1. Resolve the repository root from the script file location:
   - `$ProjectRoot = Split-Path -Parent $PSScriptRoot`
   - `Set-Location $ProjectRoot`
2. Set UTF-8 console output the same way the existing scripts do:
   - `System.Text.UTF8Encoding($false)`
   - `[Console]::OutputEncoding = $Utf8`
   - `$OutputEncoding = $Utf8`
   - `chcp.com 65001 | Out-Null` in a guarded `try`
3. Resolve the repo-local interpreter only:
   - `Join-Path $ProjectRoot ".venv\Scripts\python.exe"`
   - if missing, print a short error such as `FAIL repo-local python missing: .venv\Scripts\python.exe`
   - exit non-zero immediately
4. Use one internal helper such as `Invoke-ReleaseStep` to standardize step banners:
   - print `==> pytest`
   - print `PASS pytest`
   - on failure print `FAIL pytest`
5. Run validation commands in this order:
   - `.\.venv\Scripts\python.exe -m pytest -q`
   - `.\.venv\Scripts\python.exe -m ruff check app tests`
   - `powershell -ExecutionPolicy Bypass -File scripts/check_deploy_readiness.ps1`
   - `powershell -ExecutionPolicy Bypass -File scripts/validate_local.ps1`
   - `powershell -ExecutionPolicy Bypass -File scripts/validate_ops_package.ps1`
6. Stop immediately on the first non-zero exit code
7. Return `0` only after all steps pass
8. Never print:
   - `.env` contents
   - service key values
   - token-like values
9. Preserve direct invocation of the existing scripts without changing their internal semantics

Expected wrapper output shape:

```text
==> pytest
PASS pytest
==> ruff
PASS ruff
==> check_deploy_readiness
PASS check_deploy_readiness
==> validate_local
PASS validate_local
==> validate_ops_package
PASS validate_ops_package
Validation release gate passed.
```

Expected underlying output patterns that the wrapper should allow to surface safely:

- `No issues found!`
- `All tests passed!`
- `"deploy_ready":  true` or `"deploy_ready": true`
- `Local validation completed successfully.`
- `Local operations v1.0 package validation completed.`

## 5. Failure behavior

The wrapper should fail fast and classify errors by step name, not by stack trace volume.

Required failure cases:

- missing `.\.venv\Scripts\python.exe`
  - message pattern: `FAIL repo-local python missing`
  - exit code: non-zero
- pytest failure
  - message pattern: `FAIL pytest`
  - exit code: non-zero
- ruff failure
  - message pattern: `FAIL ruff`
  - exit code: non-zero
- `check_deploy_readiness.ps1` failure or malformed output
  - message pattern: `FAIL check_deploy_readiness`
  - exit code: non-zero
- `validate_local.ps1` failure
  - message pattern: `FAIL validate_local`
  - exit code: non-zero
- `validate_ops_package.ps1` failure
  - message pattern: `FAIL validate_ops_package`
  - exit code: non-zero

Implementation assumptions:

- The wrapper should not swallow the underlying script output. It should add concise step framing, then propagate the existing step output so operators can still diagnose the failure source.
- The wrapper should not parse `.env` itself. That avoids accidental value echo and keeps secret-sensitive logic in already-reviewed scripts.
- The wrapper should use `-ExecutionPolicy Bypass` per process when invoking PowerShell child scripts so the operator does not need a machine-level policy change.

## 6. Security / no-real constraints

Required rc17 safety invariants:

- `real_api_call_attempted=false`
- `real_network_call_attempted=false`
- `service_key_exposed=false`

Specific constraints for implementation:

- do not add any call to `Invoke-WebRequest`, `Invoke-RestMethod`, `httpx`, or remote endpoints inside `scripts/validate_release.ps1`
- do not read `.env` contents for printing or diagnostics
- do not echo environment variables containing:
  - `SERVICE_KEY`
  - `TOKEN`
  - `SECRET`
  - `PASSWORD`
- keep `scripts/check_deploy_readiness.ps1`, `scripts/validate_local.ps1`, and `scripts/validate_ops_package.ps1` independently runnable
- keep `validate_local.ps1` as the script that owns local FastAPI startup/shutdown and smoke semantics
- keep `validate_ops_package.ps1` as the package-oriented wrapper over `validate_local.ps1`

## 7. Test and validation plan

### Development repo validation commands

Run from:

`D:\Views\yonlab-g2b-agent-v2`

Required commands:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/validate_release.ps1
python -m pytest -q
python -m ruff check app tests
scripts/check_deploy_readiness.ps1
scripts/validate_local.ps1
scripts/validate_ops_package.ps1
```

Expected patterns:

- wrapper:
  - `PASS pytest`
  - `PASS ruff`
  - `PASS check_deploy_readiness`
  - `PASS validate_local`
  - `PASS validate_ops_package`
- pytest:
  - `All tests passed!` or quiet successful exit
- ruff:
  - no findings, zero exit code
- deploy readiness:
  - `"deploy_ready": true`
  - `"real_network_call_attempted": false`
  - `"service_key_exposed": false`
- local validation:
  - `Local validation completed successfully.`
- package validation:
  - `Local operations v1.0 package validation completed.`

### Wrapper coverage strategy

The repository already supports narrow script/documentation verification through:

- `tests/test_smoke_scripts.py`
- `tests/test_local_ops_package.py`

That means rc17 should add string-level coverage instead of inventing a new PowerShell test framework.

Recommended wrapper checks:

- script file exists
- script references `.venv\Scripts\python.exe`
- script references `-m pytest -q`
- script references `-m ruff check app tests`
- script invokes:
  - `scripts/check_deploy_readiness.ps1`
  - `scripts/validate_local.ps1`
  - `scripts/validate_ops_package.ps1`
- script contains no obvious secret-printing markers
- package metadata and docs reference the wrapper as the preferred release command

### Fresh deploy validation commands

Run from:

`D:\Deploy\yonlab-g2b-agent-v2-rc17`

Required commands:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/validate_release.ps1
scripts/check_deploy_readiness.ps1
scripts/validate_local.ps1
scripts/validate_ops_package.ps1
```

Expected patterns:

- wrapper passes from the deployment checkout root
- `"deploy_ready": true`
- `Local validation completed successfully.`
- `Local operations v1.0 package validation completed.`
- `real_api_call_attempted=false`
- `real_network_call_attempted=false`
- `service_key_exposed=false`

## 8. Implementation tasks

### Task 1: Inspect existing validation scripts and docs

**Goal**

Capture the exact current invocation patterns, repo-root assumptions, Python resolution behavior, and no-secret posture before changing anything.

**Files to modify/create**

- No code changes expected.
- Read only:
  - `scripts/check_deploy_readiness.ps1`
  - `scripts/validate_local.ps1`
  - `scripts/validate_ops_package.ps1`
  - `pyproject.toml`
  - `README.md`
  - `docs/04_TESTING_STRATEGY.md`
  - `docs/06_OPERATIONS_RUNBOOK.md`
  - `docs/07_DEPLOYMENT_HANDOFF.md`
  - `docs/99_DECISION_LOG.md`
  - `app/services/local_ops_package.py`
  - `tests/test_local_ops_package.py`
  - `tests/test_smoke_scripts.py`

**Test or validation files**

- `tests/test_local_ops_package.py`
- `tests/test_smoke_scripts.py`

**Specific validation cases**

- verify that `validate_local.ps1` already prefers `.venv\Scripts\python.exe`
- verify that `validate_ops_package.ps1` delegates to `validate_local.ps1`
- verify that `check_deploy_readiness.ps1` is offline and secret-safe
- verify that docs currently advertise legacy validation commands
- verify that existing tests already support string-based script validation

**Implementation steps**

- [ ] Read the existing validation scripts and record:
  - repo-root resolution style
  - Python invocation style
  - PowerShell invocation style
  - whether each script can run offline
- [ ] Read the existing docs and record the validation commands they currently recommend.
- [ ] Read `app/services/local_ops_package.py` and record whether package metadata should advertise the new wrapper.
- [ ] Read `tests/test_local_ops_package.py` and `tests/test_smoke_scripts.py` and confirm they are the correct place for wrapper presence/content assertions.
- [ ] Do not change product code, tests, scripts, or `docs/99_DECISION_LOG.md` in this task.

**Validation commands**

```powershell
git status -sb
rg -n "validate_local|validate_ops_package|check_deploy_readiness|python -m pytest|ruff" README.md docs app tests scripts
```

**Commit message recommendation**

- `chore: inspect rc17 validation entrypoints`

### Task 2: Add release validation wrapper

**Goal**

Create `scripts/validate_release.ps1` as the canonical Windows release validation command.

**Files to modify/create**

- Create:
  - `scripts/validate_release.ps1`

**Test or validation files**

- direct execution first
- later string-level coverage in `tests/test_smoke_scripts.py`

**Specific validation cases**

- wrapper resolves repo root from script location
- wrapper fails with a clear message if `.venv\Scripts\python.exe` is missing
- wrapper runs `pytest` and `ruff` through repo-local Python
- wrapper invokes the three existing validation scripts with `-ExecutionPolicy Bypass`
- wrapper exits on first failure
- wrapper does not print `.env` contents or secrets

**Implementation steps**

- [ ] Create `scripts/validate_release.ps1`.
- [ ] Add UTF-8 console setup consistent with the existing PowerShell scripts.
- [ ] Add a helper function for step framing, for example `Invoke-ReleaseStep`.
- [ ] Resolve `$ProjectRoot` from `$PSScriptRoot` and call `Set-Location $ProjectRoot`.
- [ ] Resolve `$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"`.
- [ ] If `$Python` is missing, print a short non-secret error and `exit 1`.
- [ ] Run:
  - `& $Python -m pytest -q`
  - `& $Python -m ruff check app tests`
  - `powershell -ExecutionPolicy Bypass -File (Join-Path $ProjectRoot "scripts\check_deploy_readiness.ps1")`
  - `powershell -ExecutionPolicy Bypass -File (Join-Path $ProjectRoot "scripts\validate_local.ps1")`
  - `powershell -ExecutionPolicy Bypass -File (Join-Path $ProjectRoot "scripts\validate_ops_package.ps1")`
- [ ] On any non-zero exit, print `FAIL <step>` and return non-zero immediately.
- [ ] After the final step, print `Validation release gate passed.`

**Validation commands**

```powershell
powershell -ExecutionPolicy Bypass -File scripts/validate_release.ps1
```

Expected output patterns:

```text
==> pytest
PASS pytest
==> ruff
PASS ruff
==> check_deploy_readiness
PASS check_deploy_readiness
```

**Commit message recommendation**

- `chore: add rc17 release validation wrapper`

### Task 3: Add wrapper validation coverage and package metadata alignment

**Goal**

Use the existing repository test patterns to verify wrapper existence/content and expose the wrapper in package metadata.

**Files to modify/create**

- Modify:
  - `app/services/local_ops_package.py`
  - `tests/test_local_ops_package.py`
  - `tests/test_smoke_scripts.py`

**Test or validation files**

- `tests/test_local_ops_package.py`
- `tests/test_smoke_scripts.py`

**Specific validation cases**

- `/ops/package-info` includes `scripts/validate_release.ps1`
- package metadata exposes the wrapper as the preferred release validation command
- wrapper file exists
- wrapper references `.venv\Scripts\python.exe`
- wrapper references `pytest`, `ruff`, and all three delegated PowerShell scripts
- wrapper contains no obvious secret-printing pattern

**Implementation steps**

- [ ] Add `scripts/validate_release.ps1` to `PACKAGE_SCRIPTS` in `app/services/local_ops_package.py`.
- [ ] Extend `validation` metadata in `build_local_ops_package_info()` with a new key such as:
  - `"release": "powershell -ExecutionPolicy Bypass -File scripts/validate_release.ps1"`
- [ ] Update `tests/test_local_ops_package.py` to assert:
  - `scripts/validate_release.ps1` exists
  - `/ops/package-info` includes the wrapper reference
  - package validation metadata contains the release wrapper command
- [ ] Update `tests/test_smoke_scripts.py` to assert wrapper content includes:
  - `.venv\\Scripts\\python.exe`
  - `-m pytest -q`
  - `-m ruff check app tests`
  - `check_deploy_readiness.ps1`
  - `validate_local.ps1`
  - `validate_ops_package.ps1`
  - no `SECRET-KEY`
- [ ] Keep the tests narrow and string-based; do not introduce a brittle subprocess-heavy PowerShell test framework here.

**Validation commands**

```powershell
python -m pytest -q tests/test_local_ops_package.py
python -m pytest -q tests/test_smoke_scripts.py
```

Expected output patterns:

- zero exit code
- no assertion mentioning missing `scripts/validate_release.ps1`

**Commit message recommendation**

- `test: cover rc17 release validation wrapper`

### Task 4: Documentation update

**Goal**

Document the wrapper as the preferred Windows release validation entrypoint without exposing `.env` contents or changing decision-log history early.

**Files to modify/create**

- Modify:
  - `README.md`
  - `docs/04_TESTING_STRATEGY.md`
  - `docs/06_OPERATIONS_RUNBOOK.md`
  - `docs/07_DEPLOYMENT_HANDOFF.md`

**Test or validation files**

- `tests/test_local_ops_package.py`
- `tests/test_smoke_scripts.py` if doc presence assertions are extended

**Specific validation cases**

- docs show:
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_release.ps1`
- docs explain:
  - per-process execution policy bypass only
  - no machine-level PowerShell policy change required
  - repo-local `.venv\Scripts\python.exe` is used by the wrapper
- docs do not show:
  - `.env` contents
  - real service key examples

**Implementation steps**

- [ ] Update `README.md` so the preferred release validation command is the wrapper.
- [ ] Update `docs/04_TESTING_STRATEGY.md` so the release validation path is clearly distinguished from the existing local validation path.
- [ ] Update `docs/06_OPERATIONS_RUNBOOK.md` to point operators to the wrapper for release validation.
- [ ] Update `docs/07_DEPLOYMENT_HANDOFF.md` to make the wrapper the canonical pre-release and fresh-deploy command.
- [ ] Keep `docs/99_DECISION_LOG.md` unchanged in this task.

**Validation commands**

```powershell
rg -n "validate_release.ps1|ExecutionPolicy Bypass|\\.venv\\\\Scripts\\\\python.exe" README.md docs
```

Expected output patterns:

- all four doc files reference `scripts/validate_release.ps1`
- no doc line prints a service key or `.env` content

**Commit message recommendation**

- `docs: document rc17 release validation wrapper`

### Task 5: Full local validation

**Goal**

Validate that the wrapper works from the main development checkout and that the legacy commands still pass independently.

**Files to modify/create**

- No new files expected.
- Use the wrapper and the existing scripts exactly as implemented.

**Test or validation files**

- whole test suite
- validation scripts

**Specific validation cases**

- wrapper passes
- pytest passes directly
- ruff passes directly
- deploy readiness returns `deploy_ready=true`
- local validation passes
- ops package validation passes
- no-real confirmation remains explicit

**Implementation steps**

- [ ] Run the wrapper from repo root.
- [ ] Run the legacy direct commands from repo root.
- [ ] Capture the exact output patterns and any step that takes materially longer than expected.
- [ ] If the wrapper fails, fix the wrapper or the narrow documentation/package-metadata integration that caused the failure without changing product behavior.

**Validation commands**

```powershell
powershell -ExecutionPolicy Bypass -File scripts/validate_release.ps1
python -m pytest -q
python -m ruff check app tests
scripts/check_deploy_readiness.ps1
scripts/validate_local.ps1
scripts/validate_ops_package.ps1
```

Expected output patterns:

```text
PASS pytest
PASS ruff
PASS check_deploy_readiness
PASS validate_local
PASS validate_ops_package
```

And:

```text
"deploy_ready": true
real_api_call_attempted=false
real_network_call_attempted=false
service_key_exposed=false
```

**Commit message recommendation**

- `chore: verify rc17 local release validation flow`

### Task 6: Fresh deploy validation

**Goal**

Prove the wrapper works outside the development checkout in a fresh deployment path.

**Files to modify/create**

- No product-code files expected.
- Deployment target:
  - `D:\Deploy\yonlab-g2b-agent-v2-rc17`

**Test or validation files**

- deployment-local validation scripts

**Specific validation cases**

- wrapper works from the fresh deploy root
- deploy readiness is true
- legacy scripts still pass in the fresh deploy
- no-real confirmations remain false
- if `.env` or `.venv` are copied or linked, that fact is reported without exposing contents

**Implementation steps**

- [ ] Create or refresh `D:\Deploy\yonlab-g2b-agent-v2-rc17`.
- [ ] Ensure `.venv` exists in the fresh deploy or record clearly whether it is copied, recreated, or linked.
- [ ] If `.env` is copied for deployment validation, report only that it was present; do not print contents.
- [ ] Run the wrapper and the three legacy validation scripts from the fresh deploy root.
- [ ] Record `deploy_ready=true` and the no-real confirmation fields.

**Validation commands**

```powershell
Set-Location D:\Deploy\yonlab-g2b-agent-v2-rc17
powershell -ExecutionPolicy Bypass -File scripts/validate_release.ps1
scripts/check_deploy_readiness.ps1
scripts/validate_local.ps1
scripts/validate_ops_package.ps1
```

Expected output patterns:

- wrapper passes
- `"deploy_ready": true`
- `real_api_call_attempted=false`
- `real_network_call_attempted=false`
- `service_key_exposed=false`

**Commit message recommendation**

- `chore: validate rc17 release wrapper in fresh deploy`

### Task 7: Decision log update

**Goal**

Update the decision log only after implementation and both validation passes are complete.

**Files to modify/create**

- Modify:
  - `docs/99_DECISION_LOG.md`

**Test or validation files**

- none directly
- rely on the already-passing validation evidence from Tasks 5 and 6

**Specific validation cases**

- decision log records:
  - wrapper command
  - local validation result
  - fresh deploy validation result
  - no-real confirmation
  - no product behavior change confirmation

**Implementation steps**

- [ ] Append one rc17 decision-log entry after all implementation validation is green.
- [ ] Include the preferred wrapper command:
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_release.ps1`
- [ ] Record local and fresh deploy validation outcomes.
- [ ] Record:
  - `real_api_call_attempted=false`
  - `real_network_call_attempted=false`
  - `service_key_exposed=false`
- [ ] Record that rc17 changed validation environment hardening only, not product behavior.

**Validation commands**

```powershell
git diff -- docs/99_DECISION_LOG.md
```

Expected output patterns:

- one new rc17 decision-log entry only
- no secret values

**Commit message recommendation**

- `docs: record rc17 validation hardening result`

## 9. Fresh deploy validation plan

Fresh deploy target:

- `D:\Deploy\yonlab-g2b-agent-v2-rc17`

Required preparation sequence:

- clone or refresh the rc17 target checkout
- ensure `main` or the intended validated rc17 commit is present
- ensure `.venv` exists under the deployment root
- ensure `.env` handling is operator-safe and no contents are echoed

Fresh deploy command set:

```powershell
Set-Location D:\Deploy\yonlab-g2b-agent-v2-rc17
powershell -ExecutionPolicy Bypass -File scripts/validate_release.ps1
scripts/check_deploy_readiness.ps1
scripts/validate_local.ps1
scripts/validate_ops_package.ps1
```

Fresh deploy acceptance criteria:

- wrapper uses deployment-local `.venv\Scripts\python.exe`
- deploy root is resolved from script location, not from the caller's previous shell location
- `deploy_ready=true`
- `real_api_call_attempted=false`
- `real_network_call_attempted=false`
- `service_key_exposed=false`
- no machine-level PowerShell policy changes required

If a copied `.env` or linked `.venv` is used:

- report that it was copied or linked
- do not print its contents
- do not print any path that reveals secret material

## 10. Decision log update policy

The decision log must remain untouched during the planning-only task and during early implementation steps.

Policy for rc17 implementation:

- do not update `docs/99_DECISION_LOG.md` in Task 1, Task 2, Task 3, or Task 4
- update `docs/99_DECISION_LOG.md` only after:
  - `powershell -ExecutionPolicy Bypass -File scripts/validate_release.ps1` passes
  - direct `python -m pytest -q` passes
  - direct `python -m ruff check app tests` passes
  - `scripts/check_deploy_readiness.ps1` passes
  - `scripts/validate_local.ps1` passes
  - `scripts/validate_ops_package.ps1` passes
  - fresh deploy validation at `D:\Deploy\yonlab-g2b-agent-v2-rc17` passes
- record the wrapper command and explicit no-real confirmation fields in the decision log entry

## 11. Self-review checklist

- [ ] The plan only references files that were confirmed to exist in `D:\Views\yonlab-g2b-agent-v2`.
- [ ] The plan keeps rc17 scoped to validation-process hardening only.
- [ ] The plan does not require product code changes under `app/api`, route behavior changes, or new real-network behavior.
- [ ] The plan includes the exact wrapper path: `scripts/validate_release.ps1`.
- [ ] The plan requires repo-local Python at `.venv\Scripts\python.exe`.
- [ ] The plan preserves direct use of:
  - `scripts/check_deploy_readiness.ps1`
  - `scripts/validate_local.ps1`
  - `scripts/validate_ops_package.ps1`
- [ ] The plan includes the required development validation commands.
- [ ] The plan includes the required fresh deploy validation commands.
- [ ] The plan includes explicit no-real confirmation:
  - `real_api_call_attempted=false`
  - `real_network_call_attempted=false`
  - `service_key_exposed=false`
- [ ] The plan makes `docs/99_DECISION_LOG.md` a post-validation update only.
- [ ] The implementation tasks are small, codebase-specific, and include file paths, validation cases, commands, and commit recommendations.
