param(
    [int] $Port = 8000,
    [switch] $OpenBrowser
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$Utf8 = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $Utf8
$OutputEncoding = $Utf8
try { chcp.com 65001 | Out-Null } catch {}

$ActivateScript = Join-Path $ProjectRoot ".venv\Scripts\Activate.ps1"
if (Test-Path -LiteralPath $ActivateScript) {
    . $ActivateScript
}

$Url = "http://127.0.0.1:$Port/ui"
Write-Host "Starting YOnLab G2B Agent v2 Local Operations v1.0"
Write-Host "Dashboard: $Url"
Write-Host "Swagger:   http://127.0.0.1:$Port/docs"
Write-Host "Health:    http://127.0.0.1:$Port/health"

if ($OpenBrowser) {
    Start-Process $Url
}

uvicorn app.main:app --host 127.0.0.1 --port $Port
