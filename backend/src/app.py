import time, uuid, psutil, logging
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from diskcache import Cache
from pathlib import Path

from .generator import generate_manim_code
from .executor  import execute_manim_code, concat_videos, MEDIA_ROOT

# ─── Logging & Cache ─────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("uvicorn")
cache = Cache("cache")

# ─── FastAPI setup ───────────────────────────────────────────────────────────
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET","POST","OPTIONS"],
    allow_headers=["*"],
)

class ResourceGuard(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/health":
            return await call_next(request)
        if psutil.cpu_percent() > 90 or psutil.virtual_memory().percent > 90:
            return JSONResponse({"error":"Server overloaded"}, status.HTTP_503_SERVICE_UNAVAILABLE)
        start = time.time()
        resp = await call_next(request)
        if time.time() - start > 300:
            return JSONResponse({"error":"Request timed out"}, status.HTTP_408_REQUEST_TIMEOUT)
        return resp

app.add_middleware(ResourceGuard)

@app.get("/health")
async def health(): return {"status":"ok"}

@app.post("/generate")
async def generate(request: Request):
    body = await request.json()
    prompt = body.get("prompt","").strip()
    if not prompt:
        raise HTTPException(400, "Prompt is required")

    cache_key = f"gen::{hash(prompt)}"
    if (cached := cache.get(cache_key)):
        return cached

    try:
        scenes = generate_manim_code(prompt)
    except Exception as e:
        raise HTTPException(500, f"LLM generation error: {e}")

    videos, codes, errors = [], [], []
    for idx, sc in enumerate(scenes, start=1):
        name, code = sc["name"], sc["code"]
        codes.append({"scene":idx, "name":name, "code":code})
        try:
            vp = execute_manim_code(code, name)
            videos.append(vp)
        except Exception as e:
            logger.error("Scene %d failed: %s", idx, e)
            errors.append({"scene":idx, "error": str(e)})

    if not videos:
        raise HTTPException(500, "All scenes failed—see errors array")

    # If multiple, concat; otherwise pick lone
    final_path = concat_videos(videos) if len(videos)>1 else videos[0]
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
        raise HTTPException(404, "Video not found")
    return FileResponse(
        str(file),
        headers={
            "Cache-Control":"no-store, max-age=0",
            "Pragma":"no-cache",
            "Expires":"0"
        }
    )
