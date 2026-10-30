#!/usr/bin/env bash
# Usage: scripts/install-to-tv.sh <TV_IP> [path/to/app.apk]
# With no apk path it downloads the latest APK (e.g. Jay-TV.apk) from your GitHub Releases (needs gh).
set -euo pipefail
cd "$(dirname "$0")/.."

TV_IP="${1:?Usage: $0 <TV_IP> [apk]}"
APK="${2:-}"

command -v adb >/dev/null || { echo "adb not found. Install Android platform-tools (comes with Android Studio)."; exit 1; }

if [ -z "$APK" ]; then
  command -v gh >/dev/null || { echo "gh not found. Pass an APK path instead."; exit 1; }
  mkdir -p downloads
  gh release download --pattern "*.apk" --dir downloads --clobber
  APK="$(ls -t downloads/*.apk | head -n 1)"
fi

adb connect "${TV_IP}:5555"
echo "If the TV shows 'Allow USB debugging?', choose Always allow + OK, then press Enter here."
read -r _
adb -s "${TV_IP}:5555" install -r "$APK"
echo "Installed. Open Jay TV from the TV's app list."
