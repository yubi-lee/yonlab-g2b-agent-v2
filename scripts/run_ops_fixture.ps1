$ErrorActionPreference = "Stop"

$Utf8 = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $Utf8
$OutputEncoding = $Utf8
try { chcp.com 65001 | Out-Null } catch {}

$BaseUrl = $env:YONLAB_G2B_BASE_URL
if ([string]::IsNullOrWhiteSpace($BaseUrl)) {
    $BaseUrl = "http://127.0.0.1:8000"
}

$Keyword = $env:YONLAB_DEFAULT_KEYWORD
if ([string]::IsNullOrWhiteSpace($Keyword)) {
    $Keyword = "AI"
}

$NumRows = 10
if (-not [string]::IsNullOrWhiteSpace($env:YONLAB_DEFAULT_NUM_ROWS)) {
    $NumRows = [int] $env:YONLAB_DEFAULT_NUM_ROWS
}

$BodyJson = @{
    mode = "fixture"
    keyword = $Keyword
    num_rows = $NumRows
    include_reports = $true
    confirm_real_api_call = $false
} | ConvertTo-Json -Depth 5

$Bytes = [System.Text.Encoding]::UTF8.GetBytes($BodyJson)

$Response = Invoke-WebRequest `
    -Method Post `
    -Uri "$BaseUrl/ops/run-recommendations" `
    -ContentType "application/json; charset=utf-8" `
    -UseBasicParsing `
    -Body $Bytes

if ($Response.RawContentStream) {
    $Response.RawContentStream.Position = 0
    $Reader = New-Object System.IO.StreamReader -ArgumentList $Response.RawContentStream, ([System.Text.Encoding]::UTF8)
    $Text = $Reader.ReadToEnd()
} else {
    $Text = $Response.Content
}

$Text | ConvertFrom-Json | ConvertTo-Json -Depth 30
