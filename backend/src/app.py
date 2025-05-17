import os
import re
import time
import logging
import psutil

from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from diskcache import Cache

from .generator import generate_manim_code
from .executor import execute_manim_code

# ─────────────────────────────────────────────────────────────────────────────
# Load environment
load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
PORT       = int(os.getenv("PORT", 5000))
CACHE_DIR  = "cache"
CACHE_TTL  = 60 #seconds
MEDIA_DIR  = Path("media/videos")
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# Logging
logger = logging.getLogger("uvicorn")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ─────────────────────────────────────────────────────────────────────────────
# App init
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Disk‐backed cache
cache = Cache(CACHE_DIR)

# ─────────────────────────────────────────────────────────────────────────────
# Middleware: resource guard + timeout
class ResourceGuardMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # if CPU or RAM >90%, reject
        if psutil.cpu_percent() > 90 or psutil.virtual_memory().percent > 90:
            return JSONResponse(
                {"error": "Server overloaded; try again later."},
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        request.state.start_time = time.time()
        response = await call_next(request)
        elapsed = time.time() - request.state.start_time
        if elapsed > 300:
            return JSONResponse(
                {"error": "Request timeout"},
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
            )
        return response

app.add_middleware(ResourceGuardMiddleware)

# ─────────────────────────────────────────────────────────────────────────────
# Startup event
@app.on_event("startup")
async def on_startup():
    logger.info("🚀 FastAPI application has started!")

# ─────────────────────────────────────────────────────────────────────────────
# Routes

@app.get("/")
async def root():
    return {"status": "ok"}


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/generate")
async def generate_animation(request: Request):
    body = await request.json()
    prompt = (body.get("prompt") or "").strip()
    if not prompt:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Prompt is required")

    logger.info("Received /generate with prompt: %s", prompt)

    cache_key = f"video::{hash(prompt)}"
    cached = cache.get(cache_key)
    if cached:
        logger.info("Cache hit for prompt")
        return cached

    # 1) generate the Manim code
    code = generate_manim_code(prompt)

    # 2) extract Scene class name
    m = re.search(r"class\s+(\w+)\(Scene\)", code)
    if not m:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            "No Scene subclass found in generated code")
    scene_name = m.group(1)

    # 3) render video
    video_path = execute_manim_code(code, scene_name)
    rel = Path(video_path).resolve().relative_to(MEDIA_DIR.resolve())
    url = f"/media/videos/{rel.as_posix()}"

    payload = {"videoUrl": url, "code": code}
    cache.set(cache_key, payload, expire=CACHE_TTL)
    logger.info("Generated video %s", url)
    return payload


@app.get("/media/videos/{filename:path}")
async def serve_video(filename: str):
    file_path = MEDIA_DIR / filename
    if not file_path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video not found")
    return FileResponse(
        str(file_path),
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    code   = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail = str(exc)
    if isinstance(exc, HTTPException):
        code   = exc.status_code
        detail = exc.detail
    logger.error("Unhandled error: %s", detail, exc_info=exc)
    return JSONResponse({"error": detail}, status_code=code)
