from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    data_dir: Path = Path("/data")
    # Generate once: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    cookie_encryption_key: str
    max_workers: int = 2
    job_ttl_hours: int = 24
    allowed_origins: str = ""

settings = Settings()
