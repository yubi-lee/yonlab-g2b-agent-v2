$ErrorActionPreference = "Stop"

$Utf8 = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $Utf8
$OutputEncoding = $Utf8
try { chcp.com 65001 | Out-Null } catch {}

$BaseUrl = $env:YONLAB_G2B_BASE_URL
if ([string]::IsNullOrWhiteSpace($BaseUrl)) {
    $BaseUrl = "http://127.0.0.1:8000"
}

$BodyJson = @'
{
  "\uacf5\uace0\uba85": "\uc11c\uc6b8 AI \uc18c\ud504\ud2b8\uc6e8\uc5b4 \uac1c\ubc1c",
  "\uc218\uc694\uae30\uad00": "\uc11c\uc6b8\ud2b9\ubcc4\uc2dc \uac15\ub0a8\uad6c",
  "\ucd94\uc815\uac00\uaca9": "55,000,000\uc6d0",
  "\uc785\ucc30\ub9c8\uac10\uc77c\uc2dc": "2026-07-15",
  "\uc9c0\uc5ed\uc81c\ud55c": "\uc11c\uc6b8",
  "\uacc4\uc57d\ubc29\ubc95": "\ud611\uc0c1\uc5d0 \uc758\ud55c \uacc4\uc57d",
  "\uc5c5\ubb34\uad6c\ubd84": "\uc6a9\uc5ed",
  "\ucc38\uac00\uc790\uaca9": "\uc18c\ud504\ud2b8\uc6e8\uc5b4\uc0ac\uc5c5\uc790, \uc18c\uae30\uc5c5 \ub610\ub294 \uc18c\uc0c1\uacf5\uc778",
  "\uacfc\uc5c5\ub0b4\uc6a9": "\uc778\uacf5\uc9c0\ub2a5 \uc18c\ud504\ud2b8\uc6e8\uc5b4 \uac1c\ubc1c \ubc0f \ud074\ub77c\uc6b0\ub4dc \uae30\ubc18 \uc2dc\uc2a4\ud15c \uad6c\ucd95",
  "\ud0a4\uc6cc\ub4dc": ["AI", "\ud074\ub77c\uc6b0\ub4dc", "\uc18c\ud504\ud2b8\uc6e8\uc5b4"]
}
'@

$Bytes = [System.Text.Encoding]::UTF8.GetBytes($BodyJson)

$Response = Invoke-WebRequest `
    -Method Post `
    -Uri "$BaseUrl/recommendations/report" `
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
if ($Object.markdown) {
    $Object.markdown
} elseif ($Object.report.markdown) {
    $Object.report.markdown
} else {
    $Object | ConvertTo-Json -Depth 30
}
