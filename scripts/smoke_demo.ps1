$ErrorActionPreference = "Stop"

$Utf8 = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $Utf8
$OutputEncoding = $Utf8

try {
    chcp.com 65001 | Out-Null
} catch {
    # Ignore if chcp is unavailable.
}

$Uri = "http://127.0.0.1:8000/demo/recommendations"

$BodyJson = @{
    include_reports = $false
    limit = 5
} | ConvertTo-Json -Depth 10

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

$Text | ConvertFrom-Json | ConvertTo-Json -Depth 30