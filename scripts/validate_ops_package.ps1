$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$Utf8 = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $Utf8
$OutputEncoding = $Utf8
try { chcp.com 65001 | Out-Null } catch {}

Write-Host "Validating YOnLab G2B Agent v2 Local Operations v1.0 package."
& (Join-Path $ProjectRoot "scripts\validate_local.ps1")
Write-Host "Local operations v1.0 package validation completed."
