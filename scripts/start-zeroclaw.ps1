#Requires -Version 5.1
<#
.SYNOPSIS
  Build (if needed) and start ZeroClaw WhatsApp channel pointed at L.U.C.E.R.O.

.DESCRIPTION
  - Ensures integrations/zeroclaw is present (shallow clone if missing)
  - Builds with --features whatsapp-web when release binary is absent
  - Copies config.lucero.toml into ~/.zeroclaw/config.toml (unless -SkipConfig)
  - Starts `zeroclaw channel start` for QR pairing / inbound messages

.EXAMPLE
  .\scripts\start-zeroclaw.ps1
  .\scripts\start-zeroclaw.ps1 -SkipBuild
#>
param(
    [switch]$SkipBuild,
    [switch]$SkipConfig,
    [switch]$Daemon
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$ZcDir = Join-Path $Root "integrations\zeroclaw"
$ConfigSrc = Join-Path $ZcDir "config.lucero.toml"
$ZcHome = Join-Path $env:USERPROFILE ".zeroclaw"
$ConfigDst = Join-Path $ZcHome "config.toml"

Write-Host "L.U.C.E.R.O ZeroClaw launcher" -ForegroundColor Cyan
Write-Host "Root: $Root"

# Always restore Lucero overlay into the clone tree
$Overlay = Join-Path $Root "integrations\zeroclaw-lucero"
if (Test-Path (Join-Path $Overlay "config.lucero.toml")) {
    Copy-Item (Join-Path $Overlay "config.lucero.toml") $ConfigSrc -Force
}
if (Test-Path (Join-Path $Overlay "README.md")) {
    Copy-Item (Join-Path $Overlay "README.md") (Join-Path $ZcDir "README.LUCERO.md") -Force
}

if (-not (Test-Path (Join-Path $ZcDir "Cargo.toml"))) {
    Write-Host "Cloning zeroclaw-labs/zeroclaw (shallow)..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Force -Path (Split-Path $ZcDir) | Out-Null
    if (Test-Path $ZcDir) {
        # Keep overlay files if any
        Get-ChildItem $ZcDir -Force | Where-Object {
            $_.Name -notin @("config.lucero.toml", "README.LUCERO.md")
        } | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    }
    git clone --depth 1 https://github.com/zeroclaw-labs/zeroclaw.git $ZcDir
    if (Test-Path (Join-Path $Overlay "config.lucero.toml")) {
        Copy-Item (Join-Path $Overlay "config.lucero.toml") $ConfigSrc -Force
        Copy-Item (Join-Path $Overlay "README.md") (Join-Path $ZcDir "README.LUCERO.md") -Force -ErrorAction SilentlyContinue
    }
}

# Prefer env from backend/.env if not set
if (-not $env:LUCERO_CHANNEL_API_KEY) {
    $EnvFile = Join-Path $Root "backend\.env"
    if (Test-Path $EnvFile) {
        Get-Content $EnvFile | ForEach-Object {
            if ($_ -match '^\s*LUCERO_CHANNEL_API_KEY\s*=\s*(.+)\s*$') {
                $env:LUCERO_CHANNEL_API_KEY = $Matches[1].Trim().Trim('"')
            }
        }
    }
}
if (-not $env:LUCERO_CHANNEL_API_KEY) {
    Write-Warning "LUCERO_CHANNEL_API_KEY is not set. ZeroClaw will fail auth against L.U.C.E.R.O."
} else {
    Write-Host "LUCERO_CHANNEL_API_KEY loaded." -ForegroundColor Green
}

# Keep config api_key in sync with backend/.env so channel start works even when
# the parent process did not export LUCERO_CHANNEL_API_KEY (common on Windows).
if ($env:LUCERO_CHANNEL_API_KEY -and (Test-Path $ConfigSrc)) {
    $cfg = Get-Content $ConfigSrc -Raw
    if ($cfg -match 'api_key\s*=\s*"(?:env:LUCERO_CHANNEL_API_KEY|[^"]*)"') {
        $escaped = $env:LUCERO_CHANNEL_API_KEY.Replace('\', '\\').Replace('"', '\"')
        $cfg = [regex]::Replace(
            $cfg,
            'api_key\s*=\s*"(?:env:LUCERO_CHANNEL_API_KEY|[^"]*)"',
            "api_key = `"$escaped`"",
            1
        )
        Set-Content -Path $ConfigSrc -Value $cfg -NoNewline
    }
}

if (-not $SkipConfig) {
    if (-not (Test-Path $ConfigSrc)) {
        throw "Missing $ConfigSrc - add config.lucero.toml"
    }
    New-Item -ItemType Directory -Force -Path $ZcHome | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $ZcHome "state\whatsapp-web") | Out-Null
    Copy-Item $ConfigSrc $ConfigDst -Force

    # Local Windows session path (Docker uses ~/.zeroclaw under ZEROCLAW_HOME).
    $localSession = (Join-Path $ZcHome "state\whatsapp-web\session.db") -replace '\\', '/'
    $cfgLocal = Get-Content $ConfigDst -Raw
    $cfgLocal = [regex]::Replace(
        $cfgLocal,
        'session_path\s*=\s*"[^"]*"',
        "session_path = `"$localSession`""
    )
    if ($env:ZEROCLAW_PAIR_PHONE) {
        $pair = $env:ZEROCLAW_PAIR_PHONE.Trim()
        $cfgLocal = [regex]::Replace(
            $cfgLocal,
            'pair_phone\s*=\s*"[^"]*"',
            "pair_phone = `"$pair`""
        )
    }
    # Prefer local brain when LUCERO_API_BASE is unset and backend is on :8000.
    if ($env:LUCERO_API_BASE) {
        $base = $env:LUCERO_API_BASE.TrimEnd('/')
        $cfgLocal = [regex]::Replace(
            $cfgLocal,
            'uri\s*=\s*"[^"]*/v1"',
            "uri = `"$base/v1`""
        )
    }
    Set-Content -Path $ConfigDst -Value $cfgLocal -NoNewline
    Write-Host "Wrote $ConfigDst" -ForegroundColor Green
}

# Force ZeroClaw to use the Lucero-managed config directory rather than any
# unrelated global/default install directory on the machine.
$env:ZEROCLAW_CONFIG_DIR = $ZcHome
Write-Host "Using ZEROCLAW_CONFIG_DIR=$ZcHome" -ForegroundColor DarkGray

function Get-ZeroClawExecutable {
    param(
        [string]$ProjectDir
    )

    $candidates = @(
        (Join-Path $ProjectDir "target\release\zeroclaw.exe"),
        (Join-Path $ProjectDir "target\release\zeroclaw"),
        (Join-Path $ProjectDir "target\debug\zeroclaw.exe")
    )

    try {
        Push-Location $ProjectDir
        try {
            $metaJson = cargo metadata --format-version 1 --no-deps 2>$null
            if ($metaJson) {
                $meta = $metaJson | ConvertFrom-Json
                if ($meta.target_directory) {
                    $targetDir = [string]$meta.target_directory
                    $candidates += @(
                        (Join-Path $targetDir "release\zeroclaw.exe"),
                        (Join-Path $targetDir "release\zeroclaw"),
                        (Join-Path $targetDir "debug\zeroclaw.exe")
                    )
                }
            }
        } finally {
            Pop-Location
        }
    } catch {
        # Fall back to repo-local target paths
    }

    return $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}

$Exe = Get-ZeroClawExecutable -ProjectDir $ZcDir

if (-not $SkipBuild -or -not $Exe) {
    if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
        throw "Rust cargo not found. Install from https://rustup.rs/ then re-run."
    }
    Write-Host "Building ZeroClaw with whatsapp-web (this can take a while)..." -ForegroundColor Yellow
    Push-Location $ZcDir
    try {
        cargo build --release --features whatsapp-web
    } finally {
        Pop-Location
    }
    $Exe = Get-ZeroClawExecutable -ProjectDir $ZcDir
}

Write-Host ""
Write-Host "Ensure L.U.C.E.R.O API is running: http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "  ENABLE_CHANNEL_BRIDGE=true" -ForegroundColor DarkGray
Write-Host "WhatsApp: scan QR from terminal (Linked Devices)." -ForegroundColor Cyan
if ($Exe) {
    Write-Host "Starting: $Exe channel start" -ForegroundColor Green
} else {
    Write-Host "Binary path unresolved; falling back to cargo run." -ForegroundColor Yellow
}
Write-Host ""

Push-Location $ZcDir
try {
    if ($Exe) {
        if ($Daemon) {
            & $Exe daemon
        } else {
            & $Exe channel start
        }
    } else {
        if ($Daemon) {
            cargo run --release --features whatsapp-web -- daemon
        } else {
            cargo run --release --features whatsapp-web -- channel start
        }
    }
} finally {
    Pop-Location
}
