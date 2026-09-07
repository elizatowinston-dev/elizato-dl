#!/usr/bin/env python3
"""
elizato-dl — YouTube Music playlist downloader with lyrics
Made by Elizato Winston
"""

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

from elizato_dl import __version__


# ---------------------------------------------------------------------------
# Dependency checks — fail early with clear messages
# ---------------------------------------------------------------------------

def check_dependencies():
    errors = []

    try:
        from yt_dlp import YoutubeDL  # noqa: F401
    except ImportError:
        errors.append("yt-dlp is not installed. Run: pip install yt-dlp")

    try:
        import mutagen  # noqa: F401
    except ImportError:
        errors.append("mutagen is not installed. Run: pip install mutagen")

    try:
        import requests  # noqa: F401
    except ImportError:
        errors.append("requests is not installed. Run: pip install requests")

    result = subprocess.run(["ffmpeg", "-version"], capture_output=True)
    if result.returncode != 0:
        errors.append(
            "ffmpeg is not installed or not on PATH.\n"
            "  Windows : winget install ffmpeg  OR  https://ffmpeg.org/download.html\n"
            "  macOS   : brew install ffmpeg\n"
            "  Linux   : sudo apt install ffmpeg"
        )

    if errors:
        print("\n❌ Missing dependencies:\n")
        for e in errors:
            print(f"  • {e}")
        print()
        sys.exit(1)


check_dependencies()

import requests
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, USLT, error as ID3Error
from yt_dlp import YoutubeDL


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUPPORTED_FORMATS  = ("mp3", "m4a", "opus", "flac", "wav")
SUPPORTED_BROWSERS = ("chrome", "firefox", "edge", "safari", "brave", "opera")
LRCLIB_API         = "https://lrclib.net/api/search"
COOKIES_MAX_AGE_HOURS = 24
DONATION_MSG = (
    "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "  elizato-dl  •  Made with ❤️  by Elizato Winston\n"
    "  Feel free to donate (BTC BEP20):\n"
    "  0x0cEDD7d8f78B45fbA25B05Ada32eB37F7c193590\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_url(value: str) -> bool:
    return bool(re.match(r"^https?://", value.strip(), re.IGNORECASE))


def normalise_url(url: str) -> str:
    return url.strip()


def warn_if_cookies_stale(cookies_file: str):
    path = Path(cookies_file)
    if not path.exists():
        return
    age_hours = (time.time() - path.stat().st_mtime) / 3600
    if age_hours > COOKIES_MAX_AGE_HOURS:
        print(
            f"⚠️  WARNING: cookies.txt is {age_hours:.0f} hours old. "
            "If downloads fail with 403 errors, re-export your cookies.\n"
        )


def safe_json_load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"ERROR: {path} is not valid JSON — {e}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Lyrics — lrclib.net (free, no API key needed)
# ---------------------------------------------------------------------------

def fetch_lyrics(title: str, artist: str) -> tuple:
    if not title:
        return None, None
    try:
        params = {"q": f"{artist or ''} {title}".strip()}
        resp   = requests.get(LRCLIB_API, params=params, timeout=10)
        resp.raise_for_status()
        results = resp.json()
        if not results:
            return None, None

        best        = None
        title_lower = title.lower()
        for r in results:
            if r.get("trackName", "").lower() == title_lower:
                best = r
                break
        if not best:
            best = results[0]

        return best.get("syncedLyrics"), best.get("plainLyrics")

    except requests.RequestException as e:
        print(f"  ⚠️  Lyrics fetch failed for '{title}': {e}")
        return None, None
    except (ValueError, KeyError):
        return None, None


def embed_lyrics_mp3(filepath: Path, lyrics_text: str):
    try:
        audio = MP3(filepath, ID3=ID3)
        try:
            audio.add_tags()
        except ID3Error:
            pass
        audio.tags.add(USLT(encoding=3, lang="eng", desc="Lyrics", text=lyrics_text))
        audio.save()
    except Exception as e:
        print(f"  ⚠️  Could not embed lyrics into {filepath.name}: {e}")


def write_lrc_file(audio_path: Path, lrc_content: str):
    try:
        audio_path.with_suffix(".lrc").write_text(lrc_content, encoding="utf-8")
    except Exception as e:
        print(f"  ⚠️  Could not write .lrc file: {e}")


def process_lyrics_for_folder(output_dir: Path, entries: list):
    print("\n🎵 Fetching lyrics...\n")

    audio_files = []
    for fmt in SUPPORTED_FORMATS:
        audio_files += list(output_dir.glob(f"*.{fmt}"))

    if not audio_files:
        print("  No audio files found to add lyrics to.")
        return

    success = 0
    failed  = 0

    for audio_file in sorted(audio_files):
        stem   = audio_file.stem
        title  = stem
        artist = ""

        for entry in entries or []:
            entry_title  = entry.get("title") or ""
            entry_artist = entry.get("artist") or ""
            if entry_title and entry_title.lower() in stem.lower():
                title  = entry_title
                artist = entry_artist
                break

        print(f"  🔍 {audio_file.name}")
        synced, plain = fetch_lyrics(title, artist)

        if not synced and not plain:
            print("       ❌ No lyrics found")
            failed += 1
            continue

        lyrics_text = synced or plain

        if audio_file.suffix.lower() == ".mp3":
            embed_lyrics_mp3(audio_file, lyrics_text)

        if synced:
            write_lrc_file(audio_file, synced)
            print("       ✅ Synced lyrics embedded + .lrc saved")
        else:
            print("       ✅ Plain lyrics embedded (no synced version available)")

        success += 1

    print(f"\n  Lyrics done — {success} added, {failed} not found.\n")


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------

def extract_playlist_metadata(url: str, browser: str = None, cookies_file: str = None) -> dict:
    ydl_opts = {
        "quiet":       True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": "in_playlist",
        "extractor_args": {
            "youtube": {
                "player_client": ["android_vr"],
                "player_skip":   ["web_music"],
            }
        },
    }
    if cookies_file:
        ydl_opts["cookiefile"] = cookies_file
    elif browser:
        ydl_opts["cookiesfrombrowser"] = (browser,)

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        print(f"ERROR: Failed to fetch playlist — {e}", file=sys.stderr)
        sys.exit(1)

    if not info:
        print("ERROR: Could not retrieve playlist info. Check the URL.", file=sys.stderr)
        sys.exit(1)

    entries = info.get("entries") or []
    if not entries:
        print("WARNING: Playlist appears to be empty or all tracks are unavailable.")

    playlist = {
        "playlist_title": info.get("title"),
        "playlist_id":    info.get("id"),
        "playlist_url":   info.get("webpage_url") or url,
        "entries": [],
    }

    for entry in entries:
        if not entry:
            continue
        playlist["entries"].append({
            "id":          entry.get("id"),
            "title":       entry.get("title"),
            "artist":      entry.get("artist") or entry.get("uploader"),
            "album":       entry.get("album"),
            "track":       entry.get("track"),
            "webpage_url": entry.get("url") or entry.get("webpage_url"),
            "thumbnail":   entry.get("thumbnail"),
            "duration":    entry.get("duration"),
            "release_year":entry.get("release_year"),
        })

    return playlist


def cmd_fetch(args):
    url = normalise_url(args.source)

    if args.cookies:
        if not Path(args.cookies).exists():
            print(f"ERROR: Cookies file not found: {args.cookies}", file=sys.stderr)
            sys.exit(1)
        warn_if_cookies_stale(args.cookies)

    print(f"Fetching playlist metadata from:\n  {url}\n")
    data = extract_playlist_metadata(url, browser=args.browser, cookies_file=args.cookies)

    out_path = Path(args.output)
    out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Playlist : {data['playlist_title']}")
    print(f"Tracks   : {len(data['entries'])}")
    print(f"Manifest : {out_path}")
    print(DONATION_MSG)


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

def build_ytdlp_cmd(urls: list, output_dir: Path, fmt: str,
                    embed_thumbnail: bool, browser: str, cookies_file: str) -> list:
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--format",            "bestaudio/best",
        "--extract-audio",
        "--audio-format",      fmt,
        "--audio-quality",     "0",
        "--add-metadata",
        "--output",            str(output_dir / "%(artist,uploader)s - %(title)s.%(ext)s"),
        "--extractor-args",    "youtube:player_client=android_vr;player_skip=web_music",
        "--remote-components", "ejs:github",
        "--sleep-interval",    "5",
        "--max-sleep-interval","10",
        "--retries",           "10",
        "--fragment-retries",  "10",
        "--ignore-errors",
    ]

    if embed_thumbnail:
        cmd += ["--embed-thumbnail", "--write-thumbnail"]

    if cookies_file:
        cmd += ["--cookies", cookies_file]
    elif browser:
        cmd += ["--cookies-from-browser", browser]

    cmd += urls
    return cmd


def cmd_download(args):
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    fmt = args.format.lower()
    if fmt not in SUPPORTED_FORMATS:
        print(f"ERROR: Unsupported format '{fmt}'. Choose from: {', '.join(SUPPORTED_FORMATS)}", file=sys.stderr)
        sys.exit(1)

    if args.cookies:
        if not Path(args.cookies).exists():
            print(f"ERROR: Cookies file not found: {args.cookies}", file=sys.stderr)
            sys.exit(1)
        warn_if_cookies_stale(args.cookies)
        print(f"Using cookies file : {args.cookies}")
    elif args.browser:
        print(f"Using cookies from : {args.browser}")

    entries = []
    if is_url(args.source):
        urls = [normalise_url(args.source)]
        print(f"Downloading from URL:\n  {args.source}\n")
    else:
        manifest_path = Path(args.source)
        if not manifest_path.exists():
            print(f"ERROR: Manifest file not found: {manifest_path}", file=sys.stderr)
            sys.exit(1)
        data    = safe_json_load(manifest_path)
        entries = data.get("entries") or []
        urls    = [e["webpage_url"] for e in entries if e.get("webpage_url")]

        if not urls:
            print("ERROR: No downloadable tracks found in manifest.", file=sys.stderr)
            sys.exit(1)

        print(f"Playlist      : {data.get('playlist_title', 'Unknown')}")
        print(f"Tracks        : {len(urls)}")

    embed_thumbnail = not args.no_thumbnail
    print(f"Output folder : {output_dir}")
    print(f"Format        : {fmt.upper()}")
    print(f"Embed artwork : {'yes' if embed_thumbnail else 'no'}")
    print(f"Lyrics        : {'yes' if args.lyrics else 'no'}\n")

    cmd    = build_ytdlp_cmd(urls, output_dir, fmt, embed_thumbnail, args.browser, args.cookies)
    result = subprocess.run(cmd)

    if result.returncode == 0:
        print(f"\n✅ Download complete! Files saved to: {output_dir.resolve()}")
    else:
        print(f"\n⚠️  Finished with some errors (exit code {result.returncode}).")
        print(f"   Successfully downloaded files are in: {output_dir.resolve()}")

    if args.lyrics:
        process_lyrics_for_folder(output_dir, entries)

    print(DONATION_MSG)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        prog="elizato-dl",
        description=f"elizato-dl v{__version__} — YouTube Music playlist downloader by Elizato Winston",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Cookie options (pick one):
  --cookies cookies.txt   Recommended. Export via "Get cookies.txt LOCALLY" Chrome extension.
  --browser chrome        Browser must be fully closed when using this option.

Examples:
  elizato-dl download "https://music.youtube.com/playlist?list=PL..." --cookies cookies.txt --lyrics
  elizato-dl download "https://music.youtube.com/playlist?list=PL..." -f flac -o ~/Music --cookies cookies.txt
  elizato-dl fetch "https://music.youtube.com/playlist?list=PL..." --cookies cookies.txt
  elizato-dl download manifest.json --cookies cookies.txt --lyrics
        """,
    )

    parser.add_argument("--version", action="version", version=f"elizato-dl {__version__}")

    sub = parser.add_subparsers(dest="command", required=True)

    def add_cookie_args(p):
        group = p.add_mutually_exclusive_group()
        group.add_argument("--browser", choices=SUPPORTED_BROWSERS, default=None, metavar="BROWSER",
                           help=f"Read cookies from browser (must be closed): {', '.join(SUPPORTED_BROWSERS)}")
        group.add_argument("--cookies", default=None, metavar="FILE",
                           help="Path to cookies.txt exported from browser")

    # fetch
    p_fetch = sub.add_parser("fetch", help="Extract playlist metadata to a JSON manifest")
    p_fetch.add_argument("source", help="YouTube Music playlist URL")
    p_fetch.add_argument("-o", "--output", default="manifest.json")
    add_cookie_args(p_fetch)

    # download
    p_dl = sub.add_parser("download", help="Download audio tracks")
    p_dl.add_argument("source", help="YouTube Music URL  OR  path to manifest.json")
    p_dl.add_argument("-o", "--output", default="./music")
    p_dl.add_argument("-f", "--format", default="mp3", choices=SUPPORTED_FORMATS, metavar="FORMAT",
                      help=f"Audio format: {', '.join(SUPPORTED_FORMATS)}  (default: mp3)")
    p_dl.add_argument("--lyrics", action="store_true",
                      help="Fetch and embed lyrics after download")
    p_dl.add_argument("--no-thumbnail", action="store_true",
                      help="Do not embed album art")
    add_cookie_args(p_dl)

    args = parser.parse_args()

    if args.command == "fetch":
        cmd_fetch(args)
    elif args.command == "download":
        cmd_download(args)


if __name__ == "__main__":
    main()
