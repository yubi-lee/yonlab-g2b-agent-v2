$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$Utf8 = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $Utf8
$OutputEncoding = $Utf8
try { chcp.com 65001 | Out-Null } catch {}

$ActivateScript = Join-Path $ProjectRoot ".venv\Scripts\Activate.ps1"
if (Test-Path -LiteralPath $ActivateScript) {
    . $ActivateScript
}

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    $Python = "python"
}

function Invoke-ReadinessStep {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Name,
        [Parameter(Mandatory = $true)]
        [scriptblock] $Script
    )

    Write-Host ""
    Write-Host "==> $Name"
    & $Script
}

Invoke-ReadinessStep "no-secret validation" {
    & (Join-Path $ProjectRoot "scripts\check_no_secrets.ps1")
}

Invoke-ReadinessStep "offline readiness tests" {
    & $Python -m pytest -q `
        tests\test_g2b_client.py `
        tests\test_g2b_endpoint_presets.py `
        tests\test_g2b_pipeline_api.py `
        tests\test_g2b_readiness.py `
        tests\test_smoke_scripts.py
    if ($LASTEXITCODE -ne 0) {
        throw "Offline readiness tests failed."
    }
}

Invoke-ReadinessStep "readiness summary" {
    & $Python -m app.integrations.g2b.readiness
    if ($LASTEXITCODE -ne 0) {
        throw "Readiness summary failed."
    }
}

Write-Host ""
Write-Host "Guarded real-readiness validation completed without calling the real API."
