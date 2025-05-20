import os
import re
import time
import uuid
import logging
import psutil
import subprocess

from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from diskcache import Cache

from .generator import generate_manim_code
from .executor import execute_manim_code
from .outline import generate_outline

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

    # 1) generate a storyboard outline
    outline = generate_outline(prompt)

    # 2) for each outline item, generate Manim code
    scene_video_urls = []
    for idx, scene_desc in enumerate(outline, start=1):
        scene_code = generate_manim_code(scene_desc)
        # extract class name
        m = re.search(r"class\s+(\w+)\(Scene\)", scene_code)
        if not m:
            raise HTTPException(500, f"No Scene subclass in scene #{idx}")
        scene_name = m.group(1)

        # 3) render each scene
        video_path = execute_manim_code(scene_code, scene_name)
        rel = Path(video_path).resolve().relative_to(MEDIA_DIR.resolve())
        scene_video_urls.append(f"/media/videos/{rel.as_posix()}")

    # 4) stitch clips into one final video (ffmpeg)
    final_id = uuid.uuid4().hex
    concat_list = MEDIA_DIR / final_id / "list.txt"
    (MEDIA_DIR / final_id).mkdir(parents=True, exist_ok=True)
    with open(concat_list, "w") as f:
        for url in scene_video_urls:
            # ffmpeg concat protocol wants file paths
            path = MEDIA_DIR / url.split("/media/videos/")[1]
            f.write(f"file '{path}'\n")

    final_output = MEDIA_DIR / final_id / "final.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy", str(final_output)
    ], check=True)

    payload = {
        "videoUrl": f"/media/videos/{final_id}/final.mp4",
        "outline": outline,
        "sceneClips": scene_video_urls
    }
    cache.set(cache_key, payload, expire=CACHE_TTL)
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
