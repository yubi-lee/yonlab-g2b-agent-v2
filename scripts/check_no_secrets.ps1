$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$Utf8 = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $Utf8
$OutputEncoding = $Utf8
try { chcp.com 65001 | Out-Null } catch {}

$AllowedFiles = @(
    ".env.example",
    "scripts\check_no_secrets.ps1"
)

$Violations = New-Object System.Collections.Generic.List[string]

$RepoFiles = git ls-files --cached --others --exclude-standard
if ($LASTEXITCODE -ne 0) {
    throw "Unable to list repository files for no-secret check."
}

$RepoFiles | ForEach-Object {
    $RelativePath = $_
    $FullPath = Join-Path $ProjectRoot $RelativePath
    if (-not (Test-Path -LiteralPath $FullPath -PathType Leaf)) {
        return
    }

    try {
        $Content = Get-Content -LiteralPath $FullPath -Raw -Encoding utf8
    } catch {
        return
    }

    $IsAllowedFile = $AllowedFiles -contains $RelativePath
    if (
        -not $IsAllowedFile `
        -and $Content -match "(?m)^G2B_API_SERVICE_KEY=(?!\s*$)(?!<your local key>\s*$).+"
    ) {
        $Violations.Add("$RelativePath contains a non-placeholder G2B_API_SERVICE_KEY value.")
    }
    if (-not $IsAllowedFile -and $Content -match "(?i)serviceKey\s*=\s*[^`\r`\n\s][^`\r`\n]*") {
        $Violations.Add("$RelativePath contains a non-empty serviceKey query value.")
    }
}

if ($Violations.Count -gt 0) {
    $Violations | ForEach-Object { Write-Host $_ }
    throw "No-secret check failed."
}

Write-Host "No-secret check completed successfully."
