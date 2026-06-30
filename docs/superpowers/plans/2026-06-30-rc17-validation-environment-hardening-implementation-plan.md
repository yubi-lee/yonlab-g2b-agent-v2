# rc17 Validation Environment Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reproducible Windows release validation entrypoint that uses repo-local Python and preserves the existing validation scripts.

**Architecture:** Add a narrow PowerShell wrapper at `scripts/validate_release.ps1` that resolves the repo root, validates `.venv\Scripts\python.exe`, runs pytest and ruff through that interpreter, then delegates to the existing validation scripts. Keep product behavior unchanged and update release documentation only after validation passes.

**Tech Stack:** PowerShell, repo-local Python virtual environment, pytest, ruff, existing validation scripts, existing docs/decision-log process.

---

## 1. Scope

This rc17 plan covers only release-validation hardening:

- add `scripts/validate_release.ps1`
- make the wrapper choose `.venv\Scripts\python.exe`
- keep the existing validation scripts directly runnable
- document one canonical Windows-safe validation command
- validate the wrapper in both the dev repo and a fresh deploy copy
- update `docs/99_DECISION_LOG.md` only after implementation validation succeeds

This plan does not change any rc16 product behavior, API behavior, UI behavior, persistence
behavior, or no-real safety gates.

## 2. Non-goals

- no product-code changes under `app/`
- no test-behavior changes unrelated to wrapper/documentation coverage
- no rc16 manual decision workflow changes
- no application refactor
- no new authentication or operator workflow
- no new external dependencies
- no CI/CD overhaul
- no real G2B/API/network execution
- no secrets or `.env` value exposure

## 3. Existing code map

### Existing scripts

- `scripts/check_deploy_readiness.ps1`
  - repo-root readiness and safe configuration summary
  - already returns JSON with `deploy_ready`, `real_network_call_attempted`, and
    `service_key_exposed`
- `scripts/validate_local.ps1`
  - currently resolves repo root
  - optionally activates `.venv\Scripts\Activate.ps1`
  - prefers `.venv\Scripts\python.exe`, but falls back to global `python`
  - runs pytest, starts a temporary local FastAPI server, and runs the offline smoke suite
- `scripts/validate_ops_package.ps1`
  - thin wrapper over `scripts/validate_local.ps1`

### Existing docs

- `README.md`
  - documents `python -m pytest -q` and `.\scripts\validate_local.ps1`
- `docs/04_TESTING_STRATEGY.md`
  - documents the standard validation commands and `validate_local.ps1`
- `docs/06_OPERATIONS_RUNBOOK.md`
  - operator-facing validation flow
- `docs/07_DEPLOYMENT_HANDOFF.md`
  - release/deploy workflow, validation commands, and fresh deploy procedures
- `docs/99_DECISION_LOG.md`
  - release closeout and validation history; should be updated only after rc17 implementation
    validation passes

### Existing script-test pattern

The repository already validates PowerShell scripts by inspecting content rather than executing
every script in unit tests:

- `tests/test_smoke_scripts.py`
  - verifies script existence, UTF-8 handling, guard behavior, and expected command references
- `tests/test_local_ops_package.py`
  - verifies docs and operator surfacing references to validation/package scripts

This means rc17 should extend existing script/doc coverage rather than invent a new testing
pattern unless implementation inspection proves that content-level tests are insufficient.

### Existing runtime constraints

- `pyproject.toml`
  - sets pytest base temp to `.pytest_tmp`
  - does not define a separate task runner
- the repo already assumes a local `.venv`
- current validation semantics must remain unchanged:
  - `scripts/check_deploy_readiness.ps1`
  - `scripts/validate_local.ps1`
  - `scripts/validate_ops_package.ps1`

## 4. Target wrapper behavior

The future wrapper at `scripts/validate_release.ps1` should behave like this:

1. resolve repo root from the script location
2. set UTF-8 console/output defaults consistent with other repo scripts
3. resolve repo-local Python strictly from:
   - `.venv\Scripts\python.exe`
