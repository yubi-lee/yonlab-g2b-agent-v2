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
