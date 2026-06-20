$ErrorActionPreference = "Stop"

$BaseUrl = $env:YONLAB_G2B_BASE_URL
if ([string]::IsNullOrWhiteSpace($BaseUrl)) {
    $BaseUrl = "http://127.0.0.1:8000"
}

$Body = @{
    "공고명" = "서울 AI 소프트웨어 개발"
    "수요기관" = "테스트기관"
    "추정가격" = "55,000,000원"
    "입찰마감일시" = "2026-07-20"
    "지역제한" = "서울특별시"
    "참가자격" = "소프트웨어사업자, 소기업, 창업기업 우대"
    "과업내용" = "AI Agent 정보시스템개발서비스 클라우드 시스템 구축"
} | ConvertTo-Json -Depth 5

$Response = Invoke-RestMethod `
    -Method Post `
    -Uri "$BaseUrl/recommendations/report" `
    -ContentType "application/json; charset=utf-8" `
    -Body $Body

$Response | ConvertTo-Json -Depth 12
