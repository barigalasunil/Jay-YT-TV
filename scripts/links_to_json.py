#!/usr/bin/env python3
"""Adds the links in links.txt to channels.json (standard library only).

Where a link goes (you choose):
  [songs] / [scenes] / [channels]      a header line: everything below it goes there
  song: <link>  scene: <link>  channel: <link>     a prefix on one line (wins over the header)
  no header and no prefix              automatic: video link -> song, anything else -> channel

Optional custom name:   scene: Peppa at the beach | https://youtu.be/XXXXXXXXXXX

It MERGES: everything already in channels.json is kept, new links are added at the end,
duplicates are skipped, a link that already exists is only renamed if you gave a custom name.
Nothing is ever removed (to remove something, edit channels.json).

Usage: python3 scripts/links_to_json.py [links.txt] [channels.json]
Exit codes: 0 = ok, 2 = ok but some lines could not be resolved, 1 = nothing could be resolved
(channels.json is left untouched in that case).
"""
import json
import re
import sys
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
VIDEO_ID = r"[A-Za-z0-9_-]{11}"
CHANNEL_ID = r"UC[A-Za-z0-9_-]{22}"

KINDS = {"channel": "channels", "channels": "channels",
         "song": "songs", "songs": "songs",
         "scene": "scenes", "scenes": "scenes"}


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


def video_title(video_id):
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


def load_existing(dst):
    data = {"channels": [], "songs": [], "scenes": []}
    try:
        with open(dst, encoding="utf-8") as f:
            old = json.load(f)
    except (OSError, ValueError):
        return data
    for c in old.get("channels", []):
        if re.fullmatch(CHANNEL_ID, str(c.get("id", ""))):
            data["channels"].append({"name": c.get("name") or c["id"], "id": c["id"]})
    for key in ("songs", "scenes"):
        for s in old.get(key, []):
            if re.fullmatch(VIDEO_ID, str(s.get("id", ""))):
                data[key].append({"title": s.get("title") or s.get("name") or s["id"], "id": s["id"]})
    return data


def parse_line(raw, current):
    """returns (kind, custom_name, link) or None for blank/comment/header lines.
    Header lines are reported as ('__header__', kind, None)."""
    line = raw.strip()
    if not line or line.startswith("#"):
        return None
    h = re.fullmatch(r"\[\s*([A-Za-z]+)\s*\]", line)
    if h and h.group(1).lower() in KINDS:
        return ("__header__", KINDS[h.group(1).lower()], None)
    kind = current
    p = re.match(r"(?i)^(channels?|songs?|scenes?)\s*:\s*(.*)$", line)
    if p:
        kind = KINDS[p.group(1).lower()]
        line = p.group(2).strip()
    custom = None
    if "|" in line and not re.match(r"(?i)^https?://", line):
        custom, line = [x.strip() for x in line.split("|", 1)]
    return (kind, custom, line)


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "links.txt"
    dst = sys.argv[2] if len(sys.argv) > 2 else "channels.json"

    data = load_existing(dst)
    before = {k: len(v) for k, v in data.items()}
    index = {k: {e["id"]: e for e in v} for k, v in data.items()}
    failed, wanted = [], 0
    current = None  # None = automatic

    for raw in open(src, encoding="utf-8"):
        parsed = parse_line(raw, current)
        if parsed is None:
            continue
        if parsed[0] == "__header__":
            current = parsed[1]
            continue
        kind, custom, link = parsed
        wanted += 1
        if not re.match(r"(?i)^https?://", link):
            failed.append((raw.strip(), "not a link"))
            continue

        try:
            vid = video_id_from(link)
            if kind is None:
                kind = "songs" if vid else "channels"

            if kind in ("songs", "scenes"):
                if not vid:
                    raise RuntimeError("this is not a video link (watch?v=..., youtu.be/..., shorts/...)")
                if vid in index[kind]:
                    if custom:
                        index[kind][vid]["title"] = custom
                else:
                    entry = {"title": custom or video_title(vid), "id": vid}
                    data[kind].append(entry)
                    index[kind][vid] = entry
            else:
                if vid:
                    raise RuntimeError("this is a video link; put it under [songs] or [scenes] instead")
                if "/playlist" in link:
                    raise RuntimeError("playlist links are not supported; use a channel or video link")
                cid, name = channel_from(link)
                if cid in index["channels"]:
                    if custom:
                        index["channels"][cid]["name"] = custom
                else:
                    entry = {"name": custom or name, "id": cid}
                    data["channels"].append(entry)
                    index["channels"][cid] = entry
        except Exception as e:
            failed.append((raw.strip(), str(e)))

    print("Channels: %d (was %d) | Songs: %d (was %d) | Scenes: %d (was %d) | Failed: %d" % (
        len(data["channels"]), before["channels"], len(data["songs"]), before["songs"],
        len(data["scenes"]), before["scenes"], len(failed)))
    for line, why in failed:
        print("  FAILED: %s  ->  %s" % (line, why))

    if wanted == 0:
        print("links.txt has no links. %s left unchanged." % dst)
        sys.exit(0)
    if len(failed) == wanted:
        print("Nothing could be resolved. Leaving %s unchanged." % dst)
        sys.exit(1)

    out = {"version": 1, "channels": data["channels"], "songs": data["songs"], "scenes": data["scenes"]}
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print("Wrote", dst)
    sys.exit(2 if failed else 0)


if __name__ == "__main__":
    main()
