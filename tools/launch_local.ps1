<#
Launch FIFA 16 pointed at the local revival server.

Uses the client's built-in override settings (no binary patching, no
admin rights needed):

  Environment variables (read directly by the game):
    BLAZEIP / BLAZEPORT      -> skip redirector, connect to our Blaze server
    FUT_TARGET_HOSTNAME/PORT -> FUT RS4 API override
    FIFA_POW_URL             -> EASFC POW web API override
    OSDK_EASW_REQ_URL        -> SportsWorld/EASW override

  user.ini (game dir, highest-priority Aardvark settings file).

Usage:
  .\tools\launch_local.ps1              # launch game with overrides
  .\tools\launch_local.ps1 -NoUserIni   # env vars only
  .\tools\launch_local.ps1 -Restore     # restore original user.ini and exit
  .\tools\launch_local.ps1 -RemoveUserIni
#>

param(
    [string]$GamePath = "D:\FIFA-16-SteamRIP.com\FIFA 16",
    [string]$ServerHost = "127.0.0.1",
    [int]$BlazePort = 42127,
    [int]$FutPort = 42129,
    [int]$PowPort = 42129,
    [switch]$NoUserIni,
    [switch]$Restore,
    [switch]$RemoveUserIni,
    [switch]$NoLaunch
)

$ErrorActionPreference = "Stop"

$exe = Join-Path $GamePath "fifa16.exe"
$userIni = Join-Path $GamePath "user.ini"
$backupIni = Join-Path $GamePath "user.ini.revival-backup"

if (-not (Test-Path $exe)) {
    Write-Error "fifa16.exe not found at: $exe  (use -GamePath)"
}

if ($Restore) {
    if (Test-Path $backupIni) {
        Copy-Item $backupIni $userIni -Force
        Write-Host "Restored original user.ini from backup." -ForegroundColor Green
    } else {
        Write-Host "No user.ini.revival-backup found - nothing to restore."
    }
    exit 0
}

if ($RemoveUserIni) {
    if (Test-Path $userIni) {
        Remove-Item $userIni -Force
        Write-Host "Removed revival user.ini." -ForegroundColor Green
    }
    if (Test-Path $backupIni) {
        Copy-Item $backupIni $userIni -Force
        Write-Host "Restored original user.ini."
    }
    exit 0
}

# ---- Environment overrides (the primary, safest vector) ----
$env:BLAZEIP = $ServerHost
$env:BLAZEPORT = "$BlazePort"
$env:BLAZE_LOGGING = "1"
$env:FUT_TARGET_HOSTNAME = $ServerHost
$env:FUT_TARGET_PORT = "$FutPort"
$env:FIFA_POW_URL = "http://${ServerHost}:${PowPort}"
$env:FIFA_POW_CONTENT_SERVER_URL = "http://${ServerHost}:${PowPort}"
$env:FIFA_POW_NUCLEUS_PROXY_URL = "http://${ServerHost}:${PowPort}"
$env:OSDK_EASW_REQ_URL = "http://${ServerHost}:${PowPort}"

Write-Host "=== FIFA 16 Revival - Local Launch ===" -ForegroundColor Cyan
Write-Host "Game:     $exe"
Write-Host "Blaze:    ${ServerHost}:${BlazePort}   (BLAZEIP/BLAZEPORT)"
Write-Host "FUT API:  ${ServerHost}:${FutPort}   (FUT_TARGET_HOSTNAME/PORT)"
Write-Host "POW/EASW: http://${ServerHost}:${PowPort}   (FIFA_POW_URL, OSDK_EASW_REQ_URL)"

# ---- user.ini override (highest priority Aardvark settings file) ----
if (-not $NoUserIni) {
    if ((Test-Path $userIni) -and -not (Test-Path $backupIni)) {
        Copy-Item $userIni $backupIni
        Write-Host "Backed up existing user.ini -> user.ini.revival-backup"
    }

    $ini = @"
; Managed by fifa16-revival launch_local.ps1 - delete or run -Restore to undo
[ONLINE]
BLAZEIP=$ServerHost
BLAZEPORT=$BlazePort
FUT_TARGET_HOSTNAME=$ServerHost
FUT_TARGET_PORT=$FutPort

[POW]
FIFA_POW_URL=http://${ServerHost}:${PowPort}
FORCE-NON-SECURE=1

; flat-key form (some Aardvark loaders read keys without sections)
ONLINE/BLAZEIP=$ServerHost
ONLINE/BLAZEPORT=$BlazePort
FUT_TARGET_HOSTNAME=$ServerHost
FUT_TARGET_PORT=$FutPort
FIFA_POW_URL=http://${ServerHost}:${PowPort}
ONLINE/FORCE-NON-SECURE=1
"@
    Set-Content -Path $userIni -Value $ini -Encoding ASCII
    Write-Host "Wrote user.ini overrides to $userIni"
}

if ($NoLaunch) {
    Write-Host "Environment set. Launch the game manually from this session." -ForegroundColor Yellow
    return
}

Write-Host "Launching FIFA 16..." -ForegroundColor Green

# Overrides passed in the command line too (belt and braces: env vars +
# user.ini + argv). Unrecognized switches are ignored by the Aardvark
# settings parser, so extra forms are harmless.
$gameArgs = @(
    "-BLAZEIP", $ServerHost,
    "-BLAZEPORT", "$BlazePort",
    "-ONLINE/BLAZEIP", $ServerHost,
    "-ONLINE/BLAZEPORT", "$BlazePort",
    "-FUT_TARGET_HOSTNAME", $ServerHost,
    "-FUT_TARGET_PORT", "$FutPort",
    "-FIFA_POW_URL", "http://${ServerHost}:${PowPort}",
    "-OSDK_EASW_REQ_URL", "http://${ServerHost}:${PowPort}"
)

Write-Host "Game args: $($gameArgs -join ' ')"
Start-Process -FilePath $exe -WorkingDirectory $GamePath -ArgumentList $gameArgs
Write-Host "Watch logs\network_journal.jsonl for incoming connections."
Write-Host "Server must already be running:  python run_server.py"