4. fail fast if the repo-local Python does not exist
5. run these steps in this order:
   - `.venv\Scripts\python.exe -m pytest -q`
   - `.venv\Scripts\python.exe -m ruff check app tests`
   - `scripts/check_deploy_readiness.ps1`
   - `scripts/validate_local.ps1`
   - `scripts/validate_ops_package.ps1`
6. invoke existing PowerShell scripts with PowerShell-safe execution
7. print concise step-level PASS/FAIL markers
8. stop immediately on the first failure
9. return non-zero if any step fails
10. avoid printing `.env` contents, service keys, tokens, or secrets

Canonical operator invocation:

- `powershell -ExecutionPolicy Bypass -File scripts/validate_release.ps1`

Non-canonical but preserved commands:

- `python -m pytest -q`
- `python -m ruff check app tests`
- `scripts/check_deploy_readiness.ps1`
- `scripts/validate_local.ps1`
- `scripts/validate_ops_package.ps1`

## 5. Failure behavior

The wrapper should fail clearly and early.

Required failure cases:

1. missing `.venv\Scripts\python.exe`
   - fail before any validation step starts
   - print a concise message telling the operator that repo-local Python is required
2. pytest failure
   - stop immediately
   - return non-zero
3. ruff failure
   - stop immediately
   - return non-zero
4. readiness failure
   - stop immediately
   - return non-zero
5. `validate_local.ps1` failure
   - stop immediately
   - return non-zero
6. `validate_ops_package.ps1` failure
   - stop immediately
   - return non-zero

Failure-reporting rules:

- do not continue after the first failing step
- do not mask the underlying script exit status
- do not dump `.env`
- do not echo secret-bearing environment values

## 6. Security / no-real constraints

The implementation must preserve the existing no-real model:

- no real G2B/Public Data Portal calls
- no real application network calls
- no `.env` value printing
- no service key printing
- no credential/token printing
- no persistence behavior changes
- no automatic runtime gate enabling

Specific implementation constraints:

- the wrapper may call existing scripts, but it must not widen their semantics
- it must not set `YONLAB_AUTO_RUN_REAL_API=true`
- it must not call `validate_real_ops_controlled.ps1 -ConfirmRealApiCall`
- it must not add any real API branch to release validation

## 7. Test and validation plan

### Likely code/test/doc files for implementation

- Create: `scripts/validate_release.ps1`
- Modify: `tests/test_smoke_scripts.py`
- Modify: `tests/test_local_ops_package.py`
- Modify if needed:
  - `README.md`
  - `docs/04_TESTING_STRATEGY.md`
  - `docs/06_OPERATIONS_RUNBOOK.md`
  - `docs/07_DEPLOYMENT_HANDOFF.md`
- Modify only after validation passes:
  - `docs/99_DECISION_LOG.md`

### Expected test strategy

Prefer the existing content-inspection pattern first:

- add a script-existence assertion for `scripts/validate_release.ps1`
- add content assertions that the wrapper:
  - resolves `.venv\Scripts\python.exe`
  - does not fall back to global `python`
  - runs `-m pytest -q`
  - runs `-m ruff check app tests`
  - references `check_deploy_readiness.ps1`
  - references `validate_local.ps1`
  - references `validate_ops_package.ps1`
  - uses PowerShell-safe invocation patterns
  - stays secret-safe

If the current test pattern proves too weak during implementation, only then consider a narrow
execution-style test. That should be a second choice, not the default approach.

### Required validation commands after implementation

From `D:\Views\yonlab-g2b-agent-v2`:

- `powershell -ExecutionPolicy Bypass -File scripts/validate_release.ps1`
- `python -m pytest -q`
- `python -m ruff check app tests`
- `scripts/check_deploy_readiness.ps1`
- `scripts/validate_local.ps1`
- `scripts/validate_ops_package.ps1`

## 8. Implementation tasks

### Task 1: Reconfirm existing validation boundaries

