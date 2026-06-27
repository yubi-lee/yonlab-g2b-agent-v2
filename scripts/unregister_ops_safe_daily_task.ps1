[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string] $TaskName = "YOnLabG2BAgentV2SafeDaily"
)

$ErrorActionPreference = "Stop"

$Utf8 = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $Utf8
$OutputEncoding = $Utf8
try { chcp.com 65001 | Out-Null } catch {}

$Task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $Task) {
    Write-Host "Scheduled task not found: $TaskName"
    exit 0
}

if ($PSCmdlet.ShouldProcess($TaskName, "Unregister safe daily scheduled task")) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Unregistered safe daily scheduled task: $TaskName"
}