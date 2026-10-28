#!/usr/bin/env bash
# One-time: creates your app signing key and stores it as GitHub secrets.
# Needs: JDK 17 (keytool), GitHub CLI (gh) logged in (gh auth login), run inside your cloned repo.
set -euo pipefail
cd "$(dirname "$0")/.."

command -v keytool >/dev/null || { echo "keytool not found. Install JDK 17 first."; exit 1; }
command -v gh >/dev/null      || { echo "GitHub CLI (gh) not found. Install it from https://cli.github.com"; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "Not logged in. Run: gh auth login"; exit 1; }

if [ -f kidtube.jks ]; then
  echo "kidtube.jks already exists. Refusing to overwrite it (that would break updates)."
  exit 1
fi

PASS="$(LC_ALL=C tr -dc 'a-f0-9' </dev/urandom | head -c 32)"

keytool -genkeypair -v -keystore kidtube.jks -alias kidtube \
  -keyalg RSA -keysize 2048 -validity 10000 \
  -storepass "$PASS" -keypass "$PASS" \
  -dname "CN=KidTube, O=Home, C=US"

B64="$(base64 < kidtube.jks | tr -d '\n')"
printf %s "$B64"       | gh secret set KEYSTORE_B64
printf %s "$PASS"      | gh secret set KEYSTORE_PASSWORD
printf %s "kidtube"    | gh secret set KEY_ALIAS
printf %s "$PASS"      | gh secret set KEY_PASSWORD

printf 'alias: kidtube\nstore+key password: %s\n' "$PASS" > kidtube-passwords.txt

cat <<MSG

Done. The 4 GitHub secrets are set.

!!! BACK UP these two files somewhere safe (cloud drive / pen drive): !!!
    kidtube.jks
    kidtube-passwords.txt
If you lose them you can never update the app installed on your TV (you'd have to uninstall and reinstall).
They are git-ignored, so they will NOT be pushed to GitHub.
MSG
