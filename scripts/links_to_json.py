#!/usr/bin/env python3
"""Turns links.txt into channels.json (standard library only).

  video link   -> song   (id read from the link; title from YouTube oEmbed)
  channel link -> channel (UC... id read from the link or from the channel page)

Usage: python3 scripts/links_to_json.py [links.txt] [channels.json]
Exit code 0 = file written. Lines that could not be resolved are listed and skipped.
If NOTHING could be resolved from a non-empty links.txt, the old channels.json is left untouched.
"""
import json
import re
import sys
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
VIDEO_ID = r"[A-Za-z0-9_-]{11}"
CHANNEL_ID = r"UC[A-Za-z0-9_-]{22}"


def fetch(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept-Language": "en-US,en;q=0.9",
        "Cookie": "CONSENT=YES+1; SOCS=CAI",  # skips the EU consent page
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", "replace")


def video_id_from(url):
    p = urllib.parse.urlparse(url)
    host = p.netloc.lower().replace("www.", "").replace("m.", "")
    if host == "youtu.be":
        m = re.match(r"/(%s)" % VIDEO_ID, p.path)
        return m.group(1) if m else None
    if host.endswith("youtube.com") or host.endswith("youtube-nocookie.com"):
        if p.path == "/watch":
            v = urllib.parse.parse_qs(p.query).get("v", [""])[0]
            return v if re.fullmatch(VIDEO_ID, v) else None
        m = re.match(r"/(?:shorts|embed|live|v)/(%s)" % VIDEO_ID, p.path)
        return m.group(1) if m else None
    return None


def song_title(video_id):
    try:
        u = "https://www.youtube.com/oembed?format=json&url=" + urllib.parse.quote(
            "https://www.youtube.com/watch?v=" + video_id, safe="")
        return json.loads(fetch(u)).get("title") or video_id
    except Exception:
        return video_id


def channel_from(url):
    """returns (channel_id, name) or raises"""
    m = re.search(r"/channel/(%s)" % CHANNEL_ID, url)
    cid = m.group(1) if m else None

    # Need the page for @handle/c/user links, and for the display name.
    name = None
    try:
        page = fetch(url if cid is None else "https://www.youtube.com/channel/" + cid)
        if cid is None:
            for pat in (r'"externalId":"(%s)"' % CHANNEL_ID,
                        r'"channelId":"(%s)"' % CHANNEL_ID,
                        r'<meta itemprop="(?:identifier|channelId)" content="(%s)"' % CHANNEL_ID,
                        r'youtube\.com/channel/(%s)' % CHANNEL_ID):
                mm = re.search(pat, page)
                if mm:
                    cid = mm.group(1)
                    break
        t = re.search(r'<meta property="og:title" content="([^"]+)"', page)
        if t:
            name = (t.group(1).replace("&amp;", "&").replace("&#39;", "'").replace("&quot;", '"'))
    except Exception as e:
        if cid is None:
            raise RuntimeError("could not open the channel page: %s" % e)
    if cid is None:
        raise RuntimeError("no channel id found on the page")
    return cid, (name or cid)


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "links.txt"
    dst = sys.argv[2] if len(sys.argv) > 2 else "channels.json"

    channels, songs, failed = [], [], []
    seen_c, seen_s = set(), set()
    wanted = 0

    for raw in open(src, encoding="utf-8"):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        custom = None
        if "|" in line and not line.lower().startswith("http"):
            custom, line = [x.strip() for x in line.split("|", 1)]
        wanted += 1
        if not re.match(r"https?://", line):
            failed.append((raw.strip(), "not a link"))
            continue

        try:
            vid = video_id_from(line)
            if vid:
                if vid not in seen_s:
                    seen_s.add(vid)
                    songs.append({"title": custom or song_title(vid), "id": vid})
                continue
            if "list=" in line and "/playlist" in line:
                failed.append((raw.strip(), "playlist links are not supported; use a channel or video link"))
                continue
            cid, name = channel_from(line)
            if cid not in seen_c:
                seen_c.add(cid)
                channels.append({"name": custom or name, "id": cid})
        except Exception as e:
            failed.append((raw.strip(), str(e)))

    print("Channels: %d | Songs: %d | Failed: %d" % (len(channels), len(songs), len(failed)))
    for line, why in failed:
        print("  FAILED: %s  ->  %s" % (line, why))

    if wanted and not channels and not songs:
        print("Nothing could be resolved. Leaving %s unchanged." % dst)
        sys.exit(1)

    with open(dst, "w", encoding="utf-8") as f:
        json.dump({"version": 1, "channels": channels, "songs": songs}, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print("Wrote", dst)
    sys.exit(2 if failed else 0)


if __name__ == "__main__":
    main()
