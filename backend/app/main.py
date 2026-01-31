import logging
from logging.config import dictConfig
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware # <--- NEW

from app.core.config import settings
from app.core.logging_config import LogConfig
from app.api.v1.endpoints import profile

# 1. Logging
dictConfig(LogConfig().dict())
logger = logging.getLogger("ahp_profiler")

# 2. App Setup
app = FastAPI(title=settings.PROJECT_NAME, version="1.0.0")

# 3. ENABLE CORS (Crucial for JS Frontend)
# This allows your HTML file to talk to the Python Server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, change this to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Include API Router
app.include_router(profile.router, prefix=settings.API_V1_STR, tags=["Profiling"])

# 5. Favicon Fix
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(content=None, status_code=204)

@app.get("/")
def root():
    return {"message": "AHP API is Running", "docs": "/docs"}