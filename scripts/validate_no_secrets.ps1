$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$Utf8 = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $Utf8
$OutputEncoding = $Utf8
try { chcp.com 65001 | Out-Null } catch {}

$EnvExample = Get-Content -LiteralPath (Join-Path $ProjectRoot ".env.example") -Raw -Encoding utf8
if ($EnvExample -notmatch "(?m)^G2B_API_SERVICE_KEY=$") {
    throw ".env.example must keep G2B_API_SERVICE_KEY empty."
}

if ($EnvExample -match "SECRET-KEY|EncodingKey|DecodingKey") {
    throw ".env.example contains a secret-like value."
}

$TemplateScripts = @(
    "scripts\smoke_g2b_real_confirmed_template.ps1",
    "scripts\smoke_g2b_real_recommend_template.ps1"
)
foreach ($ScriptName in $TemplateScripts) {
    $Content = Get-Content -LiteralPath (Join-Path $ProjectRoot $ScriptName) -Raw -Encoding utf8
    if ($Content -match "SECRET-KEY|EncodingKey|DecodingKey") {
        throw "$ScriptName contains a secret-like value."
    }
    if ($Content -notmatch "G2B_API_SERVICE_KEY=<your local key>") {
        throw "$ScriptName must keep the service key as a placeholder only."
    }
}

git check-ignore -q ".env"
if ($LASTEXITCODE -ne 0) {
    throw ".env must remain ignored by Git."
}

git check-ignore -q "data/captured/g2b/sample.json"
if ($LASTEXITCODE -ne 0) {
    throw "data/captured/ must remain ignored by Git."
}

Write-Host "No-secret validation completed successfully."
