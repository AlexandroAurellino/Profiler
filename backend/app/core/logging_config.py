# backend/app/core/logging_config.py

from pydantic import BaseModel

class LogConfig(BaseModel):
    LOGGER_NAME: str = "ahp_profiler"
    LOG_FORMAT: str = "%(levelprefix)s | %(asctime)s | %(module)s:%(lineno)d | %(message)s"
    LOG_LEVEL: str = "DEBUG"

    version: int = 1
    disable_existing_loggers: bool = False
    formatters: dict = {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": LOG_FORMAT,
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    }
    handlers: dict = {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
        "file": {
            "formatter": "default",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/app.log",
            "maxBytes": 10485760, # 10MB
            "backupCount": 5,
            "encoding": "utf8",
        },
    }
    loggers: dict = {
        "ahp_profiler": {"handlers": ["default", "file"], "level": LOG_LEVEL},
        "uvicorn": {"handlers": ["default", "file"], "level": "INFO"},
    }