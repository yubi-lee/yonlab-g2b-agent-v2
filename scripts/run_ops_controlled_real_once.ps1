param(
    [switch] $ConfirmRealApiCall,
    [string] $ProjectPath = "D:\Views\yonlab-g2b-agent-v2",
    [string] $ReleaseTag = "v0.1.0-rc5.1",
    [string] $DeployFolderName = "yonlab-g2b-agent-v2-rc5.1"
)

$ErrorActionPreference = "Stop"

$Utf8 = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $Utf8
$OutputEncoding = $Utf8
try { chcp.com 65001 | Out-Null } catch {}

Write-Host "Controlled real operation wrapper."
Write-Host "This command can use live G2B API quota. It is blocked by default."

if (-not $ConfirmRealApiCall) {
    Write-Host "Blocked: pass -ConfirmRealApiCall to run exactly one controlled real operation."
    exit 0
}

$ResolvedProjectPath = (Resolve-Path -LiteralPath $ProjectPath).Path
$DeployPath = Join-Path "D:\Deploy" $DeployFolderName
$DateStamp = Get-Date -Format "yyyyMMdd"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogDir = Join-Path $DeployPath "logs\ops\$DateStamp"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$OutLog = Join-Path $LogDir "controlled_real_once_$Timestamp.out.log"
$ErrLog = Join-Path $LogDir "controlled_real_once_$Timestamp.err.log"

$Arguments = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", "scripts\run_release_closeout_harness.ps1",
    "-ReleaseTag", $ReleaseTag,
    "-DeployFolderName", $DeployFolderName,
    "-RunControlledRealCall",
    "-ConfirmRealApiCall",
    "-SkipPush"
)

try {
    $Process = Start-Process `
        -FilePath "powershell.exe" `
        -ArgumentList $Arguments `
        -WorkingDirectory $ResolvedProjectPath `
        -Wait `
        -PassThru `
        -RedirectStandardOutput $OutLog `
        -RedirectStandardError $ErrLog

    $Text = ""
    if (Test-Path -LiteralPath $OutLog) {
        $Text += Get-Content -LiteralPath $OutLog -Raw
    }
    if (Test-Path -LiteralPath $ErrLog) {
        $Text += "`n" + (Get-Content -LiteralPath $ErrLog -Raw)
    }

    $Marker = "==> release closeout summary"
    $MarkerIndex = $Text.LastIndexOf($Marker)
    if ($MarkerIndex -lt 0) {
        throw "Controlled real harness summary was not found. See log path for details."
    }

    $Tail = $Text.Substring($MarkerIndex + $Marker.Length)
    $JsonStart = $Tail.IndexOf("{")
    if ($JsonStart -lt 0) {
        throw "Controlled real harness summary JSON was not found."
    }

    $JsonLines = New-Object System.Collections.Generic.List[string]
    $Depth = 0
    $Started = $false
    foreach ($Line in ($Tail.Substring($JsonStart) -split "`r?`n")) {
        if (-not $Started -and $Line.Trim().Length -eq 0) {
            continue
        }
        $Started = $true
        $JsonLines.Add($Line) | Out-Null
        foreach ($Char in $Line.ToCharArray()) {
            if ($Char -eq "{") { $Depth += 1 }
            if ($Char -eq "}") { $Depth -= 1 }
        }
        if ($Started -and $Depth -eq 0) {
            break
        }
    }

    $Summary = ($JsonLines -join "`n") | ConvertFrom-Json
    [pscustomobject]@{
        status = $Summary.deployment_status
        run_id = $Summary.run_id
        real_call_executed = $Summary.real_call_executed
        execution_count = $Summary.execution_count
        real_report_metadata_count = $Summary.real_report_metadata_count
        summary_status = $Summary.summary_status
        auto_run_gate_cleanup_ok = $Summary.yonlab_auto_run_real_api_cleanup_ok
        log_path = $OutLog
        service_key_exposed = $false
    } | ConvertTo-Json -Depth 8

    if ($Process.ExitCode -ne 0) {
        throw "Controlled real harness failed. Do not retry without reviewing the log."
    }
} finally {
    Remove-Item Env:\YONLAB_AUTO_RUN_REAL_API -ErrorAction SilentlyContinue
}