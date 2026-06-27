param(
    [string] $DeployPath = "",
    [int] $Port = 8010,
    [switch] $RunLocalValidation,
    [switch] $RunUiSmoke
)

$ErrorActionPreference = "Stop"

$Utf8 = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $Utf8
$OutputEncoding = $Utf8
try { chcp.com 65001 | Out-Null } catch {}

function Resolve-EffectiveDeployPath {
    param([string] $RequestedDeployPath)

    if (-not [string]::IsNullOrWhiteSpace($RequestedDeployPath)) {
        return (Resolve-Path -LiteralPath $RequestedDeployPath).Path
    }

    $ScriptRepoRoot = Split-Path -Parent $PSScriptRoot
    if (Test-Path -LiteralPath (Join-Path $ScriptRepoRoot "scripts") -PathType Container) {
        return (Resolve-Path -LiteralPath $ScriptRepoRoot).Path
    }

    $CurrentPath = (Get-Location).Path
    if (Test-Path -LiteralPath (Join-Path $CurrentPath "scripts") -PathType Container) {
        return (Resolve-Path -LiteralPath $CurrentPath).Path
    }

    throw "Unable to resolve deployment path. Pass -DeployPath explicitly."
}

$ResolvedDeployPath = Resolve-EffectiveDeployPath -RequestedDeployPath $DeployPath
Set-Location $ResolvedDeployPath

$DateStamp = Get-Date -Format "yyyyMMdd"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogDir = Join-Path $ResolvedDeployPath "logs\ops\$DateStamp"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$LogPath = Join-Path $LogDir "ops_safe_daily_$Timestamp.log"

$Python = Join-Path $ResolvedDeployPath ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    $Python = "python"
}

$env:YONLAB_STORAGE_DB_PATH = Join-Path $ResolvedDeployPath "data\ops\yonlab_g2b_agent.sqlite3"
$env:YONLAB_REPORT_DIR = Join-Path $ResolvedDeployPath "data\reports\g2b"
$env:YONLAB_G2B_BASE_URL = "http://127.0.0.1:$Port"
Remove-Item Env:\YONLAB_AUTO_RUN_REAL_API -ErrorAction SilentlyContinue

$ServerJob = $null
$StartedServer = $false
$StepResults = New-Object System.Collections.Generic.List[object]

function Write-LogLine {
    param([string] $Message)
    $Line = "[$((Get-Date).ToString('s'))] $Message"
    Add-Content -LiteralPath $LogPath -Value $Line -Encoding utf8
}

function Invoke-LoggedStep {
    param(
        [string] $Name,
        [scriptblock] $Script
    )

    Write-LogLine "==> $Name"
    try {
        $Output = & $Script 2>&1
        if ($Output) {
            $Output | ForEach-Object { Add-Content -LiteralPath $LogPath -Value $_ -Encoding utf8 }
        }
        $StepResults.Add([pscustomobject]@{ name = $Name; status = "pass" }) | Out-Null
    } catch {
        Write-LogLine "FAILED: $($_.Exception.Message)"
        $StepResults.Add([pscustomobject]@{ name = $Name; status = "fail" }) | Out-Null
        throw
    }
}

function Test-Health {
    try {
        $Response = Invoke-WebRequest `
            -Method Get `
            -Uri "$env:YONLAB_G2B_BASE_URL/health" `
            -UseBasicParsing
        return ($Response.StatusCode -eq 200)
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
    throw "Timed out waiting for local operations server."
}

try {
    Write-LogLine "YOnLab G2B Agent v2 safe daily operation started."
    Write-LogLine "Deploy path: $ResolvedDeployPath"
    Write-LogLine "Real API auto-run gate: removed"

    Invoke-LoggedStep "deploy readiness" {
        & (Join-Path $ResolvedDeployPath "scripts\check_deploy_readiness.ps1")
    }
    Invoke-LoggedStep "real ops readiness (offline)" {
        & (Join-Path $ResolvedDeployPath "scripts\check_real_ops_readiness.ps1")
    }

    if (-not (Test-Health)) {
        Write-LogLine "Starting temporary local operations server on port $Port."
        $ServerJob = Start-Job -ScriptBlock {
            param($Root, $PythonPath, $JobPort, $StoragePath, $ReportDir)
            Set-Location $Root
            $env:YONLAB_STORAGE_DB_PATH = $StoragePath
            $env:YONLAB_REPORT_DIR = $ReportDir
            Remove-Item Env:\YONLAB_AUTO_RUN_REAL_API -ErrorAction SilentlyContinue
            & $PythonPath -m uvicorn app.main:app --host 127.0.0.1 --port $JobPort
        } -ArgumentList (
            $ResolvedDeployPath,
            $Python,
            $Port,
            $env:YONLAB_STORAGE_DB_PATH,
            $env:YONLAB_REPORT_DIR
        )
        $StartedServer = $true
        Wait-ForHealth
    }

    Invoke-LoggedStep "ops quality summary smoke" {
        & (Join-Path $ResolvedDeployPath "scripts\smoke_ops_quality_summary.ps1")
    }
    Invoke-LoggedStep "ops report index smoke" {
        & (Join-Path $ResolvedDeployPath "scripts\smoke_ops_report_index.ps1")
    }

    if ($RunUiSmoke) {
        Invoke-LoggedStep "ui health smoke" {
            & (Join-Path $ResolvedDeployPath "scripts\smoke_ui_health.ps1")
        }
    }

    if ($RunLocalValidation) {
        Invoke-LoggedStep "local validation" {
            Remove-Item Env:\YONLAB_G2B_BASE_URL -ErrorAction SilentlyContinue
            & (Join-Path $ResolvedDeployPath "scripts\validate_local.ps1")
            $env:YONLAB_G2B_BASE_URL = "http://127.0.0.1:$Port"
        }
    }

    Write-LogLine "Safe daily operation completed."
    [pscustomobject]@{
        status = "success"
        log_path = $LogPath
        steps = $StepResults
        real_api_call_attempted = $false
        service_key_exposed = $false
    } | ConvertTo-Json -Depth 8
} finally {
    if ($StartedServer -and $ServerJob) {
        Stop-Job $ServerJob -ErrorAction SilentlyContinue
        Remove-Job $ServerJob -Force -ErrorAction SilentlyContinue
    }
    Remove-Item Env:\YONLAB_AUTO_RUN_REAL_API -ErrorAction SilentlyContinue
    Remove-Item Env:\YONLAB_G2B_BASE_URL -ErrorAction SilentlyContinue
    Remove-Item Env:\YONLAB_STORAGE_DB_PATH -ErrorAction SilentlyContinue
    Remove-Item Env:\YONLAB_REPORT_DIR -ErrorAction SilentlyContinue
}