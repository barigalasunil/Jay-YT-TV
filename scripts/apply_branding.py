#!/usr/bin/env python3
"""Applies the files in branding/ to the app. The GitHub workflow runs this before every build.

  branding/app_name.txt  -> the app's name (launcher label and the title inside the app)
  branding/icon.png      -> app icon (square, 512x512 or bigger recommended, transparent corners allowed)
  branding/banner.png    -> TV home-screen tile (16:9, 1280x720 recommended)
  branding/logo.png      -> OPTIONAL small logo inside the app (defaults to icon.png)

Missing files are simply skipped. Needs Pillow:  pip install pillow
"""
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRAND = os.path.join(ROOT, "branding")
RES = os.path.join(ROOT, "smarttubetv", "src", "stfdroid", "res")


def cover(img, w, h):
    """Resize + center-crop so the image fills w x h exactly."""
    sw, sh = img.size
    scale = max(w / sw, h / sh)
    nw, nh = max(1, round(sw * scale)), max(1, round(sh * scale))
    img = img.resize((nw, nh), Image.LANCZOS)
    left, top = (nw - w) // 2, (nh - h) // 2
    return img.crop((left, top, left + w, top + h))


def save(img, rel, w, h, mode):
    out = os.path.join(RES, rel)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    cover(img.convert("RGBA"), w, h).convert(mode).save(out, optimize=True)
    print("wrote", rel, "%dx%d" % (w, h))


def main():
    # ---- name
    name_file = os.path.join(BRAND, "app_name.txt")
    if os.path.exists(name_file):
        lines = [l.strip() for l in open(name_file, encoding="utf-8") if l.strip()]
        if lines:
            name = lines[0][:40].replace("]]>", "")
            xml = ('<?xml version="1.0" encoding="utf-8"?>\n<resources>\n'
                   '    <string translatable="false" name="app_name"><![CDATA[%s]]></string>\n'
                   '    <string translatable="false" name="browse_title"><![CDATA[%s]]></string>\n'
                   '</resources>\n') % (name, name)
            with open(os.path.join(RES, "values", "strings.xml"), "w", encoding="utf-8") as f:
                f.write(xml)
            print("app name:", name)

    # ---- icon (+ logo)
    icon_path = os.path.join(BRAND, "icon.png")
    if os.path.exists(icon_path):
        icon = Image.open(icon_path)
        save(icon, "mipmap-nodpi/app_icon.png", 320, 320, "RGBA")
        save(icon, "mipmap-nodpi-v30/app_icon.png", 320, 320, "RGBA")  # Android 11+
        logo_path = os.path.join(BRAND, "logo.png")
        logo = Image.open(logo_path) if os.path.exists(logo_path) else icon
        # The in-app badge differs per color theme; use the same logo for all of them.
        for name in ("app_logo", "app_logo_semi_red", "app_logo_semi_grey"):
            save(logo, "mipmap-nodpi/%s.png" % name, 180, 180, "RGBA")

    # ---- TV banner
    banner_path = os.path.join(BRAND, "banner.png")
    if os.path.exists(banner_path):
        save(Image.open(banner_path), "mipmap-nodpi/app_banner.png", 640, 360, "RGB")


if __name__ == "__main__":
    sys.exit(main())
