$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$Utf8 = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $Utf8
$OutputEncoding = $Utf8
try { chcp.com 65001 | Out-Null } catch {}

$EnvPath = Join-Path $ProjectRoot ".env"
$ExamplePath = Join-Path $ProjectRoot ".env.example"

if (Test-Path -LiteralPath $EnvPath) {
    Write-Host ".env already exists. It was not overwritten."
} else {
    Copy-Item -LiteralPath $ExamplePath -Destination $EnvPath
    Write-Host ".env was created from .env.example."
}

Write-Host "Edit .env locally before a confirmed real smoke."
Write-Host "Set G2B_ENABLE_REAL_API=true only when ready."
Write-Host "Set G2B_API_SERVICE_KEY manually in .env only."
Write-Host "Use G2B_LIST_ENDPOINT_PATH=/1230000/ad/BidPublicInfoService/getBidPblancListInfoServcPPSSrch for the first service search smoke."
