$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$OpsPath = Join-Path $ProjectRoot "data\ops"
$ReportsPath = Join-Path $ProjectRoot "data\reports"

if (Test-Path -LiteralPath $OpsPath) {
    Remove-Item -LiteralPath $OpsPath -Recurse -Force
}
if (Test-Path -LiteralPath $ReportsPath) {
    Remove-Item -LiteralPath $ReportsPath -Recurse -Force
}

Write-Host "Deleted generated local ops data under data\ops and data\reports."
Write-Host ".env and source fixtures were not touched."
