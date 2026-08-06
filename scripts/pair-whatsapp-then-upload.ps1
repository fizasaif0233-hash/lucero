#Requires -Version 5.1
<#
.SYNOPSIS
  Pair WhatsApp locally (clear terminal QR / pair code), then upload the
  session into Railway lucero-whatsapp so it stays linked 24/7.

.DESCRIPTION
  Railway's web log viewer cannot show a scannable QR. This script:
  1) Starts local ZeroClaw against the hosted Lucero brain
  2) You link the business phone (scan QR in this terminal, or type pair code)
  3) Uploads session.db to the Railway volume and restarts the service
#>
param(
    [string]$PairPhone = $env:ZEROCLAW_PAIR_PHONE,
    [switch]$SkipStart,
    [switch]$UploadOnly
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Backend = Join-Path $Root "backend"
$ZcHome = Join-Path $env:USERPROFILE ".zeroclaw"
$Session = Join-Path $ZcHome "state\whatsapp-web\session.db"

if (-not $PairPhone) { $PairPhone = "923203628978" }
$PairPhone = ($PairPhone -replace '[^\d]', '')

Write-Host "Lucero WhatsApp pair-then-upload" -ForegroundColor Cyan
Write-Host "Business phone digits: $PairPhone"
Write-Host "Session path: $Session"
Write-Host ""

if (-not $UploadOnly) {
    if (-not $SkipStart) {
        $env:ZEROCLAW_PAIR_PHONE = $PairPhone
        $env:LUCERO_API_BASE = "https://lucero-api-production.up.railway.app"
        if (-not $env:LUCERO_CHANNEL_API_KEY) {
            $envFile = Join-Path $Backend ".env"
            if (Test-Path $envFile) {
                Get-Content $envFile | ForEach-Object {
                    if ($_ -match '^\s*LUCERO_CHANNEL_API_KEY\s*=\s*(.+)\s*$') {
                        $env:LUCERO_CHANNEL_API_KEY = $Matches[1].Trim().Trim('"')
                    }
                }
            }
        }
        Write-Host "Starting local ZeroClaw. Link the business WhatsApp now." -ForegroundColor Yellow
        Write-Host "Prefer: Linked Devices → Link with phone number instead (pair code)." -ForegroundColor Yellow
        Write-Host "When linked, press Ctrl+C, then re-run with -UploadOnly" -ForegroundColor Yellow
        Write-Host ""
        & (Join-Path $Root "scripts\start-zeroclaw.ps1")
        return
    }
}

if (-not (Test-Path $Session)) {
    throw "No session file at $Session. Pair locally first (run without -UploadOnly)."
}

Write-Host "Uploading session.db to Railway volume..." -ForegroundColor Yellow
Push-Location $Backend
try {
    npx --yes @railway/cli@latest service link lucero-whatsapp | Out-Null
    $remoteDir = "/zeroclaw-data/.zeroclaw/state/whatsapp-web"
    npx --yes @railway/cli@latest volume files upload $Session "$remoteDir/session.db" --overwrite --json 2>&1
    Write-Host "Restarting lucero-whatsapp..." -ForegroundColor Yellow
    npx --yes @railway/cli@latest restart --service lucero-whatsapp 2>&1
    Write-Host "Done. Customers can message the business WhatsApp; Lucero should reply." -ForegroundColor Green
} finally {
    Pop-Location
}
