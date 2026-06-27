param(
    [string] $ReleaseTag = "v0.1.0-rc5",
    [string] $DeployRoot = "D:\Deploy",
    [string] $DeployFolderName = "",
    [switch] $RunControlledRealCall,
    [switch] $ConfirmRealApiCall,
    [switch] $RunSyntheticPersistenceCheck,
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
    base_real_config_ready = $false
    ready_for_controlled_real_call = $false
    runtime_gate_persistently_enabled = $false
    storage_path_consistent = $false
    report_path_consistent = $false
    path_blocking_reasons = @()
    deploy_ready = $false
    pytest_result = "not_run"
    validate_local_result = "not_run"
    no_secret_result = "not_run"
    korean_artifact_result = "not_run"
    ui_api_smoke_result = "not_run"
    controlled_real_run_executed = $false
    execution_count = 0
    real_call_executed = $false
    run_id = $null
    real_operation_status = $null
    real_operation_error_code = $null
    real_report_metadata_count = 0
    summary_status = $null
    yonlab_auto_run_real_api_cleanup_ok = $false
    additional_real_api_call_count = 0
    synthetic_persistence_check_executed = $false
    synthetic_persistence_run_id = $null
    synthetic_report_index_consistent = $false
    synthetic_quality_summary_consistent = $false
    synthetic_real_api_call_count = 0
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
    param(
        [string] $Root,
        [bool] $ConfirmIntent = $false
    )

    $Python = Get-PythonPath -Root $Root
    Push-Location $Root
    try {
        $Arguments = @("-m", "app.services.real_ops_runtime_readiness")
        if ($ConfirmIntent) {
            $Arguments += "--confirm-controlled-real-call-intent"
        }
        $Text = & $Python @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "real ops readiness exited with code $LASTEXITCODE."
        }
        return ($Text | ConvertFrom-Json)
    } finally {
        Pop-Location
    }
}

function Set-DeploymentRuntimeEnvironment {
    param(
        [string] $Root,
        [int] $Port = 8010
    )

    $env:YONLAB_STORAGE_DB_PATH = Join-Path $Root "data\ops\yonlab_g2b_agent.sqlite3"
    $env:YONLAB_REPORT_DIR = Join-Path $Root "data\reports\g2b"
    $env:YONLAB_G2B_BASE_URL = "http://127.0.0.1:$Port"
    Remove-Item Env:\YONLAB_AUTO_RUN_REAL_API -ErrorAction SilentlyContinue
}

function Clear-DeploymentRuntimeEnvironment {
    Remove-Item Env:\YONLAB_STORAGE_DB_PATH -ErrorAction SilentlyContinue
    Remove-Item Env:\YONLAB_REPORT_DIR -ErrorAction SilentlyContinue
    Remove-Item Env:\YONLAB_G2B_BASE_URL -ErrorAction SilentlyContinue
    Remove-Item Env:\YONLAB_AUTO_RUN_REAL_API -ErrorAction SilentlyContinue
}

function Get-PathConsistencyPayload {
    param([string] $Root)

    $Python = Get-PythonPath -Root $Root
    Push-Location $Root
    try {
        $Text = & $Python -m app.services.runtime_path_consistency --project-root $Root
        if ($LASTEXITCODE -ne 0) {
            throw "runtime path consistency exited with code $LASTEXITCODE."
        }
        return ($Text | ConvertFrom-Json)
    } finally {
        Pop-Location
    }
}

