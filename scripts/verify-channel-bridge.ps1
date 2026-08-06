#Requires -Version 5.1
<#
.SYNOPSIS
  Smoke-test the L.U.C.E.R.O OpenAI-compatible channel bridge (no WhatsApp required).

.DESCRIPTION
  Calls GET /v1/models and POST /v1/chat/completions with the channel API key.
  Full WhatsApp QR pairing still requires: Rust, start-zeroclaw.ps1, Linked Devices.
#>
param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$ApiKey = "",
    [string]$ExternalId = "",
    [string]$Message = "Say hello in one short sentence as L.U.C.E.R.O channel bridge.",
    [switch]$ExpectDeny
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

if (-not $ApiKey) {
    $EnvFile = Join-Path $Root "backend\.env"
    if (Test-Path $EnvFile) {
        Get-Content $EnvFile | ForEach-Object {
            if ($_ -match '^\s*LUCERO_CHANNEL_API_KEY\s*=\s*(.+)\s*$') {
                $ApiKey = $Matches[1].Trim().Trim('"')
            }
        }
    }
}
if (-not $ApiKey) {
    throw "LUCERO_CHANNEL_API_KEY not set"
}

Write-Host "Health..." -ForegroundColor Cyan
try {
    $health = Invoke-RestMethod -Uri "$BaseUrl/health" -Method GET
    Write-Host ("  OK: {0}" -f $health.status) -ForegroundColor Green
} catch {
    throw "Backend not reachable at $BaseUrl - start uvicorn first. $_"
}

Write-Host "Models..." -ForegroundColor Cyan
$headers = @{
    Authorization = "Bearer $ApiKey"
    "Content-Type" = "application/json"
    "X-Lucero-Channel" = "whatsapp"
}
if ($ExternalId) {
    $headers["X-Lucero-External-Id"] = $ExternalId
}
if ($ExpectDeny -and -not $ExternalId) {
    $ExternalId = "+19999999999"
    $headers["X-Lucero-External-Id"] = $ExternalId
}
try {
    $models = Invoke-RestMethod -Uri "$BaseUrl/v1/models" -Headers $headers -Method GET
    Write-Host ("  OK: {0}" -f (($models.data | ForEach-Object { $_.id }) -join ", ")) -ForegroundColor Green
} catch {
    Write-Host "  FAIL: $_" -ForegroundColor Red
    throw
}

Write-Host "Chat completions (may call OpenRouter)..." -ForegroundColor Cyan
$bodyObj = @{
    model = "lucero/agents"
    messages = @(
        @{ role = "user"; content = $Message }
    )
}
if ($ExternalId) { $bodyObj.user = $ExternalId }
$body = $bodyObj | ConvertTo-Json -Depth 5

try {
    $resp = Invoke-RestMethod -Uri "$BaseUrl/v1/chat/completions" -Headers $headers -Method POST -Body $body
    $content = $resp.choices[0].message.content
    Write-Host "  Reply:" -ForegroundColor Green
    Write-Host $content
    Write-Host ""
    if ($ExpectDeny -and ($content -notmatch "not authorized")) {
        throw "Expected deny message for unknown number"
    }
    Write-Host "Bridge smoke test passed." -ForegroundColor Green
    Write-Host "QR WhatsApp: install Rust (rustup.rs), then .\scripts\start-zeroclaw.ps1 and Linked Devices." -ForegroundColor DarkGray
} catch {
    Write-Host "  FAIL: $_" -ForegroundColor Red
    if ($_.ErrorDetails.Message) { Write-Host $_.ErrorDetails.Message }
    throw
}
