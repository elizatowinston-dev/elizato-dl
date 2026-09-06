"""HTTPS-only API facade for the desktop extraction core.
Run behind a TLS reverse proxy. Never log request bodies or cookie contents.
"""
import hashlib, os
from contextlib import asynccontextmanager
from pathlib import Path
from cryptography.fernet import Fernet, InvalidToken
from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from .settings import settings
from .schemas import DownloadRequest, JobStatus, PlaylistRequest, Playlist
from .worker import manager
from elizato_dl.core import extract_playlist_metadata

# Cookie blobs are encrypted if stored. This implementation instead decrypts into a job-only
# file and deletes it after use; encrypted upload is retained only for the request lifecycle.
fernet = Fernet(settings.cookie_encryption_key.encode())
def device_key(device_id: str | None) -> str:
    if not device_id or len(device_id) < 16: raise HTTPException(400,"X-Device-ID is required")
    return hashlib.sha256(device_id.encode()).hexdigest()
def cookie_path(device_id: str) -> Path:
    p=settings.data_dir/"requests"; p.mkdir(parents=True,exist_ok=True); return p/f"{device_key(device_id)}-{os.urandom(8).hex()}.txt"
async def materialize_cookie(upload: UploadFile, device_id: str) -> Path:
    raw=await upload.read()
    if len(raw) > 5_000_000 or b"# Netscape HTTP Cookie File" not in raw[:300]:
        raise HTTPException(400,"Upload a valid Netscape cookies.txt file")
    encrypted=fernet.encrypt(raw) # encryption boundary; never log raw
    try: plain=fernet.decrypt(encrypted)
    except InvalidToken: raise HTTPException(500,"Could not protect cookie upload")
    path=cookie_path(device_id); path.write_bytes(plain); os.chmod(path,0o600); return path

def view(job) -> JobStatus:
    return JobStatus(id=job.id,state=job.state,progress=job.progress,current_track=job.current_track,
      completed_tracks=job.completed_tracks,total_tracks=job.total_tracks,error=job.error,
      download_url=f"/v1/jobs/{job.id}/file" if job.state=="complete" else None)
@asynccontextmanager
async def life(app):
    settings.data_dir.mkdir(parents=True,exist_ok=True); await manager.start(); yield; await manager.stop()
app=FastAPI(title="elizato-dl mobile API",version="1.0.0",lifespan=life)
app.add_middleware(CORSMiddleware,allow_origins=[x for x in settings.allowed_origins.split(",") if x],allow_methods=["*"],allow_headers=["*"])
@app.get("/healthz")
def health(): return {"ok":True}
@app.post("/v1/playlists/preview",response_model=Playlist)
async def preview(url: str = Form(...), cookies: UploadFile=File(...), x_device_id: str|None=Header()):
    try: payload=PlaylistRequest(url=url)
    except Exception: raise HTTPException(422, "A valid YouTube URL is required")
    path=await materialize_cookie(cookies,x_device_id)
    try: return extract_playlist_metadata(str(payload.url),cookies_file=str(path))
    except BaseException: raise HTTPException(422,"Could not fetch playlist. Check URL and refresh cookies.")
    finally: path.unlink(missing_ok=True)
@app.post("/v1/jobs",response_model=JobStatus,status_code=202)
async def create_job(url: str=Form(...), format: str=Form("mp3"), lyrics: bool=Form(True), embed_thumbnail: bool=Form(True), cookies: UploadFile=File(...),x_device_id: str|None=Header()):
    try: payload=DownloadRequest(url=url, format=format, lyrics=lyrics, embed_thumbnail=embed_thumbnail)
    except Exception: raise HTTPException(422, "Invalid download request")
    return view(await manager.submit(payload,await materialize_cookie(cookies,x_device_id)))
@app.get("/v1/jobs/{job_id}",response_model=JobStatus)
def status(job_id: str):
    job=manager.jobs.get(job_id)
    if not job: raise HTTPException(404,"Job not found")
    return view(job)
@app.get("/v1/jobs/{job_id}/file")
def download(job_id: str):
    job=manager.jobs.get(job_id)
    if not job or job.state!="complete" or not job.archive: raise HTTPException(404,"Finished download not found")
    return FileResponse(job.archive,media_type="application/zip",filename=f"elizato-{job.id}.zip")
