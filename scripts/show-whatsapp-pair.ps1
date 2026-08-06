#Requires -Version 5.1
<#
.SYNOPSIS
  Stream lucero-whatsapp Railway logs and highlight the WhatsApp pair code.

.DESCRIPTION
  Railway's web Deploy Logs UI mangles ASCII QR codes. Prefer the 8-character
  pair code printed by ZeroClaw when ZEROCLAW_PAIR_PHONE is set.

  On the phone:
    WhatsApp → Settings → Linked Devices → Link a device
    → Link with phone number instead → enter the code shown here.
#>
param(
    [string]$Service = "lucero-whatsapp",
    [int]$Lines = 80
)

$ErrorActionPreference = "Stop"
$Backend = Join-Path (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)) "backend"

Write-Host "Streaming $Service logs. Watch for an 8-character pair code." -ForegroundColor Cyan
Write-Host "Phone: WhatsApp → Linked Devices → Link with phone number instead" -ForegroundColor Yellow
Write-Host ""

Push-Location $Backend
try {
    npx --yes @railway/cli@latest logs --service $Service --lines $Lines 2>&1 |
        ForEach-Object {
            $line = "$_"
            if ($line -match '(?i)pair(?:ing)?\s*code[^A-Z0-9]*([A-Z0-9]{8})\b') {
                Write-Host ""
                Write-Host ("=" * 40) -ForegroundColor Green
                Write-Host ("  PAIR CODE: " + $Matches[1]) -ForegroundColor Green
                Write-Host ("=" * 40) -ForegroundColor Green
                Write-Host ""
            } elseif ($line -match '(?i)pair-code flow|Link your phone|enter this code') {
                Write-Host $line -ForegroundColor Green
            } elseif ($line -match 'WhatsApp Web QR code') {
                Write-Host $line -ForegroundColor DarkYellow
                Write-Host "(QR in Railway web UI is not scannable — use pair code instead)" -ForegroundColor DarkYellow
            } else {
                Write-Host $line
            }
        }
} finally {
    Pop-Location
}
