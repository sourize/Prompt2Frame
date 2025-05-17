# src/app.py
import os
import re
import time
import psutil
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from diskcache import Cache

from .generator import generate_manim_code
from .executor import execute_manim_code

# load .env
load_dotenv()

# -------------------------------------------------------------------
# CONFIG
# -------------------------------------------------------------------
PORT = int(os.getenv("PORT", 5000))
CACHE_DIR = "cache"
CACHE_TTL = 60        # seconds
MEDIA_DIR = Path("media/videos")
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------------------------
# INIT
# -------------------------------------------------------------------
app = FastAPI()
# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # adjust to your domain(s)
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)
# Disk-backed cache
cache = Cache(CACHE_DIR)

# -------------------------------------------------------------------
# RESOURCE CHECK MIDDLEWARE
# -------------------------------------------------------------------
class ResourceGuardMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # simple CPU/memory guard
        if psutil.cpu_percent() > 90 or psutil.virtual_memory().percent > 90:
            return JSONResponse(
                {"error": "Server overloaded; try again later."},
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        # start timer
        request.state.start_time = time.time()
        resp = await call_next(request)
        # enforce max duration
        elapsed = time.time() - request.state.start_time
        if elapsed > 300:
            return JSONResponse(
                {"error": "Request timeout"},
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
            )
        return resp

app.add_middleware(ResourceGuardMiddleware)

# -------------------------------------------------------------------
# ROUTES
# -------------------------------------------------------------------
@app.post("/generate")
async def generate_animation(request: Request):
    body = await request.json()
    prompt = (body.get("prompt") or "").strip()
    if not prompt:
        raise HTTPException(400, "Prompt is required")

    # cache key based on prompt only (we auto-expire)
    key = f"video::{hash(prompt)}"
    if key in cache:
        return cache.get(key)

    # 1️⃣ generate code
    code = generate_manim_code(prompt)

    # 2️⃣ find scene class
    m = re.search(r"class\s+(\w+)\(Scene\)", code)
    if not m:
        raise HTTPException(500, "No Scene subclass found in generated code")
    scene_name = m.group(1)

    # 3️⃣ render video
    video_path = execute_manim_code(code, scene_name)
    rel = Path(video_path).resolve().relative_to(MEDIA_DIR.resolve())
    url = f"/media/videos/{rel.as_posix()}"

    payload = {"videoUrl": url, "code": code}
    # store in cache
    cache.set(key, payload, expire=CACHE_TTL)
    return payload

@app.get("/media/videos/{filename:path}")
async def serve_video(filename: str):
    file_path = MEDIA_DIR / filename
    if not file_path.exists():
        raise HTTPException(404, "Video not found")
    # no-cache headers
    return FileResponse(
        str(file_path),
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )

@app.get("/health")
async def health_check():
    return {"status": "ok"}

# -------------------------------------------------------------------
# GLOBAL EXCEPTION HANDLER
# -------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    code = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail = str(exc)
    if isinstance(exc, HTTPException):
        code = exc.status_code
        detail = exc.detail
    return JSONResponse({"error": detail}, status_code=code)