function Update-PathConsistencySummary {
    param([object] $PathConsistency)

    $Summary.storage_path_consistent = [bool] $PathConsistency.storage_path_consistent
    $Summary.report_path_consistent = [bool] $PathConsistency.report_path_consistent
    $Summary.path_blocking_reasons = @($PathConsistency.path_blocking_reasons)
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
    $StoragePath = Join-Path $Root "data\ops\yonlab_g2b_agent.sqlite3"
    $ReportDir = Join-Path $Root "data\reports\g2b"
    $Job = Start-Job -ScriptBlock {
        param($JobRoot, $JobPython, $JobPort, $JobStoragePath, $JobReportDir)
        Set-Location $JobRoot
        $env:YONLAB_STORAGE_DB_PATH = $JobStoragePath
        $env:YONLAB_REPORT_DIR = $JobReportDir
        Remove-Item Env:\YONLAB_AUTO_RUN_REAL_API -ErrorAction SilentlyContinue
        & $JobPython -m uvicorn app.main:app --host 127.0.0.1 --port $JobPort
    } -ArgumentList $Root, $Python, $Port, $StoragePath, $ReportDir

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
            latest_run_id = $Quality.latest_run_id
            real_mode_executed = [bool] $Quality.real_mode_executed
            real_report_count = [int] $Quality.real_report_count
            report_count = [int] $ReportIndex.report_count
        }
    } finally {
        Stop-Job $Job -ErrorAction SilentlyContinue
        Remove-Job $Job -Force -ErrorAction SilentlyContinue
    }
}

