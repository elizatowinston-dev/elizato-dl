#!/usr/bin/env python3
"""
elizato-dl — YouTube Music playlist downloader with lyrics
Made by Elizato Winston
"""

import argparse
import json
import platform
import re
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

from elizato_dl import __version__

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUPPORTED_FORMATS  = ("mp3", "m4a", "opus", "flac", "wav")
SUPPORTED_BROWSERS = ("chrome", "firefox", "edge", "safari", "brave", "opera")
LRCLIB_API         = "https://lrclib.net/api/search"
COOKIES_MAX_AGE_HOURS = 24
MIN_PYTHON         = (3, 10)
MIN_FREE_MB        = 500
DONATION_MSG = (
    "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "  elizato-dl  •  Made with ❤️  by Elizato Winston\n"
    "  Feel free to donate (BTC BEP20):\n"
    "  0x0cEDD7d8f78B45fbA25B05Ada32eB37F7c193590\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
)

# ---------------------------------------------------------------------------
# System detection helpers
# ---------------------------------------------------------------------------

def is_windows() -> bool:
    return platform.system() == "Windows"

def is_mac() -> bool:
    return platform.system() == "Darwin"

def is_linux() -> bool:
    return platform.system() == "Linux"

def run_silent(cmd: list) -> bool:
    """Run a command, return True if it succeeded."""
    try:
        result = subprocess.run(cmd, capture_output=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def run_visible(cmd: list) -> bool:
    """Run a command with visible output, return True if succeeded."""
    try:
        result = subprocess.run(cmd)
        return result.returncode == 0
    except FileNotFoundError:
        return False

# ---------------------------------------------------------------------------
# Internet check
# ---------------------------------------------------------------------------

def check_internet() -> bool:
    try:
        socket.setdefaulttimeout(5)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
        return True
    except Exception:
        return False

# ---------------------------------------------------------------------------
# Disk space check
# ---------------------------------------------------------------------------

def check_disk_space(path: Path) -> float:
    """Return free disk space in MB for the given path."""
    try:
        usage = shutil.disk_usage(path)
        return usage.free / (1024 * 1024)
    except Exception:
        return float("inf")

# ---------------------------------------------------------------------------
# Auto-install helpers
# ---------------------------------------------------------------------------

def install_pip_package(package: str) -> bool:
    print(f"  📦 Installing {package}...")
    return run_visible([sys.executable, "-m", "pip", "install", "--upgrade", package, "-q"])

def install_ffmpeg() -> bool:
    print("  📦 Installing ffmpeg...")
    if is_windows():
        if shutil.which("winget"):
            return run_visible(["winget", "install", "ffmpeg", "--accept-source-agreements", "--accept-package-agreements"])
        else:
            return False
    elif is_mac():
        if shutil.which("brew"):
            return run_visible(["brew", "install", "ffmpeg"])
        else:
            return False
    elif is_linux():
        return run_visible(["sudo", "apt", "install", "-y", "ffmpeg"])
    return False

def install_nodejs() -> bool:
    print("  📦 Installing Node.js...")
    if is_windows():
        if shutil.which("winget"):
            return run_visible(["winget", "install", "OpenJS.NodeJS.LTS", "--accept-source-agreements", "--accept-package-agreements"])
        else:
            return False
    elif is_mac():
        if shutil.which("brew"):
            return run_visible(["brew", "install", "node"])
        else:
            return False
    elif is_linux():
        return run_visible(["sudo", "apt", "install", "-y", "nodejs", "npm"])
    return False

def cache_ejs_solver():
    """Pre-cache the EJS JS challenge solver from GitHub."""
    print("  🔧 Caching YouTube JS challenge solver (one-time setup)...")
    run_visible([
        sys.executable, "-m", "yt_dlp",
        "--remote-components", "ejs:github",
        "--skip-download",
        "https://www.youtube.com/watch?v=jNQXAC9IVRw"
    ])

# ---------------------------------------------------------------------------
# Full environment setup — runs before every command
# ---------------------------------------------------------------------------

def setup_environment(output_dir: Path = None):
    """
    Check and auto-fix all dependencies before running.
    Exits with a clear message if anything can't be fixed automatically.
    """
    print("\n🔍 Checking your environment...\n")
    all_good = True

    # --- Python version ---
    if sys.version_info < MIN_PYTHON:
        print(f"  ❌ Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ required. You have {platform.python_version()}.")
        print(f"     Please download the latest Python from https://python.org/downloads")
        print(f"     (We can't auto-update Python safely as it may break your system)\n")
        all_good = False
    else:
        print(f"  ✅ Python {platform.python_version()}")

    # --- Internet connection ---
    if not check_internet():
        print("  ❌ No internet connection detected. Please connect and try again.")
        sys.exit(1)
    else:
        print("  ✅ Internet connection")

    # --- Disk space ---
    check_path = output_dir or Path(".")
    free_mb = check_disk_space(check_path)
    if free_mb < MIN_FREE_MB:
        print(f"  ⚠️  Low disk space: {free_mb:.0f}MB free. At least {MIN_FREE_MB}MB recommended.")
        print(f"     Free up some space before downloading a large playlist.\n")
        all_good = False
    else:
        print(f"  ✅ Disk space ({free_mb:.0f}MB free)")

    # --- yt-dlp ---
    try:
        import yt_dlp
        # Check for updates
        print("  🔄 Checking yt-dlp for updates...")
        install_pip_package("yt-dlp")
        print("  ✅ yt-dlp (up to date)")
    except ImportError:
        print("  ⚠️  yt-dlp not found. Installing...")
        if install_pip_package("yt-dlp"):
            print("  ✅ yt-dlp installed!")
        else:
            print("  ❌ Failed to install yt-dlp. Run: pip install yt-dlp")
            all_good = False

    # --- mutagen ---
    try:
        import mutagen  # noqa: F401
        print("  ✅ mutagen")
    except ImportError:
        print("  ⚠️  mutagen not found. Installing...")
        if install_pip_package("mutagen"):
            print("  ✅ mutagen installed!")
        else:
            print("  ❌ Failed to install mutagen. Run: pip install mutagen")
            all_good = False

    # --- requests ---
    try:
        import requests  # noqa: F401
        print("  ✅ requests")
    except ImportError:
        print("  ⚠️  requests not found. Installing...")
        if install_pip_package("requests"):
            print("  ✅ requests installed!")
        else:
            print("  ❌ Failed to install requests. Run: pip install requests")
            all_good = False

    # --- ffmpeg ---
    ffmpeg_ok = shutil.which("ffmpeg") is not None and run_silent(["ffmpeg", "-version"])
    if ffmpeg_ok:
        print("  ✅ ffmpeg")
    else:
        print("  ⚠️  ffmpeg not found. Attempting auto-install...")
        if install_ffmpeg():
            # Re-check after install
            if shutil.which("ffmpeg") is not None:
                print("  ✅ ffmpeg installed!")
            else:
                print("  ⚠️  ffmpeg installed but not on PATH yet.")
                print("     Please restart your terminal and run the command again.")
                all_good = False
        else:
            print("  ❌ Could not auto-install ffmpeg.")
            if is_windows():
                print("     Install manually: winget install ffmpeg")
                print("     Or download from: https://ffmpeg.org/download.html")
            elif is_mac():
                print("     Install manually: brew install ffmpeg")
                print("     Or download from: https://ffmpeg.org/download.html")
            else:
                print("     Install manually: sudo apt install ffmpeg")
            all_good = False

    # --- Node.js ---
    node_ok = shutil.which("node") is not None and run_silent(["node", "--version"])
    if node_ok:
        node_ver = subprocess.run(["node", "--version"], capture_output=True, text=True).stdout.strip()
        print(f"  ✅ Node.js {node_ver}")
    else:
        print("  ⚠️  Node.js not found. Attempting auto-install...")
        if install_nodejs():
            if shutil.which("node") is not None:
                print("  ✅ Node.js installed!")
            else:
                print("  ⚠️  Node.js installed but not on PATH yet.")
                print("     Please restart your terminal and run the command again.")
                all_good = False
        else:
            print("  ❌ Could not auto-install Node.js.")
            print("     Install manually from: https://nodejs.org (LTS version)")
            all_good = False

    # --- EJS solver cache ---
    if node_ok:
        ejs_cache = _find_ejs_cache()
        if ejs_cache:
            print("  ✅ YouTube JS challenge solver (cached)")
        else:
            print("  ⚠️  YouTube JS challenge solver not cached. Running one-time setup...")
            cache_ejs_solver()
            print("  ✅ JS challenge solver cached!")

    if not all_good:
        print("\n❌ Some issues need to be fixed before continuing.")
        print("   Please address the errors above, restart your terminal and try again.\n")
        sys.exit(1)

    print("\n✅ All checks passed! Starting...\n")

def _find_ejs_cache() -> bool:
    """Check if the EJS solver script is already cached by yt-dlp."""
    try:
        if is_windows():
            cache_dirs = [
                Path.home() / "AppData" / "Local" / "yt-dlp",
                Path.home() / "AppData" / "Roaming" / "yt-dlp",
            ]
        elif is_mac():
            cache_dirs = [Path.home() / "Library" / "Caches" / "yt-dlp"]
        else:
            cache_dirs = [Path.home() / ".cache" / "yt-dlp"]

        for d in cache_dirs:
            if d.exists():
                for f in d.rglob("*.js"):
                    if "solver" in f.name.lower() or "yt" in f.name.lower():
                        return True
        return False
    except Exception:
        return False

# ---------------------------------------------------------------------------
# Cookies validation
# ---------------------------------------------------------------------------

def validate_cookies(cookies_file: str = None) -> str:
    """
    Find and validate the cookies file.
    If no path given, look for cookies.txt in the current directory.
    Returns the path if valid, exits with instructions if not.
    """
    # If user didn't specify, look in current directory
    if not cookies_file:
        default = Path("cookies.txt")
        if default.exists():
            cookies_file = str(default)
            print(f"  🍪 Found cookies.txt in current directory")
        else:
            print("\n⚠️  No cookies file found!\n")
            print("  elizato-dl needs your YouTube cookies to download music.")
            print("  Here's how to get them:\n")
            print("  1. Open Chrome and go to youtube.com (make sure you're logged in)")
            print("  2. Install this extension: https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc")
            print("  3. Click the extension icon → Export → save as 'cookies.txt'")
            print(f"  4. Save cookies.txt in this folder: {Path('.').resolve()}")
            print("  5. Run your command again\n")
            print("  Then run:")
            print("  elizato-dl download \"YOUR_PLAYLIST_URL\" --cookies cookies.txt\n")
            sys.exit(1)

    path = Path(cookies_file)

    # Check file exists
    if not path.exists():
        print(f"\n❌ Cookies file not found: {path}")
        print(f"   Make sure the file is named exactly 'cookies.txt'")
        print(f"   and is saved in: {Path('.').resolve()}\n")
        sys.exit(1)

    # Check file is not empty
    if path.stat().st_size == 0:
        print(f"\n❌ cookies.txt is empty. Please re-export it from your browser.\n")
        sys.exit(1)

    # Check filename
    if path.name != "cookies.txt":
        print(f"\n⚠️  Your cookies file is named '{path.name}'.")
        print(f"   We recommend naming it exactly 'cookies.txt' to avoid confusion.\n")

    # Check age
    age_hours = (time.time() - path.stat().st_mtime) / 3600
    if age_hours > COOKIES_MAX_AGE_HOURS:
        print(f"\n⚠️  cookies.txt is {age_hours:.0f} hours old.")
        print("   YouTube cookies expire. If downloads fail with 403 errors,")
        print("   re-export a fresh cookies.txt from your browser.\n")

    return str(path)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_url(value: str) -> bool:
    return bool(re.match(r"^https?://", value.strip(), re.IGNORECASE))

def normalise_url(url: str) -> str:
    return url.strip()

def safe_json_load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"ERROR: {path} is not valid JSON — {e}", file=sys.stderr)
        sys.exit(1)

