# app/services/knowledge_base.py

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "AHP Student Profiler"
    PROJECT_VERSION: str = "1.0.0"
    PROJECT_DESCRIPTION: str = "AHP Profiling Engine & PDF Parser"
    API_V1_STR: str = "/api/v1"

    # Database settings
    class Config:
        case_sensitive = True

settings = Settings()