# KidTube (a locked-down SmartTube fork)

Shows **only** the YouTube channels and songs listed in `channels.json`. No search, no Home / Trending /
Subscriptions, no recommendations, no autoplay into random videos. Built for Android TV
(tested target: Redmi Smart TV X50).

> **Honest status:** this code was written without being able to compile or run it (no Android SDK in the
> environment it was created in). Expect to fix a small compile error or two on the first build.
> See "If the build fails" below.

## How it works

| What | Where |
|---|---|
| Your channels + songs | `channels.json` in this repo (edit it on github.com, no rebuild needed) |
| TV reads the list | on every app start, from `raw.githubusercontent.com/<you>/<repo>/HEAD/channels.json` (cached; works offline with the last copy) |
| New app version | every push to the code builds a signed APK and publishes a GitHub Release; the TV app offers the update on start |

Sidebar on the TV: **Songs** (your song list), **one entry per channel** (its uploads), **Settings**.

## channels.json

```json
{
  "version": 1,
  "channels": [
    { "name": "Channel name", "id": "UCxxxxxxxxxxxxxxxxxxxxxx" }
  ],
  "songs": [
    { "title": "Song name", "id": "dQw4w9WgXcQ" }
  ]
}
```

* **Channel id**: starts with `UC`, 24 characters. Open the channel on YouTube in a browser. If the address
  is `youtube.com/channel/UC...` copy that part. If it is an `@handle`, use any "YouTube channel ID finder"
  website, or View page source and search for `channelId`.
* **Song id**: the 11 characters after `v=` in `youtube.com/watch?v=XXXXXXXXXXX` (or after `youtu.be/`).
* Rows whose id is still the placeholder text are ignored.
* Songs play in the order listed and loop back to the first one.

## One-time setup (about 15 minutes)

On your PC install: **Git**, **JDK 17**, **GitHub CLI** (then run `gh auth login`), and **Android platform-tools**
(`adb`; it comes with Android Studio).

1. Fork `yuliskov/SmartTube` on GitHub, clone **your fork** (`git clone --recurse-submodules <url>`),
   apply the KidTube patch (`git apply kidtube.patch`), commit.
2. Create the signing key and GitHub secrets with ONE command:
   * Windows: `powershell -ExecutionPolicy Bypass -File scripts\setup-signing.ps1`
   * Mac/Linux: `bash scripts/setup-signing.sh`

   **Back up `kidtube.jks` and `kidtube-passwords.txt`** (cloud drive / pen drive). Lose them and you can
   never update the installed app; you would have to uninstall and reinstall.
3. Edit `channels.json`, then `git push`. In your repo's **Actions** tab, "Build KidTube APK" runs
   (about 10-20 minutes the first time). When it finishes, **Releases** has `KidTube.apk`.
4. On the Redmi TV: Settings > Device Preferences > About > click **Build** 7 times. Then Developer options >
   turn on **USB debugging** (and "Network debugging" if present). Settings > Network shows the TV's IP.
   PC and TV must be on the same Wi-Fi.
5. Install: `scripts\install-to-tv.ps1 -TvIp <TV_IP>` (Windows) or `bash scripts/install-to-tv.sh <TV_IP>`.
   Accept the prompt on the TV. KidTube appears in the TV's app list.
6. **Lock Settings**: in KidTube open Settings > General > *Protect settings with a password* and set a PIN.
   Do this straight away; until then a child can open Settings and change things.

From now on:
* Change channels or songs: edit `channels.json` on github.com. Restart the app on the TV.
* Change code: push. The TV offers the update on next start (one click on "Install").

## Local build (optional)

Needs JDK 17 and the Android SDK (Android Studio installs it).

```
./gradlew assembleStfdroidDebug
# APK: smarttubetv/build/outputs/apk/stfdroid/debug/
```
For a local build, replace `YOUR_GITHUB_USER/YOUR_REPO` in
`common/src/main/java/.../models/data/AllowList.java` and `common/src/stfdroid/res/values/update_urls.xml`
with your `owner/repo`. (The GitHub workflow does this automatically.)

## What was changed in SmartTube

* New `AllowList.java`: loads/caches `channels.json`, answers "is this channel/video allowed?".
  One switch, `AllowList.LOCKDOWN`, turns the whole lockdown on/off.
* `BrowsePresenter`: sidebar is built from the allow-list only; long-press menus disabled; channels shown as plain upload grids.
* `SearchPresenter` + `BrowseFragment`: all search (text, voice, global, deep links) disabled; search orb removed.
* `PlaybackPresenter`, `VideoLoaderController`: a video opens only if its channel/id is allowed; checked again
  when real metadata arrives (closes the player if not). Songs loop; other videos close the player at the end.
* `SuggestionsController`: related-video rows removed from the player.
* `AppUpdatePresenter` + `update_urls.xml`: updates come from your repo's Releases (`kidtube.json`).
* Flavor `stfdroid` (the one without Firebase/analytics) renamed to `app.kidtube.tv`, label "KidTube".
* GitHub workflow `build.yml`; upstream's workflows removed.

## Known gaps

* Videos opened from outside (cast, deep links) have no channel until metadata loads, so they start and are then
  closed. Set `ALLOW_UNKNOWN_CHANNEL = false` in `AllowList.java` to block them up-front (stricter, but may
  block legitimate videos if YouTube omits the channel).
* Not every video can be played by third-party clients (some music videos are restricted). If a song never
  plays, try another upload of it.
* YouTube changes break third-party apps from time to time. Merge upstream SmartTube fixes occasionally:
  `git remote add upstream https://github.com/yuliskov/SmartTube.git && git fetch upstream && git merge upstream/master`.
* Using unofficial YouTube clients is against YouTube's terms. Fine for private home use.

## If the build fails

Copy the red error lines from the Actions log (or Gradle output) and give them, together with the file
mentioned, to your coding agent or to me. Most likely culprits: a missing import or a method name in
`BrowsePresenter`, `VideoLoaderController` or `PlaybackPresenter`.
