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
$BaseUri = [System.Uri] $BaseUrl
$ServerHost = $BaseUri.Host
$ServerPort = $BaseUri.Port

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

function Test-RealApiCallExecuted {
    param(
        [Parameter(Mandatory = $false)]
        [object] $Operation
    )

    if ($null -eq $Operation) {
        return $false
    }

    $LocalGateErrors = @(
        "real_ops_disabled",
        "real_api_disabled",
        "real_api_service_key_missing",
        "real_api_endpoint_missing",
        "real_api_confirmation_required"
    )
    if ($Operation.error_code -and $LocalGateErrors -contains $Operation.error_code) {
        return $false
    }

    return $true
}

function Get-FailureClassification {
    param(
        [Parameter(Mandatory = $false)]
        [object] $Operation
    )

    if ($null -eq $Operation -or -not $Operation.error_code) {
        return $null
    }
    if ($Operation.error_code -eq "real_ops_disabled") {
        return "credential/config"
    }
    if ($Operation.error_code -like "*http*" -or $Operation.error_code -like "*transport*") {
        return "transport"
    }
    if ($Operation.error_code -like "*schema*" -or $Operation.error_code -like "*normalization*") {
        return "schema/normalization"
    }
    return "operations"
}

function Get-SafeNextAction {
    param(
        [Parameter(Mandatory = $false)]
        [object] $Operation,
        [Parameter(Mandatory = $false)]
        [object] $OpsReadiness,
        [bool] $ConfirmFlag
    )

    if (-not $ConfirmFlag) {
        return "No-confirm validation completed. Do not run a real call until readiness is green and an operator approves the confirmed command."
    }
    if ($Operation.error_code -eq "real_ops_disabled") {
        return "Set YONLAB_AUTO_RUN_REAL_API=true only for a short controlled validation window, then rerun the confirmed validation once."
    }
    if ($OpsReadiness -and -not $OpsReadiness.ready) {
        return "Resolve /ops/real-readiness missing items before any confirmed real operation."
    }
    return "Review quality summary and report index, then disable the runtime gate after validation."
}

try {
    if (-not (Test-Health)) {
        Write-Host "FastAPI server is not reachable. Starting temporary server..."
        $ServerJob = Start-Job -ScriptBlock {
            param(
                [string] $Root,
                [string] $PythonPath,
                [string] $JobHost,
                [int] $JobPort
            )

            Set-Location $Root
            & $PythonPath -m uvicorn app.main:app --host $JobHost --port $JobPort
        } -ArgumentList $ProjectRoot, $Python, $ServerHost, $ServerPort
        Wait-ForHealth
    }

    $Config = $null
    $Readiness = $null
    $OpsReadiness = $null
    $LatestRunId = $null
    $ReportIndex = $null
    $Quality = $null
    $RealOperation = $null
    $ConfirmedRealStepExecuted = $false
    $RealCallExecuted = $false

    Invoke-ControlledValidationStep "g2b config" {
        $script:Config = Read-JsonEndpoint "/g2b/config"
        $script:Config | ConvertTo-Json -Depth 20
    }

    Invoke-ControlledValidationStep "g2b real readiness" {
        $script:Readiness = Read-JsonEndpoint "/g2b/real-readiness"
        $script:Readiness | ConvertTo-Json -Depth 20
    }

    Invoke-ControlledValidationStep "ops real readiness" {
        $script:OpsReadiness = Read-JsonEndpoint "/ops/real-readiness"
        $script:OpsReadiness | ConvertTo-Json -Depth 20
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
        $script:Quality = Read-JsonEndpoint "/ops/quality-summary"
        if ($script:Quality.latest_run_id) {
            $script:LatestRunId = $script:Quality.latest_run_id
        }
        $script:Quality | ConvertTo-Json -Depth 20
    }

    Invoke-ControlledValidationStep "ops report index" {
        $script:ReportIndex = Read-JsonEndpoint "/ops/report-index?limit=20"
        $script:ReportIndex | ConvertTo-Json -Depth 20
    }

    if ($ConfirmRealApiCall) {
        Invoke-ControlledValidationStep "controlled real operation" {
            $Output = & (Join-Path $ProjectRoot "scripts\run_ops_real_controlled.ps1") -ConfirmRealApiCall
            $Output
            $JsonText = ($Output | Out-String).Trim()
            if (-not [string]::IsNullOrWhiteSpace($JsonText)) {
                $script:RealOperation = $JsonText | ConvertFrom-Json
            }
            $script:ConfirmedRealStepExecuted = $true
            $script:RealCallExecuted = Test-RealApiCallExecuted -Operation $script:RealOperation
        }
        $script:Quality = Read-JsonEndpoint "/ops/quality-summary"
        $script:ReportIndex = Read-JsonEndpoint "/ops/report-index?limit=20"
        if ($script:Quality.latest_run_id) {
            $LatestRunId = $script:Quality.latest_run_id
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
        ops_runtime_gate_enabled = [bool] $OpsReadiness.checks.real_ops_enabled
        controlled_confirm_flag_detected = [bool] $ConfirmRealApiCall
        real_call_executed = [bool] $RealCallExecuted
        real_network_call_attempted = [bool] $RealCallExecuted
        real_report_created = [bool] ($RealOperation -and $RealOperation.report_count -gt 0)
        confirmed_real_step_executed = [bool] $ConfirmedRealStepExecuted
        real_operation_status = $RealOperation.status
        real_operation_error_code = $RealOperation.error_code
        failure_classification = Get-FailureClassification -Operation $RealOperation
        safe_next_action = Get-SafeNextAction -Operation $RealOperation -OpsReadiness $OpsReadiness -ConfirmFlag ([bool] $ConfirmRealApiCall)
        latest_run_id = $LatestRunId
        report_index_reflected = [bool] ($ReportIndex -and $ReportIndex.report_count -gt 0)
        quality_summary_status = $Quality.summary_status
        quality_real_mode_executed = [bool] $Quality.real_mode_executed
    } | ConvertTo-Json -Depth 10
} finally {
    if ($ServerJob) {
        Write-Host ""
        Write-Host "Stopping temporary FastAPI server..."
        Stop-Job -Job $ServerJob -ErrorAction SilentlyContinue
        Remove-Job -Job $ServerJob -Force -ErrorAction SilentlyContinue
    }
}
