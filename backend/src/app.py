import os
import re
import time
import uuid
import logging
import psutil

from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from diskcache import Cache
from dotenv import load_dotenv

from .generator import generate_manim_code
from .outline import generate_outline
from .executor import execute_manim_code, concat_videos, MEDIA_ROOT

# ─────────────────────────────────────────────────────────────────────────────
load_dotenv()
PORT      = int(os.getenv("PORT", 5000))
CACHE_TTL = 60  # seconds
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger("uvicorn")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
cache = Cache("cache_dir")

class ResourceGuard(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if psutil.cpu_percent() > 90 or psutil.virtual_memory().percent > 90:
            return JSONResponse(
                {"error": "Server overloaded"},
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        start = time.time()
        resp = await call_next(request)
        if time.time() - start > 300:
            return JSONResponse(
                {"error": "Request timeout"},
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
            )
        return resp

app.add_middleware(ResourceGuard)

@app.on_event("startup")
async def on_startup():
    logger.info("🚀 Application startup complete")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/generate")
async def generate(request: Request):
    data = await request.json()
    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        raise HTTPException(400, "Prompt is required")

    cache_key = f"gen::{hash(prompt)}"
    if cached := cache.get(cache_key):
        return cached

    logger.info("Received prompt: %s", prompt)

    # 1) Storyboard
    try:
        outline = generate_outline(prompt)
    except Exception as e:
        raise HTTPException(500, f"Outline generation failed: {e}")

    # 2) Generate & render each scene
    scene_videos = []
    errors = []
    for idx, scene_desc in enumerate(outline, start=1):
        try:
            code = generate_manim_code(scene_desc)
            m = re.search(r"class\s+(\w+)\(Scene\)", code)
            if not m:
                raise ValueError("No Scene subclass found")
            scene_name = m.group(1)
            try:
                vid = execute_manim_code(code, scene_name)
                scene_videos.append(vid)
            except Exception as e:
                logger.error("Scene %d failed: %s", idx, e)
                errors.append({"scene": idx, "error": str(e)})
        except Exception as e:
            logger.error("Code generation failed for scene %d: %s", idx, e)
            errors.append({"scene": idx, "error": f"Code generation failed: {e}"})

    if not scene_videos:
        raise HTTPException(500, f"All scenes failed: {errors}")

    # 3) Stitch
    try:
        final_vid = concat_videos(scene_videos, final_name=str(uuid.uuid4()))
    except Exception as e:
        raise HTTPException(500, f"Video stitching failed: {e}")

    rel = final_vid.resolve().relative_to(MEDIA_ROOT.resolve())
    url = f"/media/videos/{rel.as_posix()}"

    payload = {"videoUrl": url, "outline": outline, "errors": errors}
    cache.set(cache_key, payload, expire=CACHE_TTL)
    return payload

@app.get("/media/videos/{path:path}")
async def serve(path: str):
    file_path = MEDIA_ROOT / path
    if not file_path.exists():
        raise HTTPException(404, "Not found")
    return FileResponse(
        str(file_path),
        headers={
            "Cache-Control": "no-store",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )

@app.exception_handler(Exception)
async def catch_all(request, exc):
    code = getattr(exc, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR)
    msg = str(exc)
    logger.error("Unhandled error: %s", msg, exc_info=exc)
    return JSONResponse({"error": msg}, status_code=code)
