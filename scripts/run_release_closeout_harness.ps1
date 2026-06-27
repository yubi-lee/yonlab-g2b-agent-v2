param(
    [string] $ReleaseTag = "v0.1.0-rc3",
    [string] $DeployRoot = "D:\Deploy",
    [string] $DeployFolderName = "",
    [switch] $RunControlledRealCall,
    [switch] $ConfirmRealApiCall,
    [switch] $SkipPush
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$Utf8 = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $Utf8
$OutputEncoding = $Utf8
try { chcp.com 65001 | Out-Null } catch {}

if ([string]::IsNullOrWhiteSpace($DeployFolderName)) {
    $DeploySuffix = $ReleaseTag.Replace("v0.1.0-", "")
    $DeployFolderName = "yonlab-g2b-agent-v2-$DeploySuffix"
}

$Summary = [ordered]@{
    development_repo_status = ""
    commit_hash = ""
    tag_name = $ReleaseTag
    tag_push_result = "not_attempted"
    main_push_result = "not_attempted"
    fresh_deployment_path = ""
    project_path_ok = $false
    env_file_present = $false
    ready_for_controlled_real_call = $false
    deploy_ready = $false
    pytest_result = "not_run"
    validate_local_result = "not_run"
    no_secret_result = "not_run"
    korean_artifact_result = "not_run"
    ui_api_smoke_result = "not_run"
    controlled_real_run_executed = $false
    additional_real_api_call_count = 0
    deployment_status = "blocked"
    remaining_blocking_issues = @()
}

function Write-Step {
    param([string] $Message)
    Write-Host ""
    Write-Host "==> $Message"
}

function Invoke-Checked {
    param(
        [string] $Name,
        [scriptblock] $Script
    )

    Write-Step $Name
    & $Script
}

function Invoke-Native {
    param(
        [string] $FilePath,
        [string[]] $Arguments = @(),
        [string] $WorkingDirectory = $ProjectRoot
    )

    Push-Location $WorkingDirectory
    try {
        & $FilePath @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "$FilePath exited with code $LASTEXITCODE."
        }
    } finally {
        Pop-Location
    }
}

function Get-PythonPath {
    param([string] $Root)

    $Python = Join-Path $Root ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $Python) {
        return $Python
    }
    return "python"
}

function Get-ReadinessPayload {
    param([string] $Root)

    $Python = Get-PythonPath -Root $Root
    Push-Location $Root
    try {
        $Text = & $Python -m app.services.real_ops_runtime_readiness
        if ($LASTEXITCODE -ne 0) {
            throw "real ops readiness exited with code $LASTEXITCODE."
        }
        return ($Text | ConvertFrom-Json)
    } finally {
        Pop-Location
    }
}

