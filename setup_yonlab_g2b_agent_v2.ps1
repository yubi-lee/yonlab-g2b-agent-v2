param(
    [string]$ProjectRoot = "D:\Views\yonlab-g2b-agent-v2",
    [switch]$ForceOverwrite
)

$ErrorActionPreference = "Stop"

function Write-Info($Message) {
    Write-Host "[INFO] $Message" -ForegroundColor Cyan
}

function Write-Ok($Message) {
    Write-Host "[OK]   $Message" -ForegroundColor Green
}

function Write-Warn($Message) {
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Ensure-Dir($Path) {
    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
        Write-Ok "Created directory: $Path"
    }
}

function Write-TextFile($Path, $Content) {
    $exists = Test-Path $Path
    if ($exists -and -not $ForceOverwrite) {
        Write-Warn "Skipped existing file: $Path"
        return
    }

    $parent = Split-Path -Parent $Path
    if ($parent) {
        Ensure-Dir $parent
    }

    $Content | Set-Content -Path $Path -Encoding UTF8
    if ($exists) {
        Write-Ok "Updated file: $Path"
    } else {
        Write-Ok "Created file: $Path"
    }
}

Write-Info "Initializing YOnLab G2B Agent v2 at: $ProjectRoot"

Ensure-Dir $ProjectRoot
Set-Location $ProjectRoot

# Core directories
$dirs = @(
    "app",
    "app\core",
    "app\api",
    "app\domain",
    "app\integrations",
    "app\integrations\g2b",
    "app\scoring",
    "app\reports",
    "tests",
    "docs",
    "docs\upload_context",
    "data",
    "data\fixtures",
    "data\fixtures\g2b",
    "scripts"
)

foreach ($dir in $dirs) {
    Ensure-Dir (Join-Path $ProjectRoot $dir)
}

# Preserve root-uploaded context docs by copying them into docs/upload_context.
$contextDocs = @(
    "01_YOnLab_Company_Profile_Summary.md",
    "02_G2B_Registration_Qualification_Summary.md",
    "03_v1_Project_Retrospective.md",
    "04_Agent_First_Development_Methodology.md",
    "05_Bid_Recommendation_Report_Example.md"
)

