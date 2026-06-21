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
    -Uri "$BaseUrl/ui" `
    -UseBasicParsing

if ($Response.RawContentStream) {
    $Response.RawContentStream.Position = 0
    $Reader = New-Object System.IO.StreamReader -ArgumentList $Response.RawContentStream, ([System.Text.Encoding]::UTF8)
    $Text = $Reader.ReadToEnd()
} else {
    $Text = $Response.Content
}

if ($Response.StatusCode -ne 200) {
    throw "Expected /ui to return 200."
}
if ($Text -notmatch "YOnLab G2B Agent") {
    throw "Expected /ui response to contain dashboard title."
}
if ($Text -notmatch "Run recommendation") {
    throw "Expected /ui response to contain Run recommendation."
}

@{
    ok = $true
    endpoint = "/ui"
    contains_title = $true
    contains_run_recommendation = $true
} | ConvertTo-Json -Depth 5
