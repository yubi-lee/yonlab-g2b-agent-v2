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
    "공고명" = "서울 AI 소프트웨어 개발"
    "수요기관" = "서울특별시 강남구"
    "추정가격" = "55,000,000원"
    "입찰마감일시" = "2026-07-15"
    "지역제한" = "서울"
    "계약방법" = "협상에 의한 계약"
    "업무구분" = "용역"
    "참가자격" = "소프트웨어사업자, 소기업 또는 소상공인"
    "과업내용" = "인공지능 소프트웨어 개발 및 클라우드 기반 시스템 구축"
    "키워드" = @("AI", "클라우드", "소프트웨어")
} | ConvertTo-Json -Depth 10

$Bytes = [System.Text.Encoding]::UTF8.GetBytes($BodyJson)

$Response = Invoke-WebRequest `
    -Method Post `
    -Uri "$BaseUrl/recommendations/report" `
    -ContentType "application/json; charset=utf-8" `
    -Body $Bytes

if ($Response.RawContentStream) {
    $Response.RawContentStream.Position = 0
    $Reader = New-Object System.IO.StreamReader -ArgumentList $Response.RawContentStream, ([System.Text.Encoding]::UTF8)
    $Text = $Reader.ReadToEnd()
} else {
    $Text = $Response.Content
}

$Object = $Text | ConvertFrom-Json
if ($Object.markdown) {
    $Object.markdown
} elseif ($Object.report.markdown) {
    $Object.report.markdown
} else {
    $Object | ConvertTo-Json -Depth 30
}
