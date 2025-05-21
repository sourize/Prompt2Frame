# app.py
import time, psutil, logging
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from diskcache import Cache
from pathlib import Path

from .prompt_expander import expand_prompt
from .generator       import generate_manim_code
from .executor        import execute_manim_code, concat_videos, MEDIA_ROOT

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("uvicorn")
cache = Cache("cache")

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class ResourceGuard(BaseHTTPMiddleware):
    async def dispatch(self, req, call_next):
        if req.url.path == "/health":
            return await call_next(req)
        if psutil.cpu_percent() > 90 or psutil.virtual_memory().percent > 90:
            return JSONResponse({"error":"Server overloaded"}, status.HTTP_503_SERVICE_UNAVAILABLE)
        start = time.time()
        resp = await call_next(req)
        if time.time() - start > 300:
            return JSONResponse({"error":"Request timed out"}, status.HTTP_408_REQUEST_TIMEOUT)
        return resp

app.add_middleware(ResourceGuard)

@app.get("/health")
async def health():
    return {"status":"ok"}

@app.post("/generate")
async def generate(request: Request):
    body = await request.json()
    prompt = body.get("prompt","").strip()
    if not prompt:
        raise HTTPException(400, "Prompt is required")

    # 1) Expand -> 2) Generate code -> 3) Render all scenes -> 4) Concat
    try:
        expanded = expand_prompt(prompt)
        code = generate_manim_code(expanded)
        parts = execute_manim_code(code)  # list[Path]
        final = parts[0] if len(parts)==1 else concat_videos(parts)
    except Exception as e:
        logger.error("Generation pipeline error: %s", e)
        raise HTTPException(500, str(e))

    rel = final.resolve().relative_to(MEDIA_ROOT.resolve())
    return {
        "videoUrl": f"/media/videos/{rel.as_posix()}",
    }

@app.get("/media/videos/{path:path}")
async def serve(path: str):
    file = MEDIA_ROOT / path
    if not file.exists():
        raise HTTPException(404, "Video not found")
    return FileResponse(str(file), headers={
        "Cache-Control":"no-store",
        "Pragma":"no-cache",
        "Expires":"0",
    })
