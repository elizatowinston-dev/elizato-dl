"""Bounded async job runner. Jobs run subprocess yt-dlp so API workers remain responsive."""
import asyncio, shutil, time, uuid, zipfile
from dataclasses import dataclass, field
from pathlib import Path
from .settings import settings
from .schemas import DownloadRequest
from elizato_dl.core import build_ytdlp_cmd, extract_playlist_metadata, process_lyrics_for_folder, cleanup_stray_files

@dataclass
class Job:
    id: str; request: DownloadRequest; cookie_file: Path
    state: str = "queued"; progress: float = 0; current_track: str | None = None
    completed_tracks: int = 0; total_tracks: int = 0; error: str | None = None
    directory: Path | None = None; archive: Path | None = None; created: float = field(default_factory=time.time)

class JobManager:
    def __init__(self): self.jobs: dict[str, Job] = {}; self.queue: asyncio.Queue[Job] = asyncio.Queue(); self.tasks=[]
    async def start(self): self.tasks=[asyncio.create_task(self._run()) for _ in range(settings.max_workers)]
    async def stop(self):
        for task in self.tasks: task.cancel()
    async def submit(self, request, cookie_file):
        job=Job(uuid.uuid4().hex, request, cookie_file); self.jobs[job.id]=job; await self.queue.put(job); return job
    async def _run(self):
        while True:
            job=await self.queue.get()
            try: await asyncio.to_thread(self._download, job)
            finally: self.queue.task_done()
    def _download(self, job):
        job.state="running"; job.directory=settings.data_dir / "jobs" / job.id; job.directory.mkdir(parents=True)
        try:
            metadata=extract_playlist_metadata(str(job.request.url), cookies_file=str(job.cookie_file))
            entries=metadata["entries"]; job.total_tracks=len(entries)
            urls=[x["webpage_url"] for x in entries if x.get("webpage_url")]
            if not urls: raise RuntimeError("No downloadable tracks in playlist")
            cmd=build_ytdlp_cmd(urls, job.directory, job.request.format.value, job.request.embed_thumbnail, None, str(job.cookie_file))
            # yt-dlp output is deliberately not persisted: it may contain URL/query credentials.
            proc=__import__('subprocess').Popen(cmd, stdout=__import__('subprocess').PIPE, stderr=__import__('subprocess').STDOUT, text=True, errors="replace")
            for line in proc.stdout:
                if "[download] Destination:" in line or "[ExtractAudio] Destination:" in line:
                    job.current_track=line.rsplit(":", 1)[-1].strip()
                if "has already been downloaded" in line or "Deleting original file" in line:
                    job.completed_tracks=min(job.total_tracks, job.completed_tracks+1); job.progress=job.completed_tracks/max(1,job.total_tracks)
            if proc.wait() != 0: raise RuntimeError("yt-dlp finished with errors; refresh cookies and retry")
            job.completed_tracks=job.total_tracks; job.progress=1
            if job.request.lyrics: process_lyrics_for_folder(job.directory, entries)
            cleanup_stray_files(job.directory)
            archive=job.directory.with_suffix(".zip")
            with zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED) as z:
                for p in job.directory.iterdir():
                    if p.is_file(): z.write(p,p.name)
            job.archive=archive; job.state="complete"
        except Exception as exc:
            job.error=str(exc); job.state="failed"
        finally:
            if job.cookie_file.exists(): job.cookie_file.unlink()  # per-job decrypted cookie never retained

manager=JobManager()
