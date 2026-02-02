import logging
from logging.config import dictConfig
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging_config import LogConfig
from app.api.v1.endpoints import profile, admin

# 1. Logging Setup (Fixed for Pydantic v2)
dictConfig(LogConfig().model_dump())
logger = logging.getLogger("ahp_profiler")

# 2. App Setup
app = FastAPI(title=settings.PROJECT_NAME)

# 3. CORS (Allow Streamlit or JS Frontend to talk to this)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Router
app.include_router(profile.router, prefix=settings.API_V1_STR)
app.include_router(admin.router, prefix=f"{settings.API_V1_STR}/admin", tags=["Admin"])

@app.get("/")
def root():
    return {"message": "AHP API is Running", "docs_url": "/docs"}