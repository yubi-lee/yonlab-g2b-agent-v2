$ErrorActionPreference = "Stop"

$Utf8 = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $Utf8
$OutputEncoding = $Utf8
try { chcp.com 65001 | Out-Null } catch {}

$BaseUrl = $env:YONLAB_G2B_BASE_URL
if ([string]::IsNullOrWhiteSpace($BaseUrl)) {
    $BaseUrl = "http://127.0.0.1:8000"
}

function Invoke-JsonRequest {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Method,
        [Parameter(Mandatory = $true)]
        [string] $Uri,
        [object] $Body = $null
    )

    # Invoke-WebRequest receives -UseBasicParsing through this splatted parameter set.
    $Parameters = @{
        Method = $Method
        Uri = $Uri
        UseBasicParsing = $true
    }
    if ($null -ne $Body) {
        $BodyJson = $Body | ConvertTo-Json -Depth 10
        $Parameters["ContentType"] = "application/json; charset=utf-8"
        $Parameters["Body"] = [System.Text.Encoding]::UTF8.GetBytes($BodyJson)
    }

    $Response = Invoke-WebRequest @Parameters
    if ($Response.RawContentStream) {
        $Response.RawContentStream.Position = 0
        $Reader = New-Object System.IO.StreamReader -ArgumentList $Response.RawContentStream, ([System.Text.Encoding]::UTF8)
        $Text = $Reader.ReadToEnd()
    } else {
        $Text = $Response.Content
    }
    return $Text | ConvertFrom-Json
}

$Run = Invoke-JsonRequest `
    -Method "Post" `
    -Uri "$BaseUrl/ops/run-recommendations" `
    -Body @{
        mode = "fixture"
        keyword = "AI"
        page_no = 1
        num_rows = 3
        include_reports = $true
        confirm_real_api_call = $false
    }

$Runs = Invoke-JsonRequest -Method "Get" -Uri "$BaseUrl/ops/runs?limit=5"
$Recommendations = Invoke-JsonRequest -Method "Get" -Uri "$BaseUrl/ops/recommendations?limit=5&run_id=$($Run.run_id)"
$Reports = Invoke-JsonRequest -Method "Get" -Uri "$BaseUrl/ops/reports/$($Run.run_id)"
$ReportLoaded = $false

if ($Reports.reports.Count -gt 0) {
    $FirstReport = $Reports.reports | Select-Object -First 1
    $ReportContent = Invoke-JsonRequest `
        -Method "Get" `
        -Uri "$BaseUrl/ops/report-content/$($Run.run_id)/$($FirstReport.notice_id)"
    $ReportLoaded = -not [string]::IsNullOrWhiteSpace($ReportContent.markdown)
}

@{
    ok = $true
    run_id = $Run.run_id
    run_status = $Run.status
    run_count = $Runs.runs.Count
    recommendation_count = $Recommendations.recommendations.Count
    report_count = $Reports.reports.Count
    report_loaded = $ReportLoaded
    service_key_exposed = $false
} | ConvertTo-Json -Depth 10