foreach ($doc in $contextDocs) {
    $source = Join-Path $ProjectRoot $doc
    $target = Join-Path $ProjectRoot ("docs\upload_context\" + $doc)
    if ((Test-Path $source) -and -not (Test-Path $target)) {
        Copy-Item $source $target
        Write-Ok "Copied upload context doc to docs\upload_context: $doc"
    }
}

# If a file named AGENTS exists without extension, preserve it.
# Create AGENTS.md as the canonical Codex/OpenAI Agents instruction file.
$agentsMd = @'
# AGENTS.md — YOnLab G2B Agent v2

## Repository identity

This repository is the second-generation YOnLab G2B/Narajangteo AI Bid Recommendation Agent.

It is independent from the previous repository:

- Previous repository: `D:\Views\yonlab-bid-agent`
- Current repository: `D:\Views\yonlab-g2b-agent-v2`

Do not import, copy, or assume previous repository code unless explicitly instructed.

## Product goal

The application should:

1. Retrieve or load Korean procurement notices.
2. Normalize G2B/public procurement data.
3. Evaluate YOnLab eligibility.
4. Score opportunity fit on a 100-point basis.
5. Detect risks such as region restriction, performance requirements, license mismatch, and deadline urgency.
6. Generate a YOnLab-specific recommendation report.

## YOnLab baseline

Use this profile as fixed domain context:

- Company: 주식회사 와이온랩
- Location: 서울특별시 강남구
- Size: 소기업 / 소상공인
- Status: 초기창업기업
- Core qualification: 소프트웨어사업자
- Key procurement categories:
  - 인공지능소프트웨어
  - 정보시스템개발서비스
  - 패키지소프트웨어개발및도입서비스
  - 클라우드소프트웨어
  - 시스템관리소프트웨어
- Core technical strengths:
  - 온디바이스 AI
  - Device Farm
  - AI/SW 원격 검증
  - 로봇/산업용 AI
  - AI Agent
  - 클라우드 시스템

## Architecture rules

- Use FastAPI for the API layer.
- Keep domain logic independent from FastAPI.
- Keep G2B integration logic separate from scoring logic.
- Use fixtures first. Real API calls must be opt-in.
- Use Pydantic models for normalized data.
- Do not hardcode API keys.
- Do not commit `.env`.
- Keep changes small and testable.

## Testing rules

Baseline validation for every coding task:

```powershell
python -m pytest -q
```

Task-specific tests should be run only after those test files exist.

Examples:

```powershell
python -m pytest -q tests/test_app_health.py
```

For future scoring changes, after scoring tests are created:

```powershell
python -m pytest -q tests/test_yonlab_eligibility.py tests/test_score_engine.py
```

For future G2B integration changes, after G2B tests are created:

```powershell
python -m pytest -q tests/test_g2b_normalizer.py
```

Do not treat missing future test files as an application failure during Phase 1 initialization.

## Completion report

Every Codex task must end with:

1. Files changed
2. Behavior changed
3. Tests run
4. Test result
5. Known risks
6. Suggested next task

## Security rules

- Never print or expose API keys.
- Never commit `.env`.
- Use `.env.example` only.
- Real API tests require explicit confirmation.
'@

$readme = @'
# YOnLab G2B Agent v2

YOnLab-specific G2B/Narajangteo AI bid recommendation application.

This repository is a new Agent-first implementation and must remain independent from the previous repository:

- Previous repository: `D:\Views\yonlab-bid-agent`
- Current repository: `D:\Views\yonlab-g2b-agent-v2`

## Current phase

Phase 1: Initial FastAPI baseline.

Implemented:

- Minimal FastAPI app
- `GET /health`
- pytest health test
- project guidance files
- initial docs and scripts

Not implemented yet:

- G2B API integration
- G2B fixtures
- bid normalizer
- YOnLab eligibility engine
- scoring engine
- recommendation report generator
- database
- UI

## Quick start

```powershell
Set-Location D:\Views\yonlab-g2b-agent-v2
.\.venv\Scripts\Activate.ps1
python -m pytest -q
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "app": "YOnLab G2B Agent v2"
}
```

## Development rule

Fixture-first. Test-first. No real API call unless explicitly confirmed.
'@

$gitignore = @'
.venv/
__pycache__/
*.pyc
.env
.env.*
!.env.example
.pytest_cache/
.ruff_cache/
.coverage
htmlcov/
data/raw/
data/private/
*.log
'@

$envExample = @'
APP_ENV=local
APP_NAME=YOnLab G2B Agent v2

G2B_ENABLE_REAL_API=false
G2B_API_BASE_URL=https://apis.data.go.kr
G2B_API_SERVICE_KEY=
G2B_REQUEST_TIMEOUT_SECONDS=15
G2B_DEFAULT_NUM_ROWS=10

LOG_LEVEL=INFO
'@

$pyproject = @'
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
addopts = "-q"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
ignore = []
'@

$appInit = @'
"""YOnLab G2B Agent v2 application package."""
'@

$coreInit = @'
"""Core configuration and infrastructure."""
'@

$apiInit = @'
"""API routes."""
'@

$domainInit = @'
"""Domain models for bid notices and recommendations."""
'@

$integrationsInit = @'
"""External integrations."""
'@

$g2bInit = @'
"""G2B/Narajangteo integration package."""
'@

$scoringInit = @'
"""YOnLab bid-fit scoring package."""
'@

$reportsInit = @'
"""Recommendation report generation package."""
'@

$configPy = @'
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_env: str = "local"
    app_name: str = "YOnLab G2B Agent v2"

    g2b_enable_real_api: bool = False
    g2b_api_base_url: str = "https://apis.data.go.kr"
    g2b_api_service_key: str = ""
    g2b_request_timeout_seconds: int = 15
    g2b_default_num_rows: int = 10

    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
'@

$routesPy = @'
from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_name,
    }
