from enum import Enum
from pydantic import BaseModel, Field, HttpUrl

class AudioFormat(str, Enum):
    mp3="mp3"; flac="flac"; m4a="m4a"; wav="wav"; opus="opus"
class PlaylistRequest(BaseModel):
    url: HttpUrl
class DownloadRequest(BaseModel):
    url: HttpUrl
    format: AudioFormat = AudioFormat.mp3
    lyrics: bool = True
    embed_thumbnail: bool = True
class Track(BaseModel):
    id: str | None = None; title: str | None = None; artist: str | None = None
    album: str | None = None; thumbnail: str | None = None; duration: int | None = None
    webpage_url: str | None = None
class Playlist(BaseModel):
    playlist_title: str | None = None; playlist_id: str | None = None
    playlist_url: str | None = None; entries: list[Track] = []
class JobStatus(BaseModel):
    id: str; state: str; progress: float = 0; current_track: str | None = None
    completed_tracks: int = 0; total_tracks: int = 0; error: str | None = None
    download_url: str | None = None