# ---------------------------------------------------------------------------
# Lyrics — lrclib.net (free, no API key needed)
# ---------------------------------------------------------------------------

def fetch_lyrics(title: str, artist: str):
    if not title:
        return None, None
    try:
        import requests
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

    except Exception as e:
        print(f"  ⚠️  Lyrics fetch failed for '{title}': {e}")
        return None, None


def embed_lyrics_mp3(filepath: Path, lyrics_text: str):
    try:
        from mutagen.mp3 import MP3
        from mutagen.id3 import ID3, USLT, error as ID3Error
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
    from yt_dlp import YoutubeDL
    ydl_opts = {
        "quiet":        True,
        "no_warnings":  True,
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
    output_dir = Path(".")
    setup_environment(output_dir)

    url          = normalise_url(args.source)
    cookies_file = validate_cookies(args.cookies)

    print(f"Fetching playlist metadata from:\n  {url}\n")
    data = extract_playlist_metadata(url, browser=args.browser, cookies_file=cookies_file)

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
        "--format",             "bestaudio/best",
        "--extract-audio",
        "--audio-format",       fmt,
        "--audio-quality",      "0",
        "--add-metadata",
        "--output",             str(output_dir / "%(artist,uploader)s - %(title)s.%(ext)s"),
        "--extractor-args",     "youtube:player_client=android_vr;player_skip=web_music",
        "--remote-components",  "ejs:github",
        "--sleep-interval",     "5",
        "--max-sleep-interval", "10",
        "--retries",            "10",
        "--fragment-retries",   "10",
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

    # Run full environment setup
    setup_environment(output_dir)

    fmt = args.format.lower()
    if fmt not in SUPPORTED_FORMATS:
        print(f"ERROR: Unsupported format '{fmt}'. Choose from: {', '.join(SUPPORTED_FORMATS)}", file=sys.stderr)
        sys.exit(1)

    # Validate cookies
    cookies_file = validate_cookies(args.cookies)
    print(f"  🍪 Using cookies: {cookies_file}\n")

    # Resolve source
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

    # Disk space warning based on track count
    estimated_mb = len(urls) * 8 if urls else 0
    free_mb      = check_disk_space(output_dir)
    if estimated_mb > 0 and free_mb < estimated_mb:
        print(f"\n⚠️  Estimated download size: ~{estimated_mb}MB")
        print(f"   Free space available: {free_mb:.0f}MB")
        print("   You may run out of disk space during download.\n")

    embed_thumbnail = not args.no_thumbnail
    print(f"Output folder : {output_dir.resolve()}")
    print(f"Format        : {fmt.upper()}")
    print(f"Embed artwork : {'yes' if embed_thumbnail else 'no'}")
    print(f"Lyrics        : {'yes' if args.lyrics else 'no'}\n")

    cmd    = build_ytdlp_cmd(urls, output_dir, fmt, embed_thumbnail, args.browser, cookies_file)
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
Examples:
  elizato-dl download "https://music.youtube.com/playlist?list=PL..." --cookies cookies.txt --lyrics
  elizato-dl download "https://music.youtube.com/playlist?list=PL..." -f flac -o ~/Music --cookies cookies.txt
  elizato-dl fetch "https://music.youtube.com/playlist?list=PL..." --cookies cookies.txt
  elizato-dl download manifest.json --cookies cookies.txt --lyrics

Cookies:
  Export cookies.txt using "Get cookies.txt LOCALLY" Chrome extension from youtube.com
  Save it in the same folder where you run the command.
        """,
    )

    parser.add_argument("--version", action="version", version=f"elizato-dl {__version__}")

    sub = parser.add_subparsers(dest="command", required=True)

    def add_cookie_args(p):
        group = p.add_mutually_exclusive_group()
        group.add_argument("--browser", choices=SUPPORTED_BROWSERS, default=None, metavar="BROWSER",
                           help=f"Read cookies from browser (must be closed): {', '.join(SUPPORTED_BROWSERS)}")
        group.add_argument("--cookies", default=None, metavar="FILE",
                           help="Path to cookies.txt exported from browser (default: looks for cookies.txt in current folder)")

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