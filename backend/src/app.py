import re
import time
import uuid
import logging
import psutil
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from diskcache import Cache

from .outline    import generate_outline
from .generator  import generate_manim_code
from .executor   import execute_manim_code, concat_videos, MEDIA_ROOT

# ─── Logging & Cache ─────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("uvicorn")
cache = Cache("cache")

# ─── FastAPI setup ───────────────────────────────────────────────────────────
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

class ResourceGuard(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/health":
            return await call_next(request)
        # reject if overloaded
        if psutil.cpu_percent() > 90 or psutil.virtual_memory().percent > 90:
            return JSONResponse(
                {"error": "Server overloaded"},
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        start = time.time()
        resp = await call_next(request)
        if time.time() - start > 300:
            return JSONResponse(
                {"error": "Request timed out"},
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
            )
        return resp

app.add_middleware(ResourceGuard)

@app.get("/health")
async def health():
    return {"status": "ok"}

_SCENE_NAME_REGEX = re.compile(r"class\s+(\w+)\s*\(\s*Scene\s*\)")

@app.post("/generate")
async def generate(request: Request):
    body = await request.json()
    prompt = body.get("prompt", "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")

    cache_key = f"gen::{hash(prompt)}"
    if (cached := cache.get(cache_key)):
        return cached

    # 1) Turn prompt into 3–6 scene descriptions
    try:
        descriptions = generate_outline(prompt)
    except Exception as e:
        logger.error("Outline generation failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Outline error: {e}")

    # 2) For each description, generate Python code + name
    scenes: list[dict] = []
    for idx, desc in enumerate(descriptions, start=1):
        try:
            code = generate_manim_code(desc)
        except Exception as e:
            logger.error("LLM code gen for scene %d failed: %s", idx, e)
            scenes.append({"scene": idx, "error": f"Code gen failed: {e}"})
            continue

        m = _SCENE_NAME_REGEX.search(code)
        if not m:
            logger.error("Could not extract class name from scene %d code", idx)
            scenes.append({"scene": idx, "error": "No Scene subclass found in code"})
            continue

        name = m.group(1)
        scenes.append({"scene": idx, "name": name, "code": code})

    # 3) Execute Manim on each successfully generated scene
    videos = []
    codes   = []
    errors  = []
    for sc in scenes:
        if "error" in sc:
            errors.append({"scene": sc["scene"], "error": sc["error"]})
            continue

        idx, name, code = sc["scene"], sc["name"], sc["code"]
        codes.append({"scene": idx, "name": name, "code": code})
        try:
            video_path = execute_manim_code(code, name)
            videos.append(video_path)
        except Exception as e:
            logger.error("Scene %d rendering failed: %s", idx, e)
            errors.append({"scene": idx, "error": str(e)})

    if not videos:
        # nothing succeeded
        raise HTTPException(
            status_code=500,
            detail="All scenes failed – see errors",
        )

    # 4) Concatenate if needed, else use single
    final_path = concat_videos(videos) if len(videos) > 1 else videos[0]
    rel = final_path.resolve().relative_to(MEDIA_ROOT.resolve())
    payload = {
        "videoUrl": f"/media/videos/{rel.as_posix()}",
        "codes": codes,
        "errors": errors,
    }

    cache.set(cache_key, payload, expire=60)
    return payload

@app.get("/media/videos/{path:path}")
async def serve(path: str):
    file = MEDIA_ROOT / path
    if not file.exists():
        raise HTTPException(status_code=404, detail="Video not found")
    return FileResponse(
        str(file),
        headers={
            "Cache-Control": "no-store, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )
