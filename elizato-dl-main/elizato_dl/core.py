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
            # Lyrics are now embedded in the file itself — no need for a
            # separate .lrc file cluttering the folder.
            if synced:
                print("       ✅ Synced lyrics embedded into MP3")
            else:
                print("       ✅ Plain lyrics embedded into MP3 (no synced version available)")
        else:
            # Other formats (flac, m4a, wav, opus) don't get lyrics embedded
            # by this tool, so the .lrc file is the only way to have lyrics —
            # keep it.
            if synced:
                write_lrc_file(audio_file, synced)
                print("       ✅ Synced .lrc file saved")
            else:
                write_lrc_file(audio_file, plain)
                print("       ✅ Plain .lrc file saved (no synced version available)")

        success += 1

    print(f"\n  Lyrics done — {success} added, {failed} not found.\n")


def cleanup_stray_files(output_dir: Path):
    """
    Remove leftover thumbnail images and any orphaned .lrc files whose
    matching audio file no longer exists (e.g. from a previous failed run).
    """
    removed = 0

    # Leftover thumbnail images (jpg/jpeg/png/webp) sitting loose in the folder
    for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
        for img in output_dir.glob(ext):
            try:
                img.unlink()
                removed += 1
            except Exception:
                pass

    # Orphaned .lrc files with no matching audio file
    for lrc in output_dir.glob("*.lrc"):
        has_audio = any(
            lrc.with_suffix(f".{fmt}").exists() for fmt in SUPPORTED_FORMATS
        )
        if not has_audio:
            try:
                lrc.unlink()
                removed += 1
            except Exception:
                pass

    if removed:
        print(f"🧹 Cleaned up {removed} leftover file(s) (thumbnails/orphaned lyrics)\n")

# ---------------------------------------------------------------------------
# High-resolution square album art
# ---------------------------------------------------------------------------

def fetch_highres_square_thumbnail(webpage_url: str) -> str:
    """
    YouTube Music album/track pages expose a higher-resolution SQUARE
    thumbnail (hosted on lh3.googleusercontent.com, usually 544x544 or
    larger) via the page's og:image meta tag. This is better than the
    default 16:9 padded thumbnail yt-dlp normally grabs.

    Returns the high-res square image URL if found, else None.
    """
    try:
        import requests
        # Make sure we're hitting the music.youtube.com page, since that's
        # the one that carries the square og:image variant.
        music_url = webpage_url
        if "music.youtube.com" not in music_url:
            match = re.search(r"[?&]v=([\w-]{11})", music_url)
            if match:
                music_url = f"https://music.youtube.com/watch?v={match.group(1)}"

        resp = requests.get(music_url, timeout=10, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        })
        resp.raise_for_status()
        html = resp.text

        match = re.search(r'<meta property="og:image" content="([^"]+)"', html)
        if not match:
            return None

        image_url = match.group(1)

        # googleusercontent URLs support a size suffix like "=w544-h544"
        # append/replace it to request the largest square crop available.
        image_url = re.sub(r"=w\d+-h\d+.*$", "", image_url)
        if "googleusercontent.com" in image_url:
            image_url += "=w1200-h1200"

        return image_url
    except Exception:
        return None


def download_thumbnail_file(image_url: str, dest_path: Path) -> bool:
    """Download a thumbnail image to disk. Returns True on success."""
    try:
        import requests
        resp = requests.get(image_url, timeout=15)
        resp.raise_for_status()
        dest_path.write_bytes(resp.content)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Audio-only vs music-video detection
# ---------------------------------------------------------------------------

VIDEO_HINT_PATTERNS = (
    "official video", "official music video", "music video",
    "(video)", "[video]", "official mv", " mv)", " mv]",
)

AUDIO_HINT_PATTERNS = (
    "official audio", "audio)", "audio]", "lyric video", "lyrics)",
    "topic", "visualizer",
)


def looks_like_video_upload(title: str) -> bool:
    """Heuristic: does this title look like an official music VIDEO
    (as opposed to a clean audio-only upload)?"""
    if not title:
        return False
    t = title.lower()
    if any(hint in t for hint in AUDIO_HINT_PATTERNS):
        return False
    return any(hint in t for hint in VIDEO_HINT_PATTERNS)


def find_clean_audio_match(title: str, artist: str, cookies_file: str, browser: str):
    """
    Search YouTube Music (audio-first catalog) for a clean "official audio"
    upload of the given title/artist, to use instead of a music-video
    upload that may contain intros, skits, or crowd noise.

    Returns a webpage_url string if a good match is found, else None.
    """
    if not title:
        return None
    try:
        from yt_dlp import YoutubeDL
        query = f"{artist or ''} {title}".strip()
        search_term = f"ytsearch5:{query}"

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": "in_playlist",
            "extractor_args": {
                "youtube": {
                    "player_client": ["android_vr"],
                    "player_skip": ["web_music"],
                }
            },
        }
        if cookies_file:
            ydl_opts["cookiefile"] = cookies_file
        elif browser:
            ydl_opts["cookiesfrombrowser"] = (browser,)

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_term, download=False)

        candidates = (info or {}).get("entries") or []
        title_lower = title.lower()

        for cand in candidates:
            if not cand:
                continue
            cand_title = (cand.get("title") or "").lower()
            # Skip anything that itself looks like a video upload
            if looks_like_video_upload(cand_title):
                continue
            # Must still clearly be the same song
            if title_lower[:15] not in cand_title:
                continue
            return cand.get("url") or cand.get("webpage_url")

        return None
    except Exception:
        return None


def resolve_clean_audio_urls(entries: list, cookies_file: str, browser: str) -> list:
    """
    Given manifest entries, check each for a "looks like a music video"
    title, and if so, try to swap in a clean official-audio version found
    via YouTube Music search. Falls back to the original if no match found,
    printing a note either way.

    Returns the (possibly modified) list of webpage URLs to download, in
    the same order as entries.
    """
    resolved_urls = []
    swapped = 0
    flagged = 0

    print("\n🎧 Checking tracks for music-video vs clean-audio versions...\n")

    for entry in entries:
        title  = entry.get("title") or ""
        artist = entry.get("artist") or ""
        original_url = entry.get("webpage_url")

        if looks_like_video_upload(title):
            clean_url = find_clean_audio_match(title, artist, cookies_file, browser)
            if clean_url and clean_url != original_url:
                print(f"  🔁 '{title}' looked like a music video — swapped in a clean audio version")
                resolved_urls.append(clean_url)
                swapped += 1
                continue
            else:
                print(f"  ⚠️  '{title}' looks like a music video, but no clean audio version was found — using original")
                flagged += 1

        resolved_urls.append(original_url)

    if swapped or flagged:
        print(f"\n  Done — {swapped} swapped to clean audio, {flagged} kept as-is (no clean version found).\n")

    return resolved_urls

def upgrade_artwork_to_highres(output_dir: Path, entries: list, fmt: str):
    """
    After download, try to replace each file's embedded album art with the
    higher-resolution SQUARE version fetched from YouTube Music directly
    (see fetch_highres_square_thumbnail). If that can't be found for a
    track, its existing center-cropped square thumbnail (from the yt-dlp
    postprocessor) is left as-is — still square, just standard resolution.
    """
    print("\n🖼️  Upgrading album art to high-res square where possible...\n")

    audio_files = []
    for f in SUPPORTED_FORMATS:
        audio_files += list(output_dir.glob(f"*.{f}"))

    if not audio_files or not entries:
        return

    upgraded = 0
    skipped  = 0

    for audio_file in audio_files:
        stem = audio_file.stem.lower()
        match = None
        for entry in entries:
            title = (entry.get("title") or "").lower()
            if title and title in stem:
                match = entry
                break

        if not match or not match.get("webpage_url"):
            skipped += 1
            continue

        image_url = fetch_highres_square_thumbnail(match["webpage_url"])
        if not image_url:
            skipped += 1
            continue

        temp_img = output_dir / f".__art_{audio_file.stem}.jpg"
        if not download_thumbnail_file(image_url, temp_img):
            skipped += 1
            continue

        if embed_artwork_from_file(audio_file, temp_img, fmt):
            upgraded += 1
        else:
            skipped += 1

        try:
            temp_img.unlink()
        except Exception:
            pass

    print(f"  Done — {upgraded} upgraded to high-res square art, {skipped} kept default artwork.\n")


def embed_artwork_from_file(audio_path: Path, image_path: Path, fmt: str) -> bool:
    """Embed a local image file as album art into the given audio file."""
    try:
        image_data = image_path.read_bytes()

        if fmt == "mp3":
            from mutagen.mp3 import MP3
            from mutagen.id3 import ID3, APIC, error as ID3Error
            audio = MP3(audio_path, ID3=ID3)
            try:
                audio.add_tags()
            except ID3Error:
                pass
            audio.tags.delall("APIC")
            audio.tags.add(APIC(encoding=3, mime="image/jpeg", type=3,
                                 desc="Cover", data=image_data))
            audio.save()
            return True

        elif fmt == "flac":
            from mutagen.flac import FLAC, Picture
            audio = FLAC(audio_path)
            audio.clear_pictures()
            pic = Picture()
            pic.data = image_data
            pic.type = 3
            pic.mime = "image/jpeg"
            audio.add_picture(pic)
            audio.save()
            return True

        elif fmt == "m4a":
            from mutagen.mp4 import MP4, MP4Cover
            audio = MP4(audio_path)
            audio["covr"] = [MP4Cover(image_data, imageformat=MP4Cover.FORMAT_JPEG)]
            audio.save()
            return True

        else:
            # opus/wav: embedding artwork isn't reliably supported by mutagen
            # for these formats, so we leave the yt-dlp-embedded version as-is.
            return False

    except Exception:
        return False

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
                    embed_thumbnail: bool, browser: str, cookies_file: str,
                    start_track_number: int = 1) -> list:
    """
    Build the yt-dlp command.

    start_track_number lets us continue numbering correctly when downloading
    is split into batches (kept at 1 for a normal single-run download).

    Track numbers are filled in from the playlist position so music apps
    sort tracks in the artist's intended album order instead of
    alphabetically. Album art is cropped to a centered square as a
    fallback for any track where we couldn't fetch a proper high-res
    square thumbnail ourselves beforehand.
    """
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--format",             "bestaudio/best",
        "--extract-audio",
        "--audio-format",       fmt,
        "--audio-quality",      "0",
        "--add-metadata",
        "--parse-metadata",     "playlist_index:%(track_number)s",
        "--output",             str(output_dir / "%(artist,uploader)s - %(title)s.%(ext)s"),
        "--extractor-args",     "youtube:player_client=android_vr;player_skip=web_music",
        "--remote-components",  "ejs:github",
        "--sleep-interval",     "5",
        "--max-sleep-interval", "10",
        "--retries",            "10",
        "--fragment-retries",   "10",
        "--ignore-errors",
        "--playlist-start",     str(start_track_number),
    ]

    if embed_thumbnail:
        cmd += ["--embed-thumbnail", "--convert-thumbnails", "png"]
        # Fallback square-crop: if a track didn't get a pre-fetched
        # high-res square thumbnail swapped in (see download_highres_artwork),
        # this crops the default padded 16:9 thumbnail to a centered square
        # before it gets embedded, so it still displays cleanly everywhere.
        cmd += [
            "--ppa",
            r'EmbedThumbnail+ffmpeg_o:-c:v png -vf crop="min(iw\,ih):min(iw\,ih)"',
        ]

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

        if not entries:
            print("ERROR: No downloadable tracks found in manifest.", file=sys.stderr)
            sys.exit(1)

        print(f"Playlist      : {data.get('playlist_title', 'Unknown')}")
        print(f"Tracks        : {len(entries)}")

        # Swap music-video uploads for clean official-audio versions where
        # possible, so downloads don't contain skits/intros/crowd noise.
        urls = resolve_clean_audio_urls(entries, cookies_file, args.browser)
        urls = [u for u in urls if u]

        if not urls:
            print("ERROR: No downloadable tracks found in manifest.", file=sys.stderr)
            sys.exit(1)

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
    print(f"Track numbers : yes (playlist order)")
    print(f"Lyrics        : {'yes' if args.lyrics else 'no'}\n")

    cmd    = build_ytdlp_cmd(urls, output_dir, fmt, embed_thumbnail, args.browser, cookies_file)
    result = subprocess.run(cmd)

    if result.returncode == 0:
        print(f"\n✅ Download complete! Files saved to: {output_dir.resolve()}")
    else:
        print(f"\n⚠️  Finished with some errors (exit code {result.returncode}).")
        print(f"   Successfully downloaded files are in: {output_dir.resolve()}")

    if embed_thumbnail and entries:
        upgrade_artwork_to_highres(output_dir, entries, fmt)

    if args.lyrics:
        process_lyrics_for_folder(output_dir, entries)

    cleanup_stray_files(output_dir)

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
