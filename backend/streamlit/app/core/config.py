# app/core/config.py

import os
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "AHP Student Profiler"
    
    # Base Dir is the directory containing this file (app/core) -> parent (app) -> parent (root)
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    
    # Pointing to the 'data' folder at the ROOT of the project
    DATA_DIR: Path = BASE_DIR / "data" 
    LOG_DIR: Path = BASE_DIR / "logs"

    class Config:
        case_sensitive = True

settings = Settings()
os.makedirs(settings.LOG_DIR, exist_ok=True)