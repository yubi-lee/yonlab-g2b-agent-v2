param(
    [switch] $ConfirmRealApiCall
)

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

$BaseUrl = $env:YONLAB_G2B_BASE_URL
if ([string]::IsNullOrWhiteSpace($BaseUrl)) {
    $BaseUrl = "http://127.0.0.1:8000"
}

$ServerJob = $null

function Invoke-ControlledValidationStep {
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

function Test-Health {
    try {
        $Response = Invoke-WebRequest -Method Get -Uri "$BaseUrl/health" -UseBasicParsing
        return $Response.StatusCode -eq 200
    } catch {
        return $false
    }
}

function Wait-ForHealth {
    $Deadline = (Get-Date).AddSeconds(30)
    while ((Get-Date) -lt $Deadline) {
        if (Test-Health) {
            return
        }
        Start-Sleep -Milliseconds 500
    }
    throw "Timed out waiting for $BaseUrl/health"
}

function Read-JsonEndpoint {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Path
    )

    $Response = Invoke-WebRequest -Method Get -Uri "$BaseUrl$Path" -UseBasicParsing
    if ($Response.RawContentStream) {
        $Response.RawContentStream.Position = 0
        $Reader = New-Object System.IO.StreamReader -ArgumentList $Response.RawContentStream, ([System.Text.Encoding]::UTF8)
        $Text = $Reader.ReadToEnd()
    } else {
        $Text = $Response.Content
    }
    return $Text | ConvertFrom-Json
}

try {
    if (-not (Test-Health)) {
        Write-Host "FastAPI server is not reachable. Starting temporary server..."
        $ServerJob = Start-Job -ScriptBlock {
            param(
                [string] $Root,
                [string] $PythonPath
            )

            Set-Location $Root
            & $PythonPath -m uvicorn app.main:app --host 127.0.0.1 --port 8000
        } -ArgumentList $ProjectRoot, $Python
        Wait-ForHealth
    }

    $Config = $null
    $Readiness = $null
    $LatestRunId = $null
    $RealCallExecuted = $false

    Invoke-ControlledValidationStep "g2b config" {
        $script:Config = Read-JsonEndpoint "/g2b/config"
        $script:Config | ConvertTo-Json -Depth 20
    }

    Invoke-ControlledValidationStep "g2b real readiness" {
        $script:Readiness = Read-JsonEndpoint "/g2b/real-readiness"
        $script:Readiness | ConvertTo-Json -Depth 20
    }

    Invoke-ControlledValidationStep "guard blocked real smoke" {
        & (Join-Path $ProjectRoot "scripts\smoke_g2b_real_guard_blocked.ps1")
    }

    Invoke-ControlledValidationStep "ops runs" {
        $Runs = Read-JsonEndpoint "/ops/runs?limit=1"
        if ($Runs.runs -and $Runs.runs.Count -gt 0) {
            $script:LatestRunId = $Runs.runs[0].run_id
        }
        $Runs | ConvertTo-Json -Depth 20
    }

    Invoke-ControlledValidationStep "ops recommendations" {
        Read-JsonEndpoint "/ops/recommendations?limit=5" | ConvertTo-Json -Depth 20
    }

    Invoke-ControlledValidationStep "ops quality summary" {
        $Quality = Read-JsonEndpoint "/ops/quality-summary"
        if ($Quality.latest_run_id) {
            $script:LatestRunId = $Quality.latest_run_id
        }
        $Quality | ConvertTo-Json -Depth 20
    }

    if ($ConfirmRealApiCall) {
        Invoke-ControlledValidationStep "controlled real operation" {
            & (Join-Path $ProjectRoot "scripts\run_ops_real_controlled.ps1") -ConfirmRealApiCall
            $script:RealCallExecuted = $true
        }
        $Quality = Read-JsonEndpoint "/ops/quality-summary"
        if ($Quality.latest_run_id) {
            $LatestRunId = $Quality.latest_run_id
        }
    } else {
        Write-Host ""
        Write-Host "Confirmed real operation skipped. Pass -ConfirmRealApiCall to execute one."
    }

    Write-Host ""
    Write-Host "Controlled real operations validation summary:"
    @{
        real_api_enabled = [bool] $Config.real_api_enabled
        service_key_configured = [bool] $Config.service_key_configured
        endpoint_path_configured = [bool] $Config.endpoint_path_configured
        readiness = [bool] $Readiness.ready
        real_call_executed = [bool] $RealCallExecuted
        latest_run_id = $LatestRunId
    } | ConvertTo-Json -Depth 10
} finally {
    if ($ServerJob) {
        Write-Host ""
        Write-Host "Stopping temporary FastAPI server..."
        Stop-Job -Job $ServerJob -ErrorAction SilentlyContinue
        Remove-Job -Job $ServerJob -Force -ErrorAction SilentlyContinue
    }
}
