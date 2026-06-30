# rc17 Validation Environment Hardening Design

## Problem

The rc16 release-promotion flow exposed a validation-environment reproducibility issue rather
than a product defect.

Observed behavior during rc16 promotion:

- the default shell `python` command did not reliably resolve to the repository `.venv`
- the default PowerShell policy did not reliably allow direct script execution from the repo
  root
- the rc16 release gate still passed when the same checks were run with repo-local
  `.venv\Scripts\python.exe` and `ExecutionPolicy Bypass`-equivalent invocation

That was acceptable for rc16 because the product, tests, and docs did not require changes for
correctness. It is still a release-process risk because future releases need a clearer,
repeatable Windows validation path that does not depend on global shell correctness.

## Goals

- provide one documented Windows release validation entrypoint
- prefer repo-local Python resolution when available
- remove dependency on global `python` path correctness for the main release-validation path
- avoid requiring machine-level PowerShell policy changes
- keep existing validation scripts usable on their own
- keep fresh deploy validation possible
- preserve the existing no-real safety model

## Non-goals

- no product behavior changes
- no rc16 manual decision changes
- no application refactor
- no authentication or user-workflow changes
- no external database additions
- no CI/CD overhaul unless a minimal existing repo pattern clearly supports it later
- no secrets exposure
- no real API calls
- no real network calls from the application

## Current validation commands

The current release gate is built from these commands:

- `python -m pytest -q`
- `python -m ruff check app tests`
- `scripts/check_deploy_readiness.ps1`
- `scripts/validate_local.ps1`
- `scripts/validate_ops_package.ps1`

Current global-shell dependencies:

1. `python -m pytest -q`
   - depends on the active shell resolving `python` to an interpreter that has the repo test
     dependencies installed
2. `python -m ruff check app tests`
   - depends on the active shell resolving `python` to an interpreter that can run `ruff`
3. `scripts/check_deploy_readiness.ps1`
   - can be blocked by PowerShell execution policy when invoked directly
4. `scripts/validate_local.ps1`
   - contains repo-local Python fallback logic internally, but direct invocation can still be
     blocked before the script body runs
5. `scripts/validate_ops_package.ps1`
   - calls `scripts/validate_local.ps1`, so it inherits the same direct-script invocation risk

The current repo already partially mitigates Python resolution inside
`scripts/validate_local.ps1` by preferring `.venv\Scripts\python.exe` when available, but the
top-level release-validation path still depends on how the outer shell launches commands.

## Current risk observed during rc16

The rc16 release-promotion run established these facts:

- shell default python / PowerShell policy were not release-ready
- validation passed with repo `.venv` and `ExecutionPolicy Bypass` equivalents
- product/test/docs changes were not required for rc16 promotion
- this is a release-process reproducibility risk, not an rc16 feature defect

rc17 should harden the validation entrypoint so the expected Windows release command is
explicit, repeatable, and repo-local-first.

## Proposed approach

Use the smallest change that improves reproducibility without changing rc16 product behavior or
rewriting the current validation scripts.

### Approach options

#### Approach 1: Documentation only

Document that release promotion should use repo `.venv` plus `ExecutionPolicy Bypass`, but do
not add a wrapper.

Pros:

- smallest documentation-only change
- no new script to maintain

Cons:

- still leaves operators stitching multiple commands together
- still duplicates release-gate invocation knowledge across docs and operator habits
- does not create one canonical release-validation entrypoint

#### Approach 2: Add a repo-local validation wrapper

Add a narrow release wrapper script that resolves repo-local Python and invokes the existing
validation scripts in a PowerShell-safe way.

Pros:

- one canonical Windows entrypoint
- explicit repo-local interpreter selection
- no need for machine-level PowerShell policy change
- preserves existing validation script semantics

Cons:

- adds one new script to maintain
- still requires `.venv` to exist locally

#### Approach 3: Broader validation framework refactor

Rework existing scripts into a larger orchestrated validation subsystem.

Pros:

- could centralize more behavior long term

Cons:

- too large for rc17
- higher regression risk
- not necessary to solve the observed rc16 issue

### Chosen approach

