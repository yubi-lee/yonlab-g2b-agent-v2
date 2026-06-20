$ErrorActionPreference = "Stop"

$BaseUrl = $env:YONLAB_G2B_BASE_URL
if ([string]::IsNullOrWhiteSpace($BaseUrl)) {
    $BaseUrl = "http://127.0.0.1:8000"
}

$Body = @{
    include_reports = $false
    limit = 5
} | ConvertTo-Json -Depth 5

$Response = Invoke-RestMethod `
    -Method Post `
    -Uri "$BaseUrl/demo/recommendations" `
    -ContentType "application/json; charset=utf-8" `
    -Body $Body

$Response | ConvertTo-Json -Depth 12
