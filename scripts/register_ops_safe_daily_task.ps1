[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string] $TaskName = "YOnLabG2BAgentV2SafeDaily",
    [string] $Time = "09:00",
    [string] $DeployPath = "D:\Deploy\yonlab-g2b-agent-v2-rc5.1"
)

$ErrorActionPreference = "Stop"

$Utf8 = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $Utf8
$OutputEncoding = $Utf8
try { chcp.com 65001 | Out-Null } catch {}

$ResolvedDeployPath = (Resolve-Path -LiteralPath $DeployPath).Path
$SafeScriptPath = Join-Path $PSScriptRoot "run_ops_safe_daily.ps1"
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