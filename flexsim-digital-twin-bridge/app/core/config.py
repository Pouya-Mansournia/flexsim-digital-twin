"""Application configuration."""

from pathlib import Path

from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "flexsim-digital-twin-bridge"
    host: str = "127.0.0.1"
    port: int = 8000
    log_dir: Path = Path(__file__).resolve().parent.parent.parent / "logs"
    log_file: str = "bridge.log"
    log_level: str = "INFO"


settings = Settings()
