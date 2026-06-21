$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$LogDir = Join-Path $ProjectRoot "data\ops\logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogPath = Join-Path $LogDir "daily_fixture_$Timestamp.json"

$Result = & (Join-Path $PSScriptRoot "run_ops_fixture.ps1")
$Result | Out-File -LiteralPath $LogPath -Encoding utf8
$Result

Write-Host "Saved daily fixture operation result to $LogPath"
