# app.py
import re, time, uuid, psutil, logging
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from diskcache import Cache

from .outline    import generate_outline
from .generator  import generate_manim_code
from .executor   import execute_manim_code, concat_videos, MEDIA_ROOT

logger = logging.getLogger("uvicorn")
logging.basicConfig(level=logging.INFO)
cache = Cache("cache")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ResourceGuard(BaseHTTPMiddleware):
    async def dispatch(self, req, call_next):
        if req.url.path == "/health":
            return await call_next(req)
        if psutil.cpu_percent()>90 or psutil.virtual_memory().percent>90:
            return JSONResponse({"error":"Server overloaded"}, status_code=503)
        start = time.time()
        resp = await call_next(req)
        if time.time()-start > 300:
            return JSONResponse({"error":"Timeout"}, status_code=408)
        return resp

app.add_middleware(ResourceGuard)

_SCENE_RE = re.compile(r"class\s+(\w+)\s*\(\s*Scene\s*\)")

@app.get("/health")
async def health(): return {"status":"ok"}

@app.post("/generate")
async def generate(request: Request):
    body = await request.json()
    prompt = body.get("prompt","").strip()
    if not prompt:
        raise HTTPException(400, "Prompt required")

    key = f"gen::{hash(prompt)}"
    if (out := cache.get(key)):
        return out

    # 1) Outline → paragraphs
    try:
        paras = generate_outline(prompt)
    except Exception as e:
        raise HTTPException(500, f"Outline error: {e}")

    videos = []
    codes  = []
    errors = []

    for idx, para in enumerate(paras, start=1):
        # code gen
        try:
            code = generate_manim_code(para)
        except Exception as e:
            errors.append({"paragraph": idx, "error": str(e)})
            continue

        # extract all Scene class names
        names = _SCENE_RE.findall(code)
        if not names:
            errors.append({"paragraph": idx, "error":"No Scene subclass found"})
            continue

        codes.append({"paragraph": idx, "classes": names, "code": code})

        # render each class
        try:
            out_vids = execute_manim_code(code)
        except Exception as e:
            errors.append({"paragraph": idx, "error": str(e)})
            continue

        videos.extend(out_vids)

    if not videos:
        raise HTTPException(500, "All scenes failed")

    # 2) concat if multiple
    final = concat_videos(videos) if len(videos)>1 else videos[0]
    rel = final.resolve().relative_to(MEDIA_ROOT.resolve())
    result = {
        "videoUrl": f"/media/videos/{rel.as_posix()}",
        "codes": codes,
        "errors": errors,
    }
    cache.set(key, result, expire=60)
    return result

@app.get("/media/videos/{path:path}")
async def serve(path: str):
    f = MEDIA_ROOT / path
    if not f.exists():
        raise HTTPException(404, "Not found")
    return FileResponse(str(f), headers={
        "Cache-Control":"no-store",
        "Pragma":"no-cache",
        "Expires":"0",
    })