'@

$mainPy = @'
from fastapi import FastAPI

from app.api.routes import router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
    )
    app.include_router(router)

    return app


app = create_app()
'@

$testHealth = @'
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "app": "YOnLab G2B Agent v2",
    }
'@

$runTests = @'
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (Test-Path ".\.venv\Scripts\Activate.ps1") {
    . .\.venv\Scripts\Activate.ps1
}

python -m pytest -q
'@

$devStart = @'
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (Test-Path ".\.venv\Scripts\Activate.ps1") {
    . .\.venv\Scripts\Activate.ps1
}

uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
'@

$checkInitial = @'
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "Project root: $ProjectRoot" -ForegroundColor Cyan
Write-Host ""
Write-Host "Key files:" -ForegroundColor Cyan

$required = @(
    "AGENTS.md",
    "README.md",
    ".gitignore",
    ".env.example",
    "app\main.py",
    "app\api\routes.py",
    "app\core\config.py",
    "tests\test_app_health.py",
    "scripts\run_tests.ps1",
    "scripts\dev_start.ps1"
)

foreach ($item in $required) {
    if (Test-Path $item) {
        Write-Host "[OK]   $item" -ForegroundColor Green
    } else {
        Write-Host "[MISS] $item" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "Running tests..." -ForegroundColor Cyan
python -m pytest -q
'@

$projectCharter = @'
# 00_PROJECT_CHARTER — YOnLab G2B Agent v2

## Purpose

Build a YOnLab-specific AI-assisted procurement opportunity recommendation application.

## Scope

Phase 1 focuses on a clean, testable FastAPI baseline.

Later phases will add:

1. G2B fixture pipeline
2. Notice normalization
3. YOnLab eligibility judgment
4. 100-point scoring engine
5. Risk analysis
6. Markdown recommendation report
7. Real API smoke test
8. Optional UI or dashboard

## Non-goals for Phase 1

- No real API call
- No database
- No UI
- No code copy from `D:\Views\yonlab-bid-agent`
'@

$architecture = @'
# 01_ARCHITECTURE — Initial Architecture

## Layering

```text
API layer       FastAPI routes
Core layer      configuration, logging
Domain layer    procurement notice and recommendation models
Integration     G2B client, fixture loader, normalizer
Scoring layer   eligibility, risk, and score engine
Report layer    deterministic Korean markdown report
```

## Current implementation

Only the API and core configuration baseline are implemented.

```text
GET /health
```

## Rule

Domain and scoring logic must not depend on FastAPI.
'@

$workflow = @'
# 02_AGENT_WORKFLOW — Agent-first Development

## Required task format

Every Codex task should include:

1. Goal
2. Context
3. Constraints
4. Done when
5. Validation commands

## Development flow

```text
Create small task
→ Add/adjust tests
→ Implement minimum code
→ Run pytest
→ Review diff
→ Commit
```

## Baseline validation

```powershell
python -m pytest -q
```

## Key principle

Do not ask Codex to build the whole product at once.
'@

$matchingRules = @'
# 03_YONLAB_MATCHING_RULES — Draft

## YOnLab baseline

- Location: 서울특별시 강남구
- Size: 소기업 / 소상공인
- Status: 초기창업기업
- Qualification: 소프트웨어사업자
- Core capabilities:
  - 온디바이스 AI
  - Device Farm
  - AI/SW 원격 검증
  - 로봇/산업용 AI
  - AI Agent
  - 클라우드 시스템

## Positive signals

- 인공지능소프트웨어
- 정보시스템개발서비스
- 패키지소프트웨어개발및도입서비스
- 클라우드소프트웨어
- 시스템관리소프트웨어
- 소기업/소상공인 제한
- 창업기업 우대
- 서울 지역 제한

## Risk signals

- 타 지역 제한
- 최근 3년 단일 실적 제한
- 대기업/중견기업 중심 참여 구조
- 단순 HW 납품
- 과도한 상주 인력 요구
'@

$testingStrategy = @'
# 04_TESTING_STRATEGY — Initial

## Phase 1 baseline

```powershell
python -m pytest -q
```

Expected:

```text
1 passed
```

## Future test groups

- `test_app_health.py`
- `test_g2b_normalizer.py`
- `test_yonlab_eligibility.py`
- `test_score_engine.py`
- `test_markdown_report.py`

Future test files should be created by the task that implements the corresponding feature.
'@

$decisionLog = @'
# 99_DECISION_LOG

## 2026-06-20

Decision: Create a separate v2 project instead of modifying the existing v1 repository.

Reason:

- Prevent v1/v2 code contamination.
- Test Agent-first development from a clean baseline.
- Keep the first milestone small and verifiable.

Initial validation target:

```powershell
python -m pytest -q
```
'@

# Write files
Write-TextFile (Join-Path $ProjectRoot "AGENTS.md") $agentsMd
Write-TextFile (Join-Path $ProjectRoot "README.md") $readme
Write-TextFile (Join-Path $ProjectRoot ".gitignore") $gitignore
Write-TextFile (Join-Path $ProjectRoot ".env.example") $envExample
Write-TextFile (Join-Path $ProjectRoot "pyproject.toml") $pyproject

Write-TextFile (Join-Path $ProjectRoot "app\__init__.py") $appInit
Write-TextFile (Join-Path $ProjectRoot "app\core\__init__.py") $coreInit
Write-TextFile (Join-Path $ProjectRoot "app\api\__init__.py") $apiInit
Write-TextFile (Join-Path $ProjectRoot "app\domain\__init__.py") $domainInit
Write-TextFile (Join-Path $ProjectRoot "app\integrations\__init__.py") $integrationsInit
Write-TextFile (Join-Path $ProjectRoot "app\integrations\g2b\__init__.py") $g2bInit
Write-TextFile (Join-Path $ProjectRoot "app\scoring\__init__.py") $scoringInit
Write-TextFile (Join-Path $ProjectRoot "app\reports\__init__.py") $reportsInit

Write-TextFile (Join-Path $ProjectRoot "app\core\config.py") $configPy
Write-TextFile (Join-Path $ProjectRoot "app\api\routes.py") $routesPy
Write-TextFile (Join-Path $ProjectRoot "app\main.py") $mainPy

Write-TextFile (Join-Path $ProjectRoot "tests\test_app_health.py") $testHealth

Write-TextFile (Join-Path $ProjectRoot "scripts\run_tests.ps1") $runTests
Write-TextFile (Join-Path $ProjectRoot "scripts\dev_start.ps1") $devStart
Write-TextFile (Join-Path $ProjectRoot "scripts\check_initial_setup.ps1") $checkInitial

Write-TextFile (Join-Path $ProjectRoot "docs\00_PROJECT_CHARTER.md") $projectCharter
Write-TextFile (Join-Path $ProjectRoot "docs\01_ARCHITECTURE.md") $architecture
Write-TextFile (Join-Path $ProjectRoot "docs\02_AGENT_WORKFLOW.md") $workflow
Write-TextFile (Join-Path $ProjectRoot "docs\03_YONLAB_MATCHING_RULES.md") $matchingRules
Write-TextFile (Join-Path $ProjectRoot "docs\04_TESTING_STRATEGY.md") $testingStrategy
Write-TextFile (Join-Path $ProjectRoot "docs\99_DECISION_LOG.md") $decisionLog

Write-Info "Initial file generation finished."

if (Test-Path ".\.venv\Scripts\Activate.ps1") {
    Write-Info "Activating virtual environment."
    . .\.venv\Scripts\Activate.ps1
} else {
    Write-Warn ".venv not found. Create it first if needed: python -m venv .venv"
}

Write-Info "Running initial pytest validation."
python -m pytest -q

Write-Host ""
Write-Ok "Initial setup completed."
Write-Host "Next commands:" -ForegroundColor Cyan
Write-Host "  .\scripts\dev_start.ps1"
Write-Host "  Open http://127.0.0.1:8000/health"
