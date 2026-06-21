$ErrorActionPreference = "Stop"

$Utf8 = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $Utf8
$OutputEncoding = $Utf8
try { chcp.com 65001 | Out-Null } catch {}

$BaseUrl = $env:YONLAB_G2B_BASE_URL
if ([string]::IsNullOrWhiteSpace($BaseUrl)) {
    $BaseUrl = "http://127.0.0.1:8000"
}

$Response = Invoke-WebRequest `
    -Method Get `
    -Uri "$BaseUrl/ops/package-info" `
    -UseBasicParsing

if ($Response.RawContentStream) {
    $Response.RawContentStream.Position = 0
    $Reader = New-Object System.IO.StreamReader -ArgumentList $Response.RawContentStream, ([System.Text.Encoding]::UTF8)
    $Text = $Reader.ReadToEnd()
} else {
    $Text = $Response.Content
}

$Payload = $Text | ConvertFrom-Json
if ($Payload.package_version -ne "1.0") {
    throw "Expected local operations package version 1.0."
}
if ($Payload.service_key_exposed -ne $false) {
    throw "Package info must not expose service keys."
}
$ServiceKeyQueryPattern = "service" + "Key="
if ($Text -match "SECRET-KEY" -or $Text -match $ServiceKeyQueryPattern) {
    throw "Package info response contains secret-looking content."
}

$Payload | ConvertTo-Json -Depth 20
