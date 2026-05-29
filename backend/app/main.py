import asyncio
import sys

if sys.platform == "win32" and hasattr(asyncio, "WindowsProactorEventLoopPolicy"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # trigger reload

from app.routers import agent, sessions, uploads, voice


app = FastAPI(title="AI Dev Agent API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://*.vercel.app",       # covers any vercel preview URL
    ],
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