function Invoke-SyntheticPersistenceCheck {
    param(
        [string] $Root,
        [int] $Port = 8012
    )

    $Python = Get-PythonPath -Root $Root
    $StoragePath = Join-Path $Root "data\ops\yonlab_g2b_agent.sqlite3"
    $ReportDir = Join-Path $Root "data\reports\g2b"
    $Job = Start-Job -ScriptBlock {
        param($JobRoot, $JobPython, $JobPort, $JobStoragePath, $JobReportDir)
        Set-Location $JobRoot
        $env:YONLAB_STORAGE_DB_PATH = $JobStoragePath
        $env:YONLAB_REPORT_DIR = $JobReportDir
        Remove-Item Env:\YONLAB_AUTO_RUN_REAL_API -ErrorAction SilentlyContinue
        & $JobPython -m uvicorn app.main:app --host 127.0.0.1 --port $JobPort
    } -ArgumentList $Root, $Python, $Port, $StoragePath, $ReportDir

    $BaseUrl = "http://127.0.0.1:$Port"
    try {
        Wait-ForEndpoint -Url "$BaseUrl/health"
        $Body = @{
            mode = "fixture"
            keyword = "AI"
            num_rows = 1
            include_reports = $true
            confirm_real_api_call = $false
        } | ConvertTo-Json -Depth 5
        $Bytes = [System.Text.Encoding]::UTF8.GetBytes($Body)
        $Run = Invoke-RestMethod "$BaseUrl/ops/run-recommendations" `
            -Method Post `
            -ContentType "application/json; charset=utf-8" `
            -Body $Bytes
        $Quality = Invoke-RestMethod "$BaseUrl/ops/quality-summary"
        $ReportIndex = Invoke-RestMethod "$BaseUrl/ops/report-index"
        if ($Run.mode -ne "fixture") {
            throw "Synthetic persistence check must use fixture mode."
        }
        if ($Quality.service_key_exposed -ne $false -or $ReportIndex.service_key_exposed -ne $false) {
            throw "Synthetic persistence check exposed service key flag."
        }
        return @{
            run_id = $Run.run_id
            quality_summary_consistent = ($Quality.latest_run_id -eq $Run.run_id)
            report_index_consistent = ($ReportIndex.latest_run_id -eq $Run.run_id)
            report_count = [int] $ReportIndex.report_count
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
            git tag -a $ReleaseTag -m "YOnLab G2B Agent v2 MVP release candidate $($ReleaseTag.Replace('v0.1.0-rc', ''))"
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
            if (-not (Test-Path -LiteralPath (Join-Path $DeployPath ".git"))) {
                throw "Deployment path already exists but is not a git repository: $DeployPath"
            }
            $Summary.fresh_deployment_path = $DeployPath
            Push-Location $DeployPath
            try {
                git fetch --tags origin
                if ($LASTEXITCODE -ne 0) {
                    throw "git fetch failed."
                }
                git checkout -f $ReleaseTag
                if ($LASTEXITCODE -ne 0) {
                    throw "git checkout $ReleaseTag failed."
                }
            } finally {
                Pop-Location
            }
        } else {
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
        Set-DeploymentRuntimeEnvironment -Root $Summary.fresh_deployment_path -Port 8011
        $PathConsistency = Get-PathConsistencyPayload -Root $Summary.fresh_deployment_path
        Update-PathConsistencySummary -PathConsistency $PathConsistency
        if (-not $Summary.storage_path_consistent -or -not $Summary.report_path_consistent) {
            throw "Fresh deployment runtime path consistency failed."
        }
        $Readiness = Get-ReadinessPayload -Root $Summary.fresh_deployment_path
        $Summary.project_path_ok = [bool] $Readiness.project_path_ok
        $Summary.env_file_present = [bool] $Readiness.env_file_present
        $Summary.base_real_config_ready = [bool] $Readiness.base_real_config_ready
        $Summary.ready_for_controlled_real_call = [bool] $Readiness.ready_for_controlled_real_call
        $Summary.runtime_gate_persistently_enabled = [bool] $Readiness.ops_runtime_gate_configured
        if (-not $Readiness.project_path_ok) {
            throw "Fresh deployment project_path_ok was false."
        }
        $env:YONLAB_G2B_BASE_URL = "http://127.0.0.1:8011"
        Invoke-Native ".\scripts\validate_real_ops_controlled.ps1" @() $Summary.fresh_deployment_path
        $DeployReadinessText = & (Join-Path $Summary.fresh_deployment_path "scripts\check_deploy_readiness.ps1")
        $FreshDeployReadiness = $DeployReadinessText | ConvertFrom-Json
        $Summary.deploy_ready = [bool] $FreshDeployReadiness.deploy_ready
        if (-not $FreshDeployReadiness.deploy_ready) {
            throw "Fresh deploy readiness failed."
        }
    }

    Invoke-Checked "fresh deployment validate_local" {
        Remove-Item Env:\YONLAB_G2B_BASE_URL -ErrorAction SilentlyContinue
        Remove-Item Env:\YONLAB_AUTO_RUN_REAL_API -ErrorAction SilentlyContinue
        Invoke-Native ".\scripts\validate_local.ps1" @() $Summary.fresh_deployment_path
        Set-DeploymentRuntimeEnvironment -Root $Summary.fresh_deployment_path -Port 8011
    }

    Invoke-Checked "fresh deployment UI/API smoke" {
        $UiSmoke = Invoke-UiApiSmoke -Root $Summary.fresh_deployment_path -Port 8010
        $Summary.ui_api_smoke_result = "pass:$($UiSmoke.port)"
    }

    if ($RunSyntheticPersistenceCheck) {
        Invoke-Checked "synthetic persistence consistency" {
            Set-DeploymentRuntimeEnvironment -Root $Summary.fresh_deployment_path -Port 8012
            $Synthetic = Invoke-SyntheticPersistenceCheck -Root $Summary.fresh_deployment_path -Port 8012
            $Summary.synthetic_persistence_check_executed = $true
            $Summary.synthetic_persistence_run_id = $Synthetic.run_id
            $Summary.synthetic_report_index_consistent = [bool] $Synthetic.report_index_consistent
            $Summary.synthetic_quality_summary_consistent = [bool] $Synthetic.quality_summary_consistent
            $Summary.synthetic_real_api_call_count = 0
            if (-not $Summary.synthetic_report_index_consistent -or -not $Summary.synthetic_quality_summary_consistent) {
                throw "Synthetic persistence consistency failed."
            }
        }
    }

    if ($RunControlledRealCall -and $ConfirmRealApiCall) {
        Invoke-Checked "optional controlled real call" {
            Set-DeploymentRuntimeEnvironment -Root $Summary.fresh_deployment_path -Port 8011
            $BaseReadiness = Get-ReadinessPayload -Root $Summary.fresh_deployment_path
            $Summary.base_real_config_ready = [bool] $BaseReadiness.base_real_config_ready
            if ($BaseReadiness.base_real_config_ready -ne $true) {
                $Summary.remaining_blocking_issues += "controlled real call skipped: base real config readiness false"
            } else {
                Push-Location $Summary.fresh_deployment_path
                try {
                    $env:YONLAB_AUTO_RUN_REAL_API = "true"
                    $env:YONLAB_G2B_BASE_URL = "http://127.0.0.1:8011"
                    $ReadyReadiness = Get-ReadinessPayload -Root $Summary.fresh_deployment_path -ConfirmIntent $true
                    $Summary.ready_for_controlled_real_call = [bool] $ReadyReadiness.ready_for_controlled_real_call
                    if ($ReadyReadiness.ready_for_controlled_real_call -ne $true) {
                        $Summary.remaining_blocking_issues += "controlled real call skipped: controlled execution readiness false"
                        return
                    }
                    .\scripts\validate_real_ops_controlled.ps1 -ConfirmRealApiCall
                    if ($LASTEXITCODE -ne 0) {
                        throw "controlled real validation failed."
                    }
                    $Summary.controlled_real_run_executed = $true
                    $Summary.execution_count = 1
                    $Summary.additional_real_api_call_count = 1
                } finally {
                    Remove-Item Env:\YONLAB_AUTO_RUN_REAL_API -ErrorAction SilentlyContinue
                    $Summary.yonlab_auto_run_real_api_cleanup_ok = [string]::IsNullOrWhiteSpace(
                        [Environment]::GetEnvironmentVariable("YONLAB_AUTO_RUN_REAL_API", "Process")
                    )
                    Pop-Location
                }
                $PostRunSmoke = Invoke-UiApiSmoke -Root $Summary.fresh_deployment_path -Port 8010
                $Summary.real_call_executed = [bool] $PostRunSmoke.real_mode_executed
                $Summary.run_id = $PostRunSmoke.latest_run_id
                $Summary.real_report_metadata_count = [int] $PostRunSmoke.report_count
                $Summary.summary_status = $PostRunSmoke.quality_summary
                if ($Summary.real_call_executed) {
                    $Summary.real_operation_status = "reflected"
                } else {
                    $Summary.real_operation_status = "not_reflected"
                    $Summary.real_operation_error_code = "real_run_not_reflected"
                }
            }
        }
    } elseif ($RunControlledRealCall -or $ConfirmRealApiCall) {
        $Summary.remaining_blocking_issues += (
            "controlled real call skipped: both -RunControlledRealCall and " +
            "-ConfirmRealApiCall are required"
        )
    }

    if ($Summary.controlled_real_run_executed -and $Summary.real_call_executed) {
        $Summary.deployment_status = "ready"
    } elseif (
        $RunSyntheticPersistenceCheck `
        -and $Summary.synthetic_report_index_consistent `
        -and $Summary.synthetic_quality_summary_consistent `
        -and $Summary.storage_path_consistent `
        -and $Summary.report_path_consistent
    ) {
        $Summary.deployment_status = "ready_for_final_controlled_real_run"
    } elseif (-not $Summary.env_file_present -or -not $Summary.base_real_config_ready) {
        $Summary.deployment_status = "ready_after_env_fix"
    } elseif ($RunControlledRealCall -and $ConfirmRealApiCall -and -not $Summary.real_call_executed) {
        $Summary.deployment_status = "blocked"
    } else {
        $Summary.deployment_status = "ready_after_env_fix"
    }
} catch {
    $Summary.deployment_status = "blocked"
    $Summary.remaining_blocking_issues += $_.Exception.Message
    throw
} finally {
    Clear-DeploymentRuntimeEnvironment
    Write-Step "release closeout summary"
    $Summary | ConvertTo-Json -Depth 20
}
