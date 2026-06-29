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
        [string] $Uri
    )

    $Response = Invoke-WebRequest -Method Get -Uri $Uri -UseBasicParsing
    if ($Response.RawContentStream) {
        $Response.RawContentStream.Position = 0
        $Reader = New-Object System.IO.StreamReader -ArgumentList $Response.RawContentStream, ([System.Text.Encoding]::UTF8)
        $Text = $Reader.ReadToEnd()
    } else {
        $Text = $Response.Content
    }
    return $Text | ConvertFrom-Json
}

$ReviewBoard = Invoke-JsonRequest -Uri "$BaseUrl/ops/review-board"
$DailyReviewPack = Invoke-JsonRequest -Uri "$BaseUrl/ops/daily-review-pack"
$UiResponse = Invoke-WebRequest -Method Get -Uri "$BaseUrl/ui" -UseBasicParsing
if ($UiResponse.RawContentStream) {
    $UiResponse.RawContentStream.Position = 0
    $UiReader = New-Object System.IO.StreamReader -ArgumentList $UiResponse.RawContentStream, ([System.Text.Encoding]::UTF8)
    $UiText = $UiReader.ReadToEnd()
} else {
    $UiText = $UiResponse.Content
}

if ($ReviewBoard.service_key_exposed -ne $false) {
    throw "Review Board endpoint must not expose service keys."
}
if ($ReviewBoard.real_api_call_attempted -ne $false) {
    throw "Review Board smoke must not call the real API."
}
if (-not $ReviewBoard.PSObject.Properties.Name.Contains("cards")) {
    throw "Review Board endpoint must include cards."
}
if (-not $ReviewBoard.PSObject.Properties.Name.Contains("deadline_first_actions")) {
    throw "Review Board endpoint must include deadline-first actions."
}
if ($DailyReviewPack.service_key_exposed -ne $false) {
    throw "Daily Review Pack must not expose service keys."
}
if ($DailyReviewPack.real_api_call_attempted -ne $false) {
    throw "Daily Review Pack smoke must not call the real API."
}
if (-not $DailyReviewPack.PSObject.Properties.Name.Contains("review_board_summary")) {
    throw "Daily Review Pack must include Review Board summary."
}
if (-not $DailyReviewPack.PSObject.Properties.Name.Contains("deadline_first_next_actions")) {
    throw "Daily Review Pack must include deadline-first next actions."
}
if ($DailyReviewPack.markdown_report -notmatch "Review Board Summary") {
    throw "Daily Review Pack markdown must include Review Board Summary."
}
if ($UiResponse.StatusCode -ne 200) {
    throw "Expected /ui to return 200."
}
if ($UiText -notmatch "Review Board") {
    throw "Expected /ui to render Review Board."
}
if ($UiText -notmatch "review-board-title") {
    throw "Expected /ui to include review-board-title hook."
}

@{
    ok = $true
    endpoint = "/ops/review-board"
    daily_review_pack_endpoint = "/ops/daily-review-pack"
    ui_endpoint = "/ui"
    real_api_call_attempted = $false
    service_key_exposed = $false
    review_board_status = $ReviewBoard.status
    review_board_cards_present = $ReviewBoard.cards.Count -ge 0
    deadline_first_actions_present = $ReviewBoard.deadline_first_actions.Count -ge 0
    review_board_summary_present = $DailyReviewPack.review_board_summary.active_count -ge 0
    markdown_contains_review_board_summary = ($DailyReviewPack.markdown_report -match "Review Board Summary")
    ui_contains_review_board = $true
} | ConvertTo-Json -Depth 10
