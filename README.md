# Jay-YT-TV

A locked-down YouTube player for Android TV. It shows **only** the channels and songs listed in
[`channels.json`](channels.json). No search, no Home or Trending, no recommendations.

## Credits

This project is a modified version of **[SmartTube](https://github.com/yuliskov/SmartTube)** by
**[yuliskov](https://github.com/yuliskov)** and its contributors. All the hard work of talking to YouTube and
playing video on Android TV is theirs. Please support the original project.

SmartTube is released under the MIT License. Its license and copyright notice are kept in [LICENSE](LICENSE).
This project is not affiliated with or endorsed by SmartTube's author or by YouTube.

## What was changed

- Sidebar shows only a Songs list and the channels from `channels.json`
- Search (text and voice) removed
- Recommendations and autoplay into other videos removed
- Videos play only if their channel or video ID is on the list
- Builds and updates come from this repository's GitHub Releases

## Using it

1. Edit `channels.json` (channel IDs start with `UC`; song IDs are the 11 characters after `v=` in a video link).
2. Push to GitHub. Editing only `channels.json` needs no rebuild; the TV reads it on every start.
3. Code changes build a signed APK automatically (Actions tab), published under Releases.
4. Full setup steps: see [KIDTUBE_README.md](KIDTUBE_README.md).

## Disclaimer

Personal, non-commercial use. Unofficial YouTube clients may go against YouTube's terms of service.
Use at your own risk.
