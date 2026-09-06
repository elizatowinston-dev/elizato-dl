# Mobile architecture and operations

## Selected v1 stack

**Android-first Flutter** is the client: Dart keeps a future iOS port practical while Android has the most dependable scoped-storage and foreground-download APIs. The Python **FastAPI** service wraps the existing `elizato_dl.core` functions. A bounded in-process queue runs at most `MAX_WORKERS` `yt-dlp` subprocesses. It uses the existing `android_vr` extractor configuration, `--remote-components ejs:github`, Node.js, ffmpeg, mutagen tagging, and LRCLIB lyric processing. The phone never runs the EJS solver.

A small $5–10/month Ubuntu VPS is the recommended reliable deployment: long-running conversion jobs, Node, persistent Docker volumes, and predictable egress are generally unsuitable for free PaaS tiers. Docker deployment also works on Fly/Railway/Render, subject to their timeout, disk, and bandwidth limits.

## API contract

All endpoints require TLS at the reverse proxy. The native app supplies a random `X-Device-ID`; it is an identifier, not authentication. Put real user authentication/rate limiting in front of any Internet-exposed instance.

* `POST /v1/playlists/preview` multipart `cookies` plus JSON-like fields (`url`) returns playlist/track metadata.
* `POST /v1/jobs` multipart `cookies`, `url`, `format`, `lyrics`, `embed_thumbnail` returns `202` and job status.
* `GET /v1/jobs/{id}` returns state (`queued`, `running`, `complete`, `failed`), per-job progress and current track.
* `GET /v1/jobs/{id}/file` streams the completed ZIP. It includes audio and `.lrc` sidecars for non-MP3 formats.

The current worker expects cookies per preview/job. The upload is encrypted in memory with Fernet, materialized mode `0600` only for yt-dlp, then deleted. It is never logged or retained server-side. The phone should retain it only through `flutter_secure_storage` or user re-import; the scaffold currently keeps the picked file reference and must be completed before release to copy it into encrypted app storage.

## Deploy

1. Install Docker and Docker Compose on Ubuntu, create DNS `music-api.example.com`, and configure Caddy/Nginx with HTTPS to `127.0.0.1:8000`.
2. `cd backend && cp .env.example .env`
3. Set `COOKIE_ENCRYPTION_KEY` using `docker run --rm python:3.12-slim python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())"` and do not rotate it while jobs exist.
4. `docker compose up -d --build`; verify through HTTPS: `/healthz`.
5. Restrict firewall to 80/443, add auth and rate limits, monitor disk, and periodically delete expired job ZIPs. This scaffold has a TTL setting but cleanup needs a scheduled task before public deployment.

## Android build

Install Flutter stable and Android SDK, then from `mobile/` run `flutter create .` **before** replacing generated Android files, `flutter pub get`, and `flutter build apk --release`. Configure the HTTPS backend in Settings. Android 11+ saving should use Storage Access Framework (`ACTION_CREATE_DOCUMENT`) rather than broad filesystem permission; use a foreground service/WorkManager for a real resumable downloader. The included manifest accepts `ACTION_SEND` text from YouTube Music.

## Production completion checklist

The project establishes the API, queue and main screens, but the following must be completed/tested on physical devices before calling it production-ready: queue polling plus ZIP streaming/save via SAF; download foreground notification/retry after process death; MediaStore library scan and `just_audio` player; cookie copy into encrypted app storage; authenticated user accounts and per-user job access; persistent queue (Redis/Celery/RQ) if using multiple API replicas; deletion scheduler; integration tests with a permitted test playlist. Do not rely on URL/device ID alone as authorization.

## Experimental offline fallback (not recommended)

QuickJS bindings on Android and JavaScriptCore on iOS can execute a narrowly-adapted EJS script, but are not Node-compatible and browser APIs/modules in yt-dlp’s solver can change without notice. Shipping it couples each app release to YouTube/yt-dlp changes, has no server-side hot fix, and is especially fragile on iOS. Keep it behind an experimental feature flag; backend solving is the supported design.
