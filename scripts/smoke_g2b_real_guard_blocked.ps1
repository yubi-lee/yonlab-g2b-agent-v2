$ErrorActionPreference = "Stop"

$Utf8 = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $Utf8
$OutputEncoding = $Utf8
try { chcp.com 65001 | Out-Null } catch {}

$BaseUrl = $env:YONLAB_G2B_BASE_URL
if ([string]::IsNullOrWhiteSpace($BaseUrl)) {
    $BaseUrl = "http://127.0.0.1:8000"
}

$BodyJson = @{
    mode = "real"
    keyword = "AI"
    page_no = 1
    num_rows = 3
    confirm_real_api_call = $false
} | ConvertTo-Json -Depth 5

$Bytes = [System.Text.Encoding]::UTF8.GetBytes($BodyJson)

$Response = Invoke-WebRequest `
    -Method Post `
    -Uri "$BaseUrl/g2b/search" `
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

$Object = $Text | ConvertFrom-Json
$AllowedErrors = @(
    "real_api_disabled",
    "service_key_missing",
    "endpoint_path_missing",
    "real_api_confirmation_required"
)
if ($Object.ok -ne $false -or $AllowedErrors -notcontains $Object.error_code) {
    throw "Expected guarded real API block, got: $Text"
}

$Object | ConvertTo-Json -Depth 30