Choose **Approach 2**.

The eventual rc17 implementation should add:

- `scripts/validate_release.ps1`

The wrapper should:

1. resolve the repository root from the script location
2. locate `.venv\Scripts\python.exe`
3. fail fast with a clear message if repo-local Python is missing
4. run pytest through the repo-local Python
5. run ruff through the repo-local Python
6. call existing validation scripts using PowerShell-safe invocation
7. avoid printing secrets or `.env` contents
8. stop on first failure and return a non-zero exit code

The wrapper should not replace the existing scripts. It should only provide one stable release
entrypoint that composes them.

Preferred operator-facing invocation:

- `powershell -ExecutionPolicy Bypass -File scripts/validate_release.ps1`

The existing scripts should remain directly runnable:

- `scripts/check_deploy_readiness.ps1`
- `scripts/validate_local.ps1`
- `scripts/validate_ops_package.ps1`

## Candidate files to inspect

The eventual rc17 implementation should inspect these existing repo files:

- `scripts/check_deploy_readiness.ps1`
- `scripts/validate_local.ps1`
- `scripts/validate_ops_package.ps1`
- `pyproject.toml`
- `README.md`
- `docs/04_TESTING_STRATEGY.md`
- `docs/06_OPERATIONS_RUNBOOK.md`
- `docs/07_DEPLOYMENT_HANDOFF.md`
- `docs/99_DECISION_LOG.md`

These paths are present in the current repository and are the most relevant places to align the
future wrapper behavior and documentation.

## Candidate files to modify in implementation

Likely future rc17 implementation files:

- `scripts/validate_release.ps1`
- `README.md`, if the canonical release-validation command should be updated there
- `docs/04_TESTING_STRATEGY.md`, if the standard command set needs explicit repo-local wrapper
  guidance
- `docs/06_OPERATIONS_RUNBOOK.md`, if operator workflow docs should point to the wrapper
- `docs/07_DEPLOYMENT_HANDOFF.md`, if release and fresh deploy instructions should point to the
  wrapper
- `docs/99_DECISION_LOG.md`, but only after implementation and validation pass

Product code and tests should not need changes for rc17 unless later inspection proves an
unexpected validation-coupling problem.

## Acceptance criteria

The eventual rc17 implementation should satisfy all of the following:

- a developer on Windows can run one documented release validation command from repo root
- the command uses `.venv\Scripts\python.exe` when present
- the command does not rely on global Python path correctness
- the command does not require machine-level PowerShell policy changes
- the command runs pytest, ruff, deploy readiness, local validation, and ops package validation
- existing validation scripts still pass independently
- fresh deploy validation remains possible
- no real API calls or real network calls are introduced
- no secrets are printed
- rc16 product behavior remains unchanged

## Validation plan

Future implementation validation should be run from:

- `D:\Views\yonlab-g2b-agent-v2`

Required checks:

- `powershell -ExecutionPolicy Bypass -File scripts/validate_release.ps1`
- `python -m pytest -q`
- `python -m ruff check app tests`
- `scripts/check_deploy_readiness.ps1`
- `scripts/validate_local.ps1`
- `scripts/validate_ops_package.ps1`

Fresh deploy validation should also be run from:

- `D:\Deploy\yonlab-g2b-agent-v2-rc17`

Fresh deploy checks should include:

- wrapper validation
- existing validation scripts
- `deploy_ready=true`
- no-real confirmation

The intended interpretation is:

- the wrapper becomes the canonical release-validation entrypoint
- the older direct commands remain available for debugging and fallback verification
- fresh deploy validation must confirm the wrapper works outside the original dev checkout

## Risks / follow-up

- environments without `.venv` need a clear failure message
- `ExecutionPolicy Bypass` may still be needed per process, but it should not require a
  machine-level policy change
- the wrapper must not mask failures from underlying scripts
- the wrapper must not print `.env` contents or secrets
- scheduler retargeting and product feature work should remain separate tasks

## Decision log policy

- `docs/99_DECISION_LOG.md` should not be updated in this design-only task
- `docs/99_DECISION_LOG.md` should be updated only after rc17 implementation and validation pass
