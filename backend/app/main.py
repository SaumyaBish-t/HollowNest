import asyncio
import os
import sys

if sys.platform == "win32" and hasattr(asyncio, "WindowsProactorEventLoopPolicy"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import agent, sessions, uploads, voice


app = FastAPI(title="AI Dev Agent API", version="1.0.0")

_default_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
_extra = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
_allow_origins = _default_origins + _extra

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent.router)
app.include_router(sessions.router)
app.include_router(uploads.router)
app.include_router(voice.router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
