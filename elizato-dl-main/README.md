# elizato-dl 🎵

A command-line tool that downloads YouTube Music playlists as MP3s (or FLAC, M4A, WAV, OPUS) with **full album art**, **metadata tags**, and **synced lyrics** — so your music library actually looks the way it's supposed to.

Made by **Elizato Winston** — first year Software Engineering student at the University of Buea 🇨🇲

---

## Why this exists

Every music downloader I tried either stripped the album art, lost the metadata or just dumped a messy pile of files on my laptop. As a graphic designer, that was unacceptable. So I built the solution myself.

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

> Cookies expire — if you get 403 errors, re-export them.

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
- 🖼️  Album art embedded in the file
- 🏷️  Full metadata tags (artist, album, title, year)
- 📝 Synced lyrics embedded + `.lrc` file saved alongside (with `--lyrics`)

---

## Support the project

If elizato-dl saved you time, feel free to donate:

**BTC (BEP20):** `0x0cEDD7d8f78B45fbA25B05Ada32eB37F7c193590`

---

## License

MIT — free to use, modify and distribute.
