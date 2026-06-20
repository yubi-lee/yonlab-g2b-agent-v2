$ErrorActionPreference = "Stop"

$BaseUrl = $env:YONLAB_G2B_BASE_URL
if ([string]::IsNullOrWhiteSpace($BaseUrl)) {
    $BaseUrl = "http://127.0.0.1:8000"
}

$Response = Invoke-RestMethod `
    -Method Get `
    -Uri "$BaseUrl/g2b/config"

$Response | ConvertTo-Json -Depth 12
