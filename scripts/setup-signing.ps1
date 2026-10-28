# One-time: creates your app signing key and stores it as GitHub secrets (Windows PowerShell).
# Needs: JDK 17 (keytool) and GitHub CLI (gh) logged in (gh auth login). Run inside your cloned repo.
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Get-Command keytool -ErrorAction SilentlyContinue)) { throw "keytool not found. Install JDK 17 first." }
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) { throw "GitHub CLI (gh) not found. Install it from https://cli.github.com" }
gh auth status *> $null
if ($LASTEXITCODE -ne 0) { throw "Not logged in. Run: gh auth login" }

if (Test-Path "kidtube.jks") { throw "kidtube.jks already exists. Refusing to overwrite it (that would break updates)." }

$bytes = New-Object byte[] 16
[Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
$pass = ($bytes | ForEach-Object { $_.ToString("x2") }) -join ""

keytool -genkeypair -v -keystore kidtube.jks -alias kidtube -keyalg RSA -keysize 2048 -validity 10000 `
  -storepass $pass -keypass $pass -dname "CN=KidTube, O=Home, C=US"
if ($LASTEXITCODE -ne 0) { throw "keytool failed" }

$b64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes((Resolve-Path "kidtube.jks")))
gh secret set KEYSTORE_B64 --body $b64
gh secret set KEYSTORE_PASSWORD --body $pass
gh secret set KEY_ALIAS --body "kidtube"
gh secret set KEY_PASSWORD --body $pass

"alias: kidtube`nstore+key password: $pass" | Set-Content kidtube-passwords.txt

Write-Host ""
Write-Host "Done. The 4 GitHub secrets are set."
Write-Host ""
Write-Host "!!! BACK UP these two files somewhere safe (cloud drive / pen drive): !!!" -ForegroundColor Yellow
Write-Host "    kidtube.jks"
Write-Host "    kidtube-passwords.txt"
Write-Host "If you lose them you can never update the app installed on your TV (you'd have to uninstall and reinstall)."
Write-Host "They are git-ignored, so they will NOT be pushed to GitHub."
