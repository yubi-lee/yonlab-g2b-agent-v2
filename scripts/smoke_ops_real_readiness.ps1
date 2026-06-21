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
    -Uri "$BaseUrl/ops/real-readiness" `
    -UseBasicParsing

if ($Response.RawContentStream) {
    $Response.RawContentStream.Position = 0
    $Reader = New-Object System.IO.StreamReader -ArgumentList $Response.RawContentStream, ([System.Text.Encoding]::UTF8)
    $Text = $Reader.ReadToEnd()
} else {
    $Text = $Response.Content
}

$Payload = $Text | ConvertFrom-Json
if ($Payload.will_call_real_api -ne $false) {
    throw "Real ops readiness smoke must not call the real API."
}
if ($Payload.db_write_attempted -ne $false) {
    throw "Real ops readiness smoke must not write to the database."
}
if ($Payload.service_key_exposed -ne $false) {
    throw "Real ops readiness smoke must not expose service keys."
}
if ($Text -match "SECRET-KEY") {
    throw "Real ops readiness response contains secret-looking content."
}

$Payload | ConvertTo-Json -Depth 20
