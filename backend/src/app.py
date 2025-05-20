import os
import re
import uuid
import subprocess
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from diskcache import Cache
import psutil

from .generator import generate_manim_code
from .outline import generate_outline
from .executor import execute_manim_code

# Configuration
env = os.getenv
PORT = int(env("PORT", 5000))
MEDIA_ROOT = Path(env("MEDIA_DIR", "media/videos")).resolve()
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
CACHE_TTL = int(env("CACHE_TTL", 60))

# FastAPI init
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["GET","POST"], allow_headers=["*"],
)
cache = Cache(env("CACHE_DIR", "cache"))

# Resource guard
@app.middleware("http")
async def guard(request: Request, call_next):
    if psutil.cpu_percent() > 90 or psutil.virtual_memory().percent > 90:
        return JSONResponse({"error": "Server overloaded"}, status_code=503)
    response = await call_next(request)
    return response

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/generate")
async def generate(request: Request):
    data = await request.json()
    prompt = data.get("prompt", "").strip()
    if not prompt:
        raise HTTPException(400, "prompt is required")

    key = f"video::{hash(prompt)}"
    if cached := cache.get(key):
        return cached

    # 1. Storyboard outline
    outline = generate_outline(prompt)

    clips = []
    for idx, scene_desc in enumerate(outline, 1):
        code = generate_manim_code(scene_desc)
        m = re.search(r"class\s+(\w+)\(Scene\)", code)
        if not m:
            raise HTTPException(500, f"No Scene subclass in segment {idx}")
        scene_name = m.group(1)
        video_path = execute_manim_code(code, scene_name, MEDIA_ROOT)
        rel = video_path.relative_to(MEDIA_ROOT)
        clips.append(f"/media/videos/{rel.as_posix()}")

    # 2. Concatenate via ffmpeg
    run_id = uuid.uuid4().hex
    bundle = MEDIA_ROOT / run_id
    bundle.mkdir()
    list_file = bundle / "parts.txt"
    with list_file.open("w") as f:
        for clip in clips:
            path = MEDIA_ROOT / Path(clip).name
            f.write(f"file '{path}'\n")
    final_mp4 = bundle / "final.mp4"
    subprocess.run([
        "ffmpeg","-y","-f","concat","-safe","0",
        "-i", str(list_file), "-c","copy", str(final_mp4)
    ], check=True)

    result = {"videoUrl": f"/media/videos/{run_id}/final.mp4", "outline": outline}
    cache.set(key, result, expire=CACHE_TTL)
    return result

@app.get("/media/videos/{path:path}")
def serve(path: str):
    file = MEDIA_ROOT / path
    if not file.exists():
        raise HTTPException(404, "not found")
    return FileResponse(str(file), media_type="video/mp4")