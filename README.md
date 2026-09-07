# elizato-dl 🎵

A command-line tool that downloads YouTube Music playlists as MP3s (or FLAC, M4A, WAV, OPUS) with **full square album art**, **correct track numbers**, **metadata tags**, and **synced lyrics** — so your music library actually looks the way it's supposed to.

Made by **Elizato Winston** — first year Software Engineering student at the University of Buea 🇨🇲

---

## Why this exists

Every music downloader I tried either stripped the album art, lost the metadata or just dumped a messy pile of files on my laptop. As a graphic designer, that was unacceptable. So I built the solution myself.

---

## What's new in v1.3.0

- 🖼️ **High-resolution square album art** — no more stretched 16:9 thumbnails. Art is fetched at high-res and center-cropped square so it displays cleanly in every music app.
- 🔢 **Correct track numbers** — tracks are now numbered in the order they appear in the album/playlist, so your player sorts them the way the artist intended instead of alphabetically.
- 🎧 **Clean audio detection** — if a playlist track looks like an "official music video" upload (which can contain intros, skits or crowd noise), elizato-dl automatically looks for a clean official-audio version instead.
- 🍪 **Cookie freshness indicator** — the environment check now shows a clear ✅ when your cookies are still fresh, not just a warning when they've gone stale.

---

## Installation

```bash
pip install elizato-dl
```

> **Requirements:** Python 3.10+, [ffmpeg](https://ffmpeg.org/download.html) on your PATH

---

## Quick Start

```bash
# Download a playlist as MP3 with lyrics
elizato-dl download "https://music.youtube.com/playlist?list=PL..." --cookies cookies.txt --lyrics

# Download as FLAC
elizato-dl download "https://music.youtube.com/playlist?list=PL..." -f flac --cookies cookies.txt

# Save metadata to a manifest file first, then download
elizato-dl fetch "https://music.youtube.com/playlist?list=PL..." --cookies cookies.txt
elizato-dl download manifest.json --cookies cookies.txt --lyrics
```

---

## Cookie Setup (Required)

YouTube requires authentication to serve audio streams. You need to export your browser cookies:

1. Install the **[Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)** Chrome extension
2. Go to [youtube.com](https://youtube.com) while logged in
3. Click the extension → **Export** → save as `cookies.txt` in your working directory
4. Pass it with `--cookies cookies.txt`

> Cookies expire — if you get 403/429 errors or "Sign in to confirm you're not a bot", re-export them. elizato-dl will show you a ✅ if they're still fresh, or a ⚠️ if they've gone stale.

---

## Commands

### `download`
```
elizato-dl download <URL or manifest.json> [options]

Options:
  -o, --output DIR        Output directory (default: ./music)
  -f, --format FORMAT     Audio format: mp3, m4a, opus, flac, wav (default: mp3)
  --lyrics                Fetch and embed synced lyrics after download
  --no-thumbnail          Skip embedding album art
  --cookies FILE          Path to cookies.txt
  --browser BROWSER       Read cookies from browser (must be closed)
```

### `fetch`
```
elizato-dl fetch <URL> [options]

Options:
  -o, --output FILE       Output manifest file (default: manifest.json)
  --cookies FILE          Path to cookies.txt
```

---

## What you get

Each downloaded track includes:
- 🎵 Highest quality audio available
- 🖼️ High-resolution square album art embedded in the file
- 🔢 Correct track number matching album order
- 🏷️ Full metadata tags (artist, album, title, year)
- 📝 Synced lyrics embedded + `.lrc` file saved alongside (with `--lyrics`)
- 🎧 Clean audio automatically swapped in for tracks that look like music videos

---

## Support the project

If elizato-dl saved you time, feel free to donate:

**BTC (BEP20):** `0x0cEDD7d8f78B45fbA25B05Ada32eB37F7c193590`

---

## License

MIT — free to use, modify and distribute.
