$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ReportRoot = Join-Path $ProjectRoot "data\reports\g2b"

if (-not (Test-Path -LiteralPath $ReportRoot)) {
    Write-Host "No operations report directory exists yet."
    exit 0
}

$Latest = Get-ChildItem -LiteralPath $ReportRoot -Directory |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if ($null -eq $Latest) {
    Write-Host "No operations report run directory exists yet."
    exit 0
}

Write-Host $Latest.FullName
Invoke-Item -LiteralPath $Latest.FullName
