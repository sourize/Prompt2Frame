import time
import psutil
import logging
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from .prompt_expander import expand_prompt
from .generator        import generate_manim_code
from .executor         import render_and_concat_all, MEDIA_ROOT

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("uvicorn")

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
async def health():
    return {"status":"ok"}

@app.post("/generate")
async def generate(request: Request):
    data = await request.json()
    prompt = data.get("prompt", "").strip()
    if not prompt:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Prompt is required")

    # 1) Expand the short user prompt to one detailed paragraph
    try:
        logger.info("Starting prompt expansion")
        detailed = expand_prompt(prompt)
        logger.info("Prompt expansion successful")
    except Exception as e:
        logger.error("Prompt expansion failed: %s", str(e))
        raise HTTPException(500, f"Prompt expansion failed: {e}")

    # 2) Generate a single Manim script
    try:
        logger.info("Starting code generation")
        code = generate_manim_code(detailed)
        logger.info("Code generation successful")
    except Exception as e:
        logger.error("Code generation failed: %s", str(e))
        raise HTTPException(500, f"Code generation failed: {e}")

    # 3) Render all scenes and concat
    try:
        logger.info("Starting rendering pipeline")
        video_path = render_and_concat_all(code)
        logger.info("Rendering pipeline successful, video at: %s", str(video_path))
    except Exception as e:
        logger.error("Generation pipeline error: %s", str(e))
        raise HTTPException(500, f"Rendering pipeline error: {e}")

    rel = video_path.resolve().relative_to(MEDIA_ROOT.resolve())
    return {"videoUrl": f"/media/videos/{rel.as_posix()}"}

@app.get("/media/videos/{path:path}")
async def serve(path: str):
    file = MEDIA_ROOT / path
    if not file.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Video not found")
    return FileResponse(str(file), headers={
        "Cache-Control":"no-store, max-age=0",
        "Pragma":"no-cache",
        "Expires":"0"
    })
