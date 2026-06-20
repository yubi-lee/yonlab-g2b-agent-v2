$ErrorActionPreference = "Stop"

$BaseUrl = $env:YONLAB_G2B_BASE_URL
if ([string]::IsNullOrWhiteSpace($BaseUrl)) {
    $BaseUrl = "http://127.0.0.1:8000"
}

$Body = @{
    mode = "fixture"
    keyword = "AI"
    page_no = 1
    num_rows = 10
    include_reports = $false
    confirm_real_api_call = $false
} | ConvertTo-Json -Depth 5

$Response = Invoke-RestMethod `
    -Method Post `
    -Uri "$BaseUrl/g2b/recommendations" `
    -ContentType "application/json; charset=utf-8" `
    -Body $Body

$Response | ConvertTo-Json -Depth 12
