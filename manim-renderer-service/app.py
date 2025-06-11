import os
import shutil
import tempfile
import uuid
import subprocess
import logging
import time
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.routing import APIRoute
from pydantic import BaseModel

# -------- logging setup --------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("renderer_service")

# -------- ensure MEDIA_ROOT --------
MEDIA_ROOT = Path(os.path.abspath("media/videos"))
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)

# -------- FastAPI + CORS + static files --------
app = FastAPI(
    title="Manim Renderer Service",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# Mount the actual video directory
app.mount(
    "/media/videos",
    StaticFiles(directory=str(MEDIA_ROOT)),
    name="media_videos",
)

# -------- request / response models --------
class RenderRequest(BaseModel):
    code: str
    quality: str   # "l", "m", or "h"
    timeout: int   # in seconds

class RenderResponse(BaseModel):
    videoUrl: str

# -------- helper to run a command with timeout --------
def run_command(cmd: List[str], timeout: int) -> None:
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        raise RuntimeError(f"Command timed out: {' '.join(cmd)}")
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed (exit {proc.returncode}): {stderr or stdout}")

# -------- helper to extract Scene subclass names --------
import ast
def extract_scene_names(code: str) -> List[str]:
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise RuntimeError(f"Invalid Python syntax: {e}")
    scenes = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                if (isinstance(base, ast.Name) and base.id == "Scene") or (
                    isinstance(base, ast.Attribute) and base.attr == "Scene"
                ):
                    scenes.append(node.name)
    if not scenes:
        raise RuntimeError("No Scene subclass found in code")
    return scenes

# -------- /render endpoint --------
@app.post("/render", response_model=RenderResponse)
async def render_endpoint(req: RenderRequest):
    logger.info(f"Starting rendering (quality={req.quality}, timeout={req.timeout}s)")

    # 1) Validate quality
    if req.quality not in ("l", "m", "h"):
        raise HTTPException(status_code=400, detail="Invalid quality. Must be 'l', 'm', or 'h'.")

    # 2) Extract scene names
    try:
        scenes = extract_scene_names(req.code)
    except Exception as e:
        logger.error(f"Scene extraction failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    # 3) Create temporary working directory
    work_dir = Path(tempfile.mkdtemp(prefix="manim_render_"))
    try:
        # 3a) Write code to file
        script_path = work_dir / "animation_script.py"
        script_path.write_text(req.code, encoding="utf-8")

        # 3b) Create media subdirectory
        media_dir = work_dir / "media"
        media_dir.mkdir(parents=True, exist_ok=True)

        # 3c) Create unique output folder under MEDIA_ROOT
        run_id = f"{uuid.uuid4().hex}_{int(time.time())}"
        final_dir = MEDIA_ROOT / run_id
        final_dir.mkdir(parents=True, exist_ok=True)
        output_file = final_dir / "final_animation.mp4"

        # 4) Build Manim command
        cmd = [
            "manim",
            "render",
            str(script_path),
            *scenes,
            f"-q{req.quality}",
            "--disable_caching",
            "--media_dir", str(media_dir),
            "--verbosity", "WARNING",
        ]
        if req.quality == "l":
            cmd += ["--frame_rate", "15"]

        logger.info(f"Running Manim: {' '.join(cmd)}")
        run_command(cmd, timeout=req.timeout)

        # 5) Gather all generated .mp4 files
        video_files = list(media_dir.rglob("*.mp4"))
        if not video_files:
            raise RuntimeError("No .mp4 files found in Manim output")

        # 6) Concatenate if multiple scenes
        if len(video_files) == 1:
            shutil.copy2(video_files[0], output_file)
        else:
            concat_txt = work_dir / "concat.txt"
            with open(concat_txt, "w") as f:
                for v in sorted(video_files):
                    f.write(f"file '{v.resolve()}'\n")
            concat_cmd = [
                "ffmpeg",
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_txt),
                "-c", "copy",
                str(output_file),
            ]
            logger.info(f"Running ffmpeg: {' '.join(concat_cmd)}")
            run_command(concat_cmd, timeout=120)

        # 7) Verify final video
        if not output_file.exists() or output_file.stat().st_size < 1024:
            raise RuntimeError("Final video is missing or too small")

        # Respond with just the relative‐URL
        rel_path = output_file.resolve().relative_to(MEDIA_ROOT.resolve())
        video_url = f"/media/videos/{rel_path.as_posix()}"
        logger.info(f"Rendering done → {video_url}")
        return RenderResponse(videoUrl=video_url)

    except RuntimeError as e:
        logger.error(f"Rendering pipeline failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # 8) Cleanup temp directory
        try:
            shutil.rmtree(work_dir)
        except Exception:
            pass

# -------- /health endpoint supporting GET & HEAD --------
@app.api_route("/health", methods=["GET", "HEAD"])
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
