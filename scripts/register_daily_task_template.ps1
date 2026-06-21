$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ScriptPath = Join-Path $PSScriptRoot "run_daily_fixture.ps1"

Write-Host "Template only. Review before registering a Windows scheduled task."
Write-Host "Example command:"
Write-Host "schtasks /Create /TN YOnLabG2BDailyFixture /SC DAILY /ST 09:00 /TR `"powershell.exe -NoProfile -ExecutionPolicy Bypass -File '$ScriptPath'`" /F"
Write-Host "Project root: $ProjectRoot"
