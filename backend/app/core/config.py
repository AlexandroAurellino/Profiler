import os
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "AHP Student Profiler"
    PROJECT_VERSION: str = "1.0.0"
    PROJECT_DESCRIPTION: str = "AHP Profiling Engine & PDF Parser"
    API_V1_STR: str = "/api/v1"

    # ==========================================
    # PATH CONFIGURATION
    # ==========================================
    # Dynamic path resolution using pathlib
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    LOG_DIR: Path = BASE_DIR.parent / "logs"

    class Config:
        case_sensitive = True

settings = Settings()

# Ensure critical directories exist on startup
os.makedirs(settings.LOG_DIR, exist_ok=True)