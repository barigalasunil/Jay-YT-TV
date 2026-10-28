# Usage: .\scripts\install-to-tv.ps1 -TvIp 192.168.1.50 [-Apk path\to\KidTube.apk]
param(
  [Parameter(Mandatory = $true)][string]$TvIp,
  [string]$Apk = ""
)
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Get-Command adb -ErrorAction SilentlyContinue)) { throw "adb not found. Install Android platform-tools (comes with Android Studio) and add it to PATH." }

if ($Apk -eq "") {
  if (-not (Get-Command gh -ErrorAction SilentlyContinue)) { throw "gh not found. Pass -Apk <path> instead." }
  New-Item -ItemType Directory -Force downloads | Out-Null
  gh release download --pattern KidTube.apk --dir downloads --clobber
  $Apk = "downloads\KidTube.apk"
}

adb connect "${TvIp}:5555"
Read-Host "If the TV shows 'Allow USB debugging?', choose Always allow + OK, then press Enter here"
adb -s "${TvIp}:5555" install -r $Apk
Write-Host "Installed. Open KidTube from the TV's app list."
