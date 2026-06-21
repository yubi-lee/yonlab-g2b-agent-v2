$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
# Safety: this removes only generated local operation data. It does not touch .env or source fixtures.
$GeneratedPaths = @(
    (Join-Path $ProjectRoot "data\ops"),
    (Join-Path $ProjectRoot "data\reports"),
    (Join-Path $ProjectRoot "data\downloaded"),
    (Join-Path $ProjectRoot "data\extracted")
)

foreach ($Path in $GeneratedPaths) {
    if (Test-Path -LiteralPath $Path) {
        Remove-Item -LiteralPath $Path -Recurse -Force
    }
}

Write-Host "Deleted generated local operation data under data\ops, data\reports, data\downloaded, and data\extracted."
Write-Host ".env and source fixtures were not touched."
