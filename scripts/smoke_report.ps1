$ErrorActionPreference = "Stop"

$Utf8 = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $Utf8
$OutputEncoding = $Utf8

try {
    chcp.com 65001 | Out-Null
} catch {
    # Ignore if chcp is unavailable.
}

$Uri = "http://127.0.0.1:8000/recommendations/report"

$BodyJson = @(
    '{',
    '  "title": "\uc11c\uc6b8 AI \uc18c\ud504\ud2b8\uc6e8\uc5b4 \uac1c\ubc1c",',
    '  "agency": "\uc11c\uc6b8\ud2b9\ubcc4\uc2dc \uac15\ub0a8\uad6c",',
    '  "budget_amount": 55000000,',
    '  "deadline": "2026-07-15",',
    '  "region": "\uc11c\uc6b8",',
    '  "contract_type": "\ud611\uc0c1\uc5d0 \uc758\ud55c \uacc4\uc57d",',
    '  "business_type": "\uc6a9\uc5ed",',
    '  "qualification_text": "\uc18c\ud504\ud2b8\uc6e8\uc5b4\uc0ac\uc5c5\uc790, \uc18c\uae30\uc5c5 \ub610\ub294 \uc18c\uc0c1\uacf5\uc778",',
    '  "description": "\uc778\uacf5\uc9c0\ub2a5 \uc18c\ud504\ud2b8\uc6e8\uc5b4 \uac1c\ubc1c \ubc0f \ud074\ub77c\uc6b0\ub4dc \uae30\ubc18 \uc2dc\uc2a4\ud15c \uad6c\ucd95",',
    '  "keywords": ["AI", "cloud", "software"]',
    '}'
) -join "`n"

$Bytes = [System.Text.Encoding]::UTF8.GetBytes($BodyJson)

$Response = Invoke-WebRequest `
    -Method Post `
    -Uri $Uri `
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