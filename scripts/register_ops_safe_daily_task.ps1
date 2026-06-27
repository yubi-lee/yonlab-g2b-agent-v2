[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string] $TaskName = "YOnLabG2BAgentV2SafeDaily",
    [string] $Time = "09:00",
    [string] $DeployPath = ""
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
$SafeScriptPath = Join-Path $ResolvedDeployPath "scripts\run_ops_safe_daily.ps1"
$SafeScriptExists = Test-Path -LiteralPath $SafeScriptPath -PathType Leaf
if (-not $SafeScriptExists -and -not $WhatIfPreference) {
    throw "Safe daily script was not found at $SafeScriptPath"
}

$ActionArguments = "-NoProfile -ExecutionPolicy Bypass -File `"$SafeScriptPath`" -DeployPath `"$ResolvedDeployPath`""
$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $ActionArguments
$Trigger = New-ScheduledTaskTrigger -Daily -At $Time
$Description = "YOnLab G2B Agent v2 safe daily check. Does not call the real G2B API."

$Preview = [pscustomobject]@{
    task_name = $TaskName
    schedule = "DAILY $Time"
    target_script = $SafeScriptPath
    target_script_exists = $SafeScriptExists
    real_api_included = $false
    requires_admin_for_registration = $true
}
$Preview | ConvertTo-Json -Depth 5

if ($PSCmdlet.ShouldProcess($TaskName, "Register safe daily scheduled task")) {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $Action `
        -Trigger $Trigger `
        -Description $Description `
        -Force | Out-Null
    Write-Host "Registered safe daily scheduled task: $TaskName"
}