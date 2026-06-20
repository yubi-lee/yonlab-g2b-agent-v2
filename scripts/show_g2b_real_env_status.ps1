$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$Utf8 = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $Utf8
$OutputEncoding = $Utf8
try { chcp.com 65001 | Out-Null } catch {}

function Get-LocalSetting {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Name
    )

    $EnvironmentValue = [Environment]::GetEnvironmentVariable($Name)
    if (-not [string]::IsNullOrWhiteSpace($EnvironmentValue)) {
        return $EnvironmentValue
    }

    foreach ($FileName in @(".env", ".env.example")) {
        $Path = Join-Path $ProjectRoot $FileName
        if (-not (Test-Path -LiteralPath $Path)) {
            continue
        }
        $Line = Get-Content -LiteralPath $Path -Encoding utf8 |
            Where-Object { $_ -match "^\s*$Name\s*=" } |
            Select-Object -First 1
        if ($Line) {
            return ($Line -replace "^\s*$Name\s*=", "").Trim()
        }
    }
    return ""
}

$EndpointPath = Get-LocalSetting -Name "G2B_LIST_ENDPOINT_PATH"
$RecommendedPath = "/1230000/ad/BidPublicInfoService/getBidPblancListInfoServcPPSSrch"
$BasePath = "/1230000/ad/BidPublicInfoService"
$RealApiEnabled = (Get-LocalSetting -Name "G2B_ENABLE_REAL_API") -eq "true"
$ServiceKeyConfigured = -not [string]::IsNullOrWhiteSpace(
    (Get-LocalSetting -Name "G2B_API_SERVICE_KEY")
)

@{
    real_api_enabled = $RealApiEnabled
    service_key_configured = $ServiceKeyConfigured
    endpoint_path_configured = -not [string]::IsNullOrWhiteSpace($EndpointPath)
    current_endpoint_path = $EndpointPath
    base_path_warning = $EndpointPath -eq $BasePath
    recommended_endpoint_path = $RecommendedPath
} | ConvertTo-Json -Depth 5
