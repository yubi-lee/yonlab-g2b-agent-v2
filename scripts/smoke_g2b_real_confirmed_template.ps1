$ErrorActionPreference = "Stop"

# WARNING:
# This template can call the real G2B/Public Data Portal API.
# Run it only after configuring .env locally with:
# - G2B_ENABLE_REAL_API=true
# - G2B_API_SERVICE_KEY=<your local key>
# - G2B_LIST_ENDPOINT_PATH=/1230000/ad/BidPublicInfoService
# Never commit .env or paste the service key into this script.

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
    confirm_real_api_call = $true
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

$Text | ConvertFrom-Json | ConvertTo-Json -Depth 30
