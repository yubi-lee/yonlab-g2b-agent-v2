$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$Utf8 = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $Utf8
$OutputEncoding = $Utf8
try { chcp.com 65001 | Out-Null } catch {}

function Test-SettingPresent {
    param([Parameter(Mandatory = $true)][string] $Name)

    $Value = [Environment]::GetEnvironmentVariable($Name, "Process")
    if (-not [string]::IsNullOrWhiteSpace($Value)) {
        return $true
    }

    $EnvPath = Join-Path $ProjectRoot ".env"
    if (-not (Test-Path -LiteralPath $EnvPath)) {
        return $false
    }

    foreach ($Line in Get-Content -LiteralPath $EnvPath -Encoding utf8) {
        $Trimmed = $Line.Trim()
        if ($Trimmed.StartsWith("#") -or -not $Trimmed.Contains("=")) {
            continue
        }
        $Parts = $Trimmed.Split("=", 2)
        if ($Parts[0].Trim() -eq $Name -and -not [string]::IsNullOrWhiteSpace($Parts[1])) {
            return $true
        }
    }
    return $false
}

function Test-SettingTrue {
    param([Parameter(Mandatory = $true)][string] $Name)

    $Value = [Environment]::GetEnvironmentVariable($Name, "Process")
    if ([string]::IsNullOrWhiteSpace($Value)) {
        $EnvPath = Join-Path $ProjectRoot ".env"
        if (Test-Path -LiteralPath $EnvPath) {
            foreach ($Line in Get-Content -LiteralPath $EnvPath -Encoding utf8) {
                $Trimmed = $Line.Trim()
                if ($Trimmed.StartsWith("#") -or -not $Trimmed.Contains("=")) {
                    continue
                }
                $Parts = $Trimmed.Split("=", 2)
                if ($Parts[0].Trim() -eq $Name) {
                    $Value = $Parts[1]
                    break
                }
            }
        }
    }
    return (-not [string]::IsNullOrWhiteSpace($Value)) -and ($Value.Trim().ToLowerInvariant() -eq "true")
}

$GitAvailable = $null -ne (Get-Command git -ErrorAction SilentlyContinue)
$WorkingTreeStatus = @()
if ($GitAvailable) {
    $WorkingTreeStatus = @(git status --porcelain)
}

$RequiredDocs = @(
    "README.md",
    "docs\06_OPERATIONS_RUNBOOK.md",
    "docs\07_DEPLOYMENT_HANDOFF.md",
    "docs\99_DECISION_LOG.md"
)
$RequiredScripts = @(
    "scripts\validate_local.ps1",
    "scripts\check_no_secrets.ps1",
    "scripts\check_real_ops_readiness.ps1",
    "scripts\validate_real_ops_controlled.ps1"
)

$DocsPresent = @{}
foreach ($Path in $RequiredDocs) {
    $DocsPresent[$Path] = Test-Path -LiteralPath (Join-Path $ProjectRoot $Path)
}

$ScriptsPresent = @{}
foreach ($Path in $RequiredScripts) {
    $ScriptsPresent[$Path] = Test-Path -LiteralPath (Join-Path $ProjectRoot $Path)
}

$BlockingReasons = @()
if (-not $GitAvailable) {
    $BlockingReasons += "git is not available."
}
if ($WorkingTreeStatus.Count -gt 0) {
    $BlockingReasons += "working tree has uncommitted changes."
}
foreach ($Entry in $DocsPresent.GetEnumerator()) {
    if (-not $Entry.Value) {
        $BlockingReasons += "missing required doc: $($Entry.Key)"
    }
}
foreach ($Entry in $ScriptsPresent.GetEnumerator()) {
    if (-not $Entry.Value) {
        $BlockingReasons += "missing required script: $($Entry.Key)"
    }
}

@{
    project_path = $ProjectRoot
    project_path_ok = ((Split-Path -Leaf $ProjectRoot) -eq "yonlab-g2b-agent-v2")
    git_available = $GitAvailable
    working_tree_clean = ($WorkingTreeStatus.Count -eq 0)
    working_tree_status = @($WorkingTreeStatus | Select-Object -First 20)
    required_scripts_present = -not ($ScriptsPresent.Values -contains $false)
    required_docs_present = -not ($DocsPresent.Values -contains $false)
    readiness_script_present = $ScriptsPresent["scripts\check_real_ops_readiness.ps1"]
    local_validation_script_present = $ScriptsPresent["scripts\validate_local.ps1"]
    no_secret_validation_available = $ScriptsPresent["scripts\check_no_secrets.ps1"]
    real_ops_readiness_script_present = $ScriptsPresent["scripts\check_real_ops_readiness.ps1"]
    real_api_settings_presence_as_boolean_only = @{
        g2b_enable_real_api_true = Test-SettingTrue -Name "G2B_ENABLE_REAL_API"
        g2b_api_base_url_configured = Test-SettingPresent -Name "G2B_API_BASE_URL"
        g2b_api_service_key_present = Test-SettingPresent -Name "G2B_API_SERVICE_KEY"
        g2b_endpoint_configured = ((Test-SettingPresent -Name "G2B_LIST_ENDPOINT_PATH") -or (Test-SettingPresent -Name "G2B_ENDPOINT_PRESET"))
        yonlab_auto_run_real_api_true = Test-SettingTrue -Name "YONLAB_AUTO_RUN_REAL_API"
    }
    deploy_ready = ($BlockingReasons.Count -eq 0)
    blocking_reasons = $BlockingReasons
    real_network_call_attempted = $false
    service_key_exposed = $false
} | ConvertTo-Json -Depth 20
