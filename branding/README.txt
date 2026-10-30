BRANDING FOLDER - change how the app looks without touching code

  app_name.txt  The app's name. One line. Example: Jay TV
  icon.png      App icon. Square, 512x512 or bigger. PNG.
  banner.png    TV home-screen tile. 16:9, 1280x720 recommended. PNG.
  logo.png      (optional) small logo inside the app. Square. If missing, icon.png is used.

How to change something:
  1. On github.com open this folder, then "Add file" > "Upload files" (same file name replaces the old one),
     or edit app_name.txt with the pencil icon.
  2. Commit. GitHub builds a new APK automatically (Actions tab, about 15 minutes).
  3. Open the app on the TV: it offers the update. Install it. Done.

You never need to resize images or put paths anywhere: scripts/apply_branding.py resizes and places them.
