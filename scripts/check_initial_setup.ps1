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