function Wait-ForEndpoint {
    param(
        [string] $Url,
        [int] $Attempts = 30
    )

    for ($Index = 0; $Index -lt $Attempts; $Index += 1) {
        try {
            Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2 | Out-Null
            return
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    throw "Endpoint did not become reachable: $Url"
}

function Invoke-UiApiSmoke {
    param(
        [string] $Root,
        [int] $Port = 8010
    )

    $Python = Get-PythonPath -Root $Root
    $Job = Start-Job -ScriptBlock {
        param($JobRoot, $JobPython, $JobPort)
        Set-Location $JobRoot
        & $JobPython -m uvicorn app.main:app --host 127.0.0.1 --port $JobPort
    } -ArgumentList $Root, $Python, $Port

    $BaseUrl = "http://127.0.0.1:$Port"
    try {
        Wait-ForEndpoint -Url "$BaseUrl/health"
        $Quality = Invoke-RestMethod "$BaseUrl/ops/quality-summary"
        $ReportIndex = Invoke-RestMethod "$BaseUrl/ops/report-index"
        $Ui = Invoke-WebRequest "$BaseUrl/ui" -UseBasicParsing
        if ($Quality.service_key_exposed -ne $false) {
            throw "quality-summary exposed service key flag."
        }
        if ($ReportIndex.service_key_exposed -ne $false) {
            throw "report-index exposed service key flag."
        }
        if ($Ui.StatusCode -ne 200) {
            throw "ui returned status $($Ui.StatusCode)."
        }
        return @{
            port = $Port
            quality_summary = $Quality.summary_status
            report_index = $ReportIndex.status
            ui_status = $Ui.StatusCode
        }
    } finally {
        Stop-Job $Job -ErrorAction SilentlyContinue
        Remove-Job $Job -Force -ErrorAction SilentlyContinue
    }
}

try {
    Remove-Item Env:\YONLAB_AUTO_RUN_REAL_API -ErrorAction SilentlyContinue

    Invoke-Checked "development preflight" {
        $Summary.development_repo_status = (git status -sb | Select-Object -First 1)
        git remote -v
        git tag --list "v0.1.0-rc*"
    }

    Invoke-Checked "development ruff" {
        Invoke-Native ".\.venv\Scripts\ruff.exe" @("check", "app", "tests")
    }

    Invoke-Checked "development pytest" {
        Invoke-Native ".\.venv\Scripts\python.exe" @("-m", "pytest", "-q")
        $Summary.pytest_result = "pass"
        $Summary.korean_artifact_result = "pass"
    }

    Invoke-Checked "development real ops readiness" {
        Invoke-Native ".\scripts\check_real_ops_readiness.ps1"
    }

    Invoke-Checked "development no-confirm controlled validation" {
        Invoke-Native ".\scripts\validate_real_ops_controlled.ps1"
    }

    Invoke-Checked "development validate_local" {
        Invoke-Native ".\scripts\validate_local.ps1"
        $Summary.validate_local_result = "pass"
        $Summary.no_secret_result = "pass"
    }

    Invoke-Checked "commit safe changes if needed" {
        $Porcelain = @(git status --porcelain)
        if ($Porcelain.Count -gt 0) {
            git add README.md docs app scripts tests
            if ($LASTEXITCODE -ne 0) {
                throw "git add failed."
            }
            git commit -m "YOnLab G2B Agent v2 Task 32H: add release closeout harness"
            if ($LASTEXITCODE -ne 0) {
                throw "git commit failed."
            }
        }
        $Summary.commit_hash = (git rev-parse --short HEAD)
    }

    Invoke-Checked "development deploy readiness" {
        $DeployReadinessText = & ".\scripts\check_deploy_readiness.ps1"
        $DeployReadiness = $DeployReadinessText | ConvertFrom-Json
        $Summary.deploy_ready = [bool] $DeployReadiness.deploy_ready
        if (-not $DeployReadiness.deploy_ready) {
            throw "Development deploy readiness failed."
        }
    }

    if (-not $SkipPush) {
        Invoke-Checked "push main" {
            git push origin main
            if ($LASTEXITCODE -ne 0) {
                throw "git push origin main failed."
            }
            $Summary.main_push_result = "success"
        }
    } else {
        $Summary.main_push_result = "skipped"
    }

    Invoke-Checked "create release tag" {
        $ExistingTag = git tag --list $ReleaseTag
        if ($ExistingTag) {
            $TagCommit = git rev-list -n 1 $ReleaseTag
            $HeadCommit = git rev-parse HEAD
            if ($TagCommit -ne $HeadCommit) {
                throw "$ReleaseTag already exists on a different commit."
            }
        } else {
            git tag -a $ReleaseTag -m "YOnLab G2B Agent v2 MVP release candidate 3"
            if ($LASTEXITCODE -ne 0) {
                throw "git tag failed."
            }
        }
    }

    if (-not $SkipPush) {
        Invoke-Checked "push release tag" {
            git push origin $ReleaseTag
            if ($LASTEXITCODE -ne 0) {
                throw "git push origin $ReleaseTag failed."
            }
            $Summary.tag_push_result = "success"
        }
    } else {
        $Summary.tag_push_result = "skipped"
    }

    Invoke-Checked "fresh deployment clone" {
        New-Item -ItemType Directory -Force $DeployRoot | Out-Null
        $DeployPath = Join-Path $DeployRoot $DeployFolderName
        if (Test-Path -LiteralPath $DeployPath) {
            $DeployPath = Join-Path $DeployRoot "$DeployFolderName-$(Get-Date -Format yyyyMMddHHmmss)"
        }
        $Summary.fresh_deployment_path = $DeployPath
        $RemoteUrl = (git remote get-url origin)
        git clone $RemoteUrl $DeployPath
        if ($LASTEXITCODE -ne 0) {
            throw "git clone failed."
        }
        Push-Location $DeployPath
        try {
            git checkout $ReleaseTag
            if ($LASTEXITCODE -ne 0) {
                throw "git checkout $ReleaseTag failed."
            }
        } finally {
            Pop-Location
        }
    }

    Invoke-Checked "fresh deployment venv and dependencies" {
        Push-Location $Summary.fresh_deployment_path
        try {
            python -m venv .venv
            if ($LASTEXITCODE -ne 0) {
                throw "python -m venv failed."
            }
            .\.venv\Scripts\python.exe -m pip install --upgrade pip
            if ($LASTEXITCODE -ne 0) {
                throw "pip upgrade failed."
            }
            .\.venv\Scripts\python.exe -m pip install -r requirements.txt
            if ($LASTEXITCODE -ne 0) {
                throw "pip install failed."
            }
        } finally {
            Pop-Location
        }
    }

    Invoke-Checked "fresh deployment ruff and pytest" {
        Invoke-Native ".\.venv\Scripts\ruff.exe" @("check", "app", "tests") $Summary.fresh_deployment_path
        Invoke-Native ".\.venv\Scripts\python.exe" @("-m", "pytest", "-q") $Summary.fresh_deployment_path
    }

    Invoke-Checked "fresh deployment readiness" {
        $Readiness = Get-ReadinessPayload -Root $Summary.fresh_deployment_path
        $Summary.project_path_ok = [bool] $Readiness.project_path_ok
        $Summary.env_file_present = [bool] $Readiness.env_file_present
        $Summary.ready_for_controlled_real_call = [bool] $Readiness.ready_for_controlled_real_call
        if (-not $Readiness.project_path_ok) {
            throw "Fresh deployment project_path_ok was false."
        }
        Invoke-Native ".\scripts\validate_real_ops_controlled.ps1" @() $Summary.fresh_deployment_path
        $DeployReadinessText = & (Join-Path $Summary.fresh_deployment_path "scripts\check_deploy_readiness.ps1")
        $FreshDeployReadiness = $DeployReadinessText | ConvertFrom-Json
        $Summary.deploy_ready = [bool] $FreshDeployReadiness.deploy_ready
        if (-not $FreshDeployReadiness.deploy_ready) {
            throw "Fresh deploy readiness failed."
        }
    }

    Invoke-Checked "fresh deployment validate_local" {
        Invoke-Native ".\scripts\validate_local.ps1" @() $Summary.fresh_deployment_path
    }

    Invoke-Checked "fresh deployment UI/API smoke" {
        $UiSmoke = Invoke-UiApiSmoke -Root $Summary.fresh_deployment_path -Port 8010
        $Summary.ui_api_smoke_result = "pass:$($UiSmoke.port)"
    }

    if ($RunControlledRealCall -and $ConfirmRealApiCall) {
        Invoke-Checked "optional controlled real call" {
            $Readiness = Get-ReadinessPayload -Root $Summary.fresh_deployment_path
            if ($Readiness.ready_for_controlled_real_call -ne $true) {
                $Summary.remaining_blocking_issues += "controlled real call skipped: readiness false"
            } else {
                Push-Location $Summary.fresh_deployment_path
                try {
                    $env:YONLAB_AUTO_RUN_REAL_API = "true"
                    .\scripts\validate_real_ops_controlled.ps1 -ConfirmRealApiCall
                    if ($LASTEXITCODE -ne 0) {
                        throw "controlled real validation failed."
                    }
                    $Summary.controlled_real_run_executed = $true
                    $Summary.additional_real_api_call_count = 1
                } finally {
                    Remove-Item Env:\YONLAB_AUTO_RUN_REAL_API -ErrorAction SilentlyContinue
                    Pop-Location
                }
            }
        }
    } elseif ($RunControlledRealCall -or $ConfirmRealApiCall) {
        $Summary.remaining_blocking_issues += (
            "controlled real call skipped: both -RunControlledRealCall and " +
            "-ConfirmRealApiCall are required"
        )
    }

    if ($Summary.controlled_real_run_executed) {
        $Summary.deployment_status = "ready"
    } elseif (-not $Summary.env_file_present -or -not $Summary.ready_for_controlled_real_call) {
        $Summary.deployment_status = "ready_after_env_fix"
    } else {
        $Summary.deployment_status = "ready_after_env_fix"
    }
} catch {
    $Summary.deployment_status = "blocked"
    $Summary.remaining_blocking_issues += $_.Exception.Message
    throw
} finally {
    Remove-Item Env:\YONLAB_AUTO_RUN_REAL_API -ErrorAction SilentlyContinue
    Write-Step "release closeout summary"
    $Summary | ConvertTo-Json -Depth 20
}
