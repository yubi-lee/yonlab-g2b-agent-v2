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

$ServerJob = $null

function Test-WritableDirectory {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Path
    )

    try {
        New-Item -ItemType Directory -Force -Path $Path | Out-Null
        $ProbePath = Join-Path $Path ".write_probe"
        "ok" | Out-File -LiteralPath $ProbePath -Encoding utf8
        Remove-Item -LiteralPath $ProbePath -Force
        return $true
    } catch {
        return $false
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
    & $Script
}

function Wait-ForHealth {
    param(
        [string] $Uri = "http://127.0.0.1:8000/health",
        [int] $TimeoutSeconds = 30
    )

    $Deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $Deadline) {
        try {
            $Response = Invoke-WebRequest -Method Get -Uri $Uri -UseBasicParsing
            if ($Response.StatusCode -eq 200) {
                $Payload = $Response.Content | ConvertFrom-Json
                if ($Payload.status -eq "ok") {
                    return
                }
            }
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }

    throw "Timed out waiting for $Uri"
}

$ValidationDataRoot = Join-Path $ProjectRoot ".local_validation_data"
if (-not (Test-WritableDirectory -Path $ValidationDataRoot)) {
    $DocumentsRoot = [Environment]::GetFolderPath("MyDocuments")
    $ValidationDataRoot = Join-Path $DocumentsRoot "YOnLab G2B Agent v2\.local_validation_data"
    if (-not (Test-WritableDirectory -Path $ValidationDataRoot)) {
        $HangulDocuments = -join ([char] 0xBB38, [char] 0xC11C)
        $ValidationDataRoot = Join-Path $env:USERPROFILE "OneDrive\$HangulDocuments\YOnLab G2B Agent v2\.local_validation_data"
    }
    if (-not (Test-WritableDirectory -Path $ValidationDataRoot)) {
        throw "No writable validation data directory is available."
    }
}

$env:YONLAB_STORAGE_DB_PATH = Join-Path $ValidationDataRoot "ops\yonlab_g2b_agent.sqlite3"
$env:YONLAB_REPORT_DIR = Join-Path $ValidationDataRoot "reports\g2b"

try {
    Invoke-ValidationStep "check_no_secrets" {
        & (Join-Path $ProjectRoot "scripts\check_no_secrets.ps1")
    }

    Invoke-ValidationStep "pytest" {
        & $Python -m pytest -q
        if ($LASTEXITCODE -ne 0) {
            throw "pytest failed."
        }
    }

    Write-Host ""
    Write-Host "==> starting FastAPI server"
    $ServerJob = Start-Job -ScriptBlock {
        param(
            [string] $Root,
            [string] $PythonPath
        )

        Set-Location $Root
        & $PythonPath -m uvicorn app.main:app --host 127.0.0.1 --port 8000
    } -ArgumentList $ProjectRoot, $Python

    Wait-ForHealth

    Invoke-ValidationStep "smoke_g2b_config" {
        & (Join-Path $ProjectRoot "scripts\smoke_g2b_config.ps1")
    }
    Invoke-ValidationStep "smoke_g2b_endpoint_presets" {
        & (Join-Path $ProjectRoot "scripts\smoke_g2b_endpoint_presets.ps1")
    }
    Invoke-ValidationStep "smoke_g2b_real_readiness" {
        & (Join-Path $ProjectRoot "scripts\smoke_g2b_real_readiness.ps1")
    }
    Invoke-ValidationStep "smoke_g2b_search_fixture" {
        & (Join-Path $ProjectRoot "scripts\smoke_g2b_search_fixture.ps1")
    }
    Invoke-ValidationStep "smoke_g2b_recommend_fixture" {
        & (Join-Path $ProjectRoot "scripts\smoke_g2b_recommend_fixture.ps1")
    }
    Invoke-ValidationStep "smoke_ui_health" {
        & (Join-Path $ProjectRoot "scripts\smoke_ui_health.ps1")
    }
    Invoke-ValidationStep "smoke_ops_package_info" {
        & (Join-Path $ProjectRoot "scripts\smoke_ops_package_info.ps1")
    }
    Invoke-ValidationStep "smoke_ops_real_readiness" {
        & (Join-Path $ProjectRoot "scripts\smoke_ops_real_readiness.ps1")
    }
    Invoke-ValidationStep "smoke_ops_review_board" {
        & (Join-Path $ProjectRoot "scripts\smoke_ops_review_board.ps1")
    }
    Invoke-ValidationStep "run_ops_fixture" {
        & (Join-Path $ProjectRoot "scripts\run_ops_fixture.ps1")
    }
    Invoke-ValidationStep "smoke_ops_quality_summary" {
        & (Join-Path $ProjectRoot "scripts\smoke_ops_quality_summary.ps1")
    }
    Invoke-ValidationStep "smoke_ops_report_index" {
        & (Join-Path $ProjectRoot "scripts\smoke_ops_report_index.ps1")
    }
    Invoke-ValidationStep "smoke_ops_ui_flow" {
        & (Join-Path $ProjectRoot "scripts\smoke_ops_ui_flow.ps1")
    }
    Invoke-ValidationStep "show_ops_runs" {
        & (Join-Path $ProjectRoot "scripts\show_ops_runs.ps1")
    }
    Invoke-ValidationStep "show_ops_recommendations" {
        & (Join-Path $ProjectRoot "scripts\show_ops_recommendations.ps1")
    }
    Invoke-ValidationStep "smoke_g2b_document_risk_analysis" {
        & (Join-Path $ProjectRoot "scripts\smoke_g2b_document_risk_analysis.ps1")
    }
    Invoke-ValidationStep "smoke_g2b_pdf_analysis_candidates_fixture" {
        & (Join-Path $ProjectRoot "scripts\smoke_g2b_pdf_analysis_candidates_fixture.ps1")
    }
    Invoke-ValidationStep "smoke_g2b_pdf_text_analysis_fixture" {
        & (Join-Path $ProjectRoot "scripts\smoke_g2b_pdf_text_analysis_fixture.ps1")
    }
    Invoke-ValidationStep "smoke_g2b_real_guard_blocked" {
        & (Join-Path $ProjectRoot "scripts\smoke_g2b_real_guard_blocked.ps1")
    }
    Invoke-ValidationStep "smoke_report" {
        & (Join-Path $ProjectRoot "scripts\smoke_report.ps1")
    }

    Write-Host ""
    Write-Host "Local validation completed successfully."
} finally {
    if ($ServerJob) {
        Write-Host ""
        Write-Host "==> stopping FastAPI server"
        Stop-Job -Job $ServerJob -ErrorAction SilentlyContinue
        Remove-Job -Job $ServerJob -Force -ErrorAction SilentlyContinue
    }
}