**Files:**

- Inspect: `scripts/check_deploy_readiness.ps1`
- Inspect: `scripts/validate_local.ps1`
- Inspect: `scripts/validate_ops_package.ps1`
- Inspect: `tests/test_smoke_scripts.py`
- Inspect: `tests/test_local_ops_package.py`
- Inspect: `README.md`
- Inspect: `docs/04_TESTING_STRATEGY.md`
- Inspect: `docs/06_OPERATIONS_RUNBOOK.md`
- Inspect: `docs/07_DEPLOYMENT_HANDOFF.md`

- [ ] Confirm the wrapper can remain a narrow orchestration layer rather than refactoring the
      existing scripts.
- [ ] Confirm which tests already assert script presence and content.
- [ ] Confirm which docs should become the canonical home of the new release-validation command.
- [ ] Commit nothing in this task unless inspection reveals a required scope adjustment.

### Task 2: Add `scripts/validate_release.ps1`

**Files:**

- Create: `scripts/validate_release.ps1`

- [ ] Add UTF-8 console/output setup matching the existing script family.
- [ ] Resolve `$ProjectRoot` from `$PSScriptRoot`.
- [ ] Resolve `$Python` strictly as `Join-Path $ProjectRoot ".venv\\Scripts\\python.exe"`.
- [ ] Fail fast with a clear message if that path is missing.
- [ ] Add a small step runner helper so output stays concise and the first failure stops
      execution.
- [ ] Run pytest through repo-local Python.
- [ ] Run ruff through repo-local Python.
- [ ] Invoke `scripts/check_deploy_readiness.ps1` safely.
- [ ] Invoke `scripts/validate_local.ps1` safely.
- [ ] Invoke `scripts/validate_ops_package.ps1` safely.
- [ ] Return non-zero on the first failed validation step.
- [ ] Keep direct script semantics unchanged; do not edit existing scripts unless inspection
      proves a compatibility fix is required.
- [ ] Commit with a wrapper-focused message.

### Task 3: Add wrapper validation coverage

**Files:**

- Modify: `tests/test_smoke_scripts.py`
- Modify if needed: `tests/test_local_ops_package.py`

- [ ] Add a test that `scripts/validate_release.ps1` exists.
- [ ] Add a test that the wrapper references `.venv\\Scripts\\python.exe`.
- [ ] Add a test that the wrapper references `-m pytest -q`.
- [ ] Add a test that the wrapper references `-m ruff check app tests`.
- [ ] Add a test that the wrapper calls:
      - `check_deploy_readiness.ps1`
      - `validate_local.ps1`
      - `validate_ops_package.ps1`
- [ ] Add a test that the wrapper is secret-safe and does not embed sample credentials.
- [ ] Run the targeted test files.
- [ ] Commit the test coverage.

### Task 4: Update validation docs

**Files:**

- Modify: `README.md`
- Modify: `docs/04_TESTING_STRATEGY.md`
- Modify: `docs/06_OPERATIONS_RUNBOOK.md`
- Modify: `docs/07_DEPLOYMENT_HANDOFF.md`

- [ ] Update the primary release-validation command to:
      `powershell -ExecutionPolicy Bypass -File scripts/validate_release.ps1`
- [ ] Keep the legacy direct commands documented for debugging and fallback verification.
- [ ] Document that the wrapper prefers repo-local Python and fails clearly if `.venv` is
      missing.
- [ ] Keep no-real and no-secret guidance unchanged.
- [ ] Do not update `docs/99_DECISION_LOG.md` in this task.
- [ ] Commit the doc updates.

### Task 5: Run full local validation

**Files:**

- Validate only; no required file edits

- [ ] Run:
      `powershell -ExecutionPolicy Bypass -File scripts/validate_release.ps1`
- [ ] Run:
      `python -m pytest -q`
- [ ] Run:
      `python -m ruff check app tests`
- [ ] Run:
      `scripts/check_deploy_readiness.ps1`
- [ ] Run:
      `scripts/validate_local.ps1`
- [ ] Run:
      `scripts/validate_ops_package.ps1`
- [ ] Verify:
      - no real API calls
      - no real network calls
      - no secrets printed
- [ ] If any command fails, fix only wrapper/doc/test changes required for rc17 scope.
- [ ] Commit only after local validation is fully green.

### Task 6: Run fresh deploy validation

**Files:**

- Validate only; no required file edits

- [ ] Create or refresh `D:\Deploy\yonlab-g2b-agent-v2-rc17`.
- [ ] Ensure the deploy copy has a repo-local `.venv` or an equivalent prepared repo-local
      Python path exactly where the wrapper expects it.
- [ ] Run:
      `powershell -ExecutionPolicy Bypass -File scripts/validate_release.ps1`
      from the deploy copy.
- [ ] Re-run:
      - `scripts/check_deploy_readiness.ps1`
      - `scripts/validate_local.ps1`
      - `scripts/validate_ops_package.ps1`
- [ ] Verify:
      - `deploy_ready=true`
      - no-real confirmation remains true
      - no secrets printed
- [ ] Record any deploy-only path assumptions found during validation.
- [ ] Commit nothing in this task unless a wrapper/doc fix is required.

### Task 7: Update decision log after validation passes

**Files:**

- Modify: `docs/99_DECISION_LOG.md`

- [ ] Add a short rc17 validation-environment hardening entry only after:
      - local validation passes
      - fresh deploy validation passes
- [ ] Record that the hardened entrypoint uses repo-local Python and PowerShell-safe
      invocation.
- [ ] Record that existing validation scripts remain independently runnable.
- [ ] Record no-real confirmation results.
- [ ] Commit the decision-log update as the final rc17 implementation closeout commit.

## 9. Fresh deploy validation plan

Fresh deploy validation should happen at:

- `D:\Deploy\yonlab-g2b-agent-v2-rc17`

Required checks in the deploy copy:

1. wrapper command:
   - `powershell -ExecutionPolicy Bypass -File scripts/validate_release.ps1`
2. direct readiness:
   - `scripts/check_deploy_readiness.ps1`
3. direct local validation:
   - `scripts/validate_local.ps1`
4. direct package validation:
   - `scripts/validate_ops_package.ps1`

Expected fresh deploy outcomes:

- wrapper passes end to end
- direct scripts still pass
- `deploy_ready=true`
- `real_api_call_attempted=false`
- `real_network_call_attempted=false`
- `service_key_exposed=false`

Fresh deploy remains a release-validation task, not a scheduler-retargeting task.

## 10. Decision log update policy

- `docs/99_DECISION_LOG.md` must not change during wrapper design or early implementation
  steps
- update `docs/99_DECISION_LOG.md` only after all rc17 implementation validation passes
- the decision-log entry should summarize:
  - the new canonical release-validation command
  - repo-local Python enforcement
  - PowerShell-safe invocation
  - preserved no-real validation behavior

## 11. Self-review checklist

- [ ] The plan keeps rc17 scoped to validation-environment hardening only.
- [ ] The plan does not require product-code changes under `app/`.
- [ ] The plan preserves rc16 manual decision behavior unchanged.
- [ ] The plan uses `scripts/validate_release.ps1` as a narrow wrapper, not a script refactor.
- [ ] The plan preserves existing script semantics and direct usability.
- [ ] The plan includes repo-local `.venv\Scripts\python.exe` enforcement.
- [ ] The plan includes explicit failure behavior for missing `.venv`.
- [ ] The plan includes script-test coverage using existing repo patterns.
- [ ] The plan includes doc updates only where present in this repo.
- [ ] The plan includes full local validation.
- [ ] The plan includes fresh deploy validation at `D:\Deploy\yonlab-g2b-agent-v2-rc17`.
- [ ] The plan postpones `docs/99_DECISION_LOG.md` updates until after implementation
      validation passes.
