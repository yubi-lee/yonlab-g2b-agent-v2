$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$Utf8 = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $Utf8
$OutputEncoding = $Utf8
try { chcp.com 65001 | Out-Null } catch {}

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    Write-Error "Repo-local Python is required for release validation. Missing: $Python"
    exit 1
}

$PowerShellExe = (Get-Command powershell.exe -ErrorAction Stop).Source

function New-StepFailure {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Message,
        [int] $ExitCode = 1
    )

    $Exception = [System.Exception]::new($Message)
    $Exception.Data["ExitCode"] = $ExitCode
    return $Exception
}

function Invoke-PowerShellScriptStep {
    param(
        [Parameter(Mandatory = $true)]
        [string] $ScriptPath
    )

    & $PowerShellExe -NoProfile -ExecutionPolicy Bypass -File $ScriptPath
    if ($LASTEXITCODE -ne 0) {
        throw (New-StepFailure -Message "Validation script failed: $ScriptPath" -ExitCode $LASTEXITCODE)
    }
}

function Invoke-ValidationStep {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Name,
        [Parameter(Mandatory = $true)]
        [scriptblock] $Script
    )

    Write-Host ""
    Write-Host "==> $Name"

    try {
        & $Script
        Write-Host "PASS $Name"
    } catch {
        $ExitCode = 1
        if ($_.Exception.Data.Contains("ExitCode")) {
            $ExitCode = [int] $_.Exception.Data["ExitCode"]
        }
        Write-Host "FAIL $Name"
        Write-Error $_.Exception.Message
        exit $ExitCode
    }
}

Invoke-ValidationStep "pytest" {
    & $Python -m pytest -q
    if ($LASTEXITCODE -ne 0) {
        throw (New-StepFailure -Message "Repo-local Python command failed: -m pytest -q" -ExitCode $LASTEXITCODE)
    }
}

Invoke-ValidationStep "ruff" {
    & $Python -m ruff check app tests
    if ($LASTEXITCODE -ne 0) {
        throw (New-StepFailure -Message "Repo-local Python command failed: -m ruff check app tests" -ExitCode $LASTEXITCODE)
    }
}

Invoke-ValidationStep "check_deploy_readiness" {
    Invoke-PowerShellScriptStep -ScriptPath (Join-Path $ProjectRoot "scripts\check_deploy_readiness.ps1")
}

Invoke-ValidationStep "validate_local" {
    Invoke-PowerShellScriptStep -ScriptPath (Join-Path $ProjectRoot "scripts\validate_local.ps1")
}

Invoke-ValidationStep "validate_ops_package" {
    Invoke-PowerShellScriptStep -ScriptPath (Join-Path $ProjectRoot "scripts\validate_ops_package.ps1")
}
