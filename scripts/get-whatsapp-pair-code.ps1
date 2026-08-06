#Requires -Version 5.1
<#
.SYNOPSIS
  Start ZeroClaw in pair-code mode and print the 8-character code to text your client.

.EXAMPLE
  .\scripts\get-whatsapp-pair-code.ps1
  .\scripts\get-whatsapp-pair-code.ps1 -PairPhone 923203628978
#>
param(
    [string]$PairPhone = $(if ($env:ZEROCLAW_PAIR_PHONE) { $env:ZEROCLAW_PAIR_PHONE } else { "923203628978" })
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$PairPhone = ($PairPhone -replace '[^\d]', '')

Write-Host ""
Write-Host "WhatsApp PAIR CODE mode" -ForegroundColor Cyan
Write-Host "Business phone digits: $PairPhone"
Write-Host "When an 8-character code appears, TEXT it to your client." -ForegroundColor Yellow
Write-Host "Client: WhatsApp → Linked Devices → Link a device → Link with phone number instead" -ForegroundColor Yellow
Write-Host ""

$env:ZEROCLAW_PAIR_PHONE = $PairPhone
$env:LUCERO_API_BASE = "https://lucero-api-production.up.railway.app"

# Prepare config via start script helpers, but run ourselves so we can highlight the code.
$Overlay = Join-Path $Root "integrations\zeroclaw-lucero\config.lucero.toml"
$ZcHome = Join-Path $env:USERPROFILE ".zeroclaw"
$ConfigDst = Join-Path $ZcHome "config.toml"
New-Item -ItemType Directory -Force -Path (Join-Path $ZcHome "state\whatsapp-web") | Out-Null

$cfg = Get-Content $Overlay -Raw
$session = ((Join-Path $ZcHome "state\whatsapp-web\session.db") -replace '\\', '/')
if ($cfg -notmatch 'pair_phone') {
    $cfg = $cfg -replace '(\[channels\.whatsapp\.home\][^\[]*)', "`$1pair_phone = `"$PairPhone`"`r`n"
} else {
    $cfg = [regex]::Replace($cfg, 'pair_phone\s*=\s*"[^"]*"', "pair_phone = `"$PairPhone`"")
}
$cfg = [regex]::Replace($cfg, 'session_path\s*=\s*"[^"]*"', "session_path = `"$session`"")

# Also ensure channels_config for builds that read it
if ($cfg -notmatch '\[channels_config\.whatsapp\]') {
    $cfg += @"

[channels_config.whatsapp]
session_path = "$session"
pair_phone = "$PairPhone"
allowed_numbers = ["*"]
"@
}

if (-not $env:LUCERO_CHANNEL_API_KEY) {
    $envFile = Join-Path $Root "backend\.env"
    if (Test-Path $envFile) {
        Get-Content $envFile | ForEach-Object {
            if ($_ -match '^\s*LUCERO_CHANNEL_API_KEY\s*=\s*(.+)\s*$') {
                $env:LUCERO_CHANNEL_API_KEY = $Matches[1].Trim().Trim('"')
            }
        }
    }
}
if ($env:LUCERO_CHANNEL_API_KEY) {
    $escaped = $env:LUCERO_CHANNEL_API_KEY.Replace('\', '\\').Replace('"', '\"')
    $cfg = [regex]::Replace($cfg, 'api_key\s*=\s*"[^"]*"', "api_key = `"$escaped`"", 1)
}

Set-Content -Path $ConfigDst -Value $cfg -NoNewline
$env:ZEROCLAW_CONFIG_DIR = $ZcHome

$exe = @(
    (Join-Path $env:USERPROFILE ".zeroclaw\bin\zeroclaw.exe"),
    (Join-Path $Root "integrations\zeroclaw\target\release\zeroclaw.exe")
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $exe) { throw "zeroclaw.exe not found. Run .\scripts\start-zeroclaw.ps1 once to build/install." }

Write-Host "Using $exe" -ForegroundColor DarkGray
Write-Host "Watch for: pair code: XXXXXXXX" -ForegroundColor Green
Write-Host ""

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $exe
$psi.Arguments = "channel start"
$psi.WorkingDirectory = $Root
$psi.UseShellExecute = $false
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.CreateNoWindow = $true
$psi.Environment["ZEROCLAW_CONFIG_DIR"] = $ZcHome
$psi.Environment["LUCERO_CHANNEL_API_KEY"] = $env:LUCERO_CHANNEL_API_KEY
$psi.Environment["ZEROCLAW_PAIR_PHONE"] = $PairPhone

$proc = New-Object System.Diagnostics.Process
$proc.StartInfo = $psi
$null = $proc.Start()

$handler = {
    if (-not $EventArgs.Data) { return }
    $line = $EventArgs.Data
    [Console]::Out.WriteLine($line)
    if ($line -match '(?i)pair code:\s*([A-Za-z0-9]{8})\b') {
        $code = $Matches[1].ToUpper()
        [Console]::Out.WriteLine("")
        [Console]::Out.WriteLine("========================================")
        [Console]::Out.WriteLine("  TEXT THIS CODE TO YOUR CLIENT: $code")
        [Console]::Out.WriteLine("========================================")
        [Console]::Out.WriteLine("Client steps:")
        [Console]::Out.WriteLine("  WhatsApp → Settings → Linked Devices → Link a device")
        [Console]::Out.WriteLine("  → Link with phone number instead → enter $code")
        [Console]::Out.WriteLine("")
    }
}

$outEvent = Register-ObjectEvent -InputObject $proc -EventName OutputDataReceived -Action $handler
$errEvent = Register-ObjectEvent -InputObject $proc -EventName ErrorDataReceived -Action $handler
$proc.BeginOutputReadLine()
$proc.BeginErrorReadLine()

try {
    while (-not $proc.HasExited) {
        Start-Sleep -Milliseconds 400
    }
} finally {
    Unregister-Event -SourceIdentifier $outEvent.Name -ErrorAction SilentlyContinue
    Unregister-Event -SourceIdentifier $errEvent.Name -ErrorAction SilentlyContinue
}
