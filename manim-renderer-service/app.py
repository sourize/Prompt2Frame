# manim-renderer-service/app.py
import os
import time
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
from executor import render_and_concat_all, RenderError, MEDIA_ROOT

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("renderer_service")

PORT = int(os.getenv("PORT", 8000))

app = FastAPI(
    title="Manim Renderer Service",
    description="Receive Manim code, render it to video, and return a URL",
    version="1.0.0",
)

# Ensure MEDIA_ROOT exists on startup
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)


class RenderRequest(BaseModel):
    code: str = Field(..., description="Full Manim Python code (as a single string)")
    quality: str = Field("m", pattern="^[lmh]$")
    timeout: int = Field(300, ge=60, le=600)


class RenderResponse(BaseModel):
    videoUrl: str
    renderTime: float
    codeLength: int


@app.post("/render", response_model=RenderResponse)
async def render_code(req: RenderRequest):
    start_time = time.time()
    code = req.code
    quality = req.quality
    timeout = req.timeout

    logger.info(f"Starting rendering (quality={quality}, timeout={timeout}s)")

    try:
        # render_and_concat_all returns a Path to final_animation.mp4
        video_path = render_and_concat_all(code, quality, timeout)
    except RenderError as e:
        logger.error(f"RenderError: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected render exception: {e}")
        raise HTTPException(status_code=500, detail="Unexpected rendering failure")

    # Build public URL for the video
    try:
        # video_path is something like media/videos/<run_id>/final_animation.mp4
        rel = video_path.resolve().relative_to(MEDIA_ROOT.parent.resolve())  # up one level
        # MEDIA_ROOT.parent is the “media” directory; we want everything after that 
        # so that /media/videos/... resolves properly
        url = f"/media/{rel.as_posix()}"
    except Exception as e:
        logger.error(f"Failed to build video URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate video URL")

    render_time = time.time() - start_time
    logger.info(f"Rendering done in {render_time:.2f}s → {url}")

    return {
        "videoUrl": url,
        "renderTime": render_time,
        "codeLength": len(code),
    }


@app.get("/media/videos/{run_id}/{filename}")
async def serve_video(run_id: str, filename: str):
    """Serve the generated .mp4 files with proper headers."""
    file_path = MEDIA_ROOT / run_id / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Video not found")

    file_size = file_path.stat().st_size
    return FileResponse(
        str(file_path),
        media_type="video/mp4",
        headers={
            "Cache-Control": "public, max-age=3600",
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
            "X-Content-Type-Options": "nosniff",
        },
    )


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
