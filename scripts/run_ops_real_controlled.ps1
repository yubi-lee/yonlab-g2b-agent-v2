param(
    [switch] $ConfirmRealApiCall,
    [string] $Keyword = "AI",
    [string] $StartDate = "2026-06-01",
    [string] $EndDate = "2026-06-20",
    [int] $NumRows = 3,
    [switch] $IncludeDocumentAnalysis
)

$ErrorActionPreference = "Stop"

$Utf8 = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $Utf8
$OutputEncoding = $Utf8
try { chcp.com 65001 | Out-Null } catch {}

Write-Host "Controlled real operations runner."
Write-Host "Real mode uses live G2B API quota. Use only when necessary."

if (-not $ConfirmRealApiCall) {
    Write-Host "Blocked: pass -ConfirmRealApiCall to run a controlled real operation."
    exit 0
}

$BaseUrl = $env:YONLAB_G2B_BASE_URL
if ([string]::IsNullOrWhiteSpace($BaseUrl)) {
    $BaseUrl = "http://127.0.0.1:8000"
}

try {
    $HealthResponse = Invoke-WebRequest `
        -Method Get `
        -Uri "$BaseUrl/health" `
        -UseBasicParsing
    if ($HealthResponse.StatusCode -ne 200) {
        Write-Host "Blocked: FastAPI server health check did not return 200."
        exit 0
    }
} catch {
    Write-Host "Blocked: FastAPI server is not reachable at $BaseUrl/health."
    Write-Host "Start it with scripts/start_local_ops.ps1 or scripts/dev_start.ps1 first."
    exit 0
}

$BodyJson = @{
    mode = "real"
    keyword = $Keyword
    start_date = $StartDate
    end_date = $EndDate
    page_no = 1
    num_rows = $NumRows
    include_reports = $true
    include_document_analysis = [bool] $IncludeDocumentAnalysis
    confirm_real_api_call = $true
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
