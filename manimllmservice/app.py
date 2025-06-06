# manim-llm-service/app.py

import os
import time
import logging
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import httpx

from prompt_expander import expand_prompt_with_fallback, PromptExpansionError
from generator import generate_manim_code_with_fallback

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("llm_service")

# ← This must be exactly your deployed renderer service (no trailing slash)
RENDERER_URL = os.getenv("RENDERER_URL", "").rstrip("/")
if not RENDERER_URL:
    raise RuntimeError(
        "Please set RENDERER_URL to project 2’s base URL "
        "(e.g. https://manim-renderer-service.onrender.com)"
    )

PORT = int(os.getenv("PORT", 8000))


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=500)
    quality: str = Field("m", pattern="^[lmh]$")
    timeout: int = Field(300, ge=60, le=600)


class GenerateResponse(BaseModel):
    videoUrl: str
    renderTime: float
    codeLength: int
    expandedPrompt: Optional[str] = None


app = FastAPI(
    title="Manim LLM Service",
    description="Expand user prompt → generate Manim code → delegate to renderer",
    version="1.0.0",
)

# ─── Install CORS before any routes ───────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


@app.post("/generate-code", response_model=GenerateResponse)
async def generate_code_and_delegate(req: GenerateRequest):
    start_time = time.time()
    user_prompt = req.prompt.strip()
    logger.info("Received /generate-code; expanding prompt")

    # 1) Expand prompt (fallback)
    try:
        detailed = expand_prompt_with_fallback(user_prompt)
    except PromptExpansionError as e:
        logger.error(f"Prompt expansion error: {e}")
        raise HTTPException(status_code=500, detail="Prompt expansion failed")

    logger.info(f"Expanded prompt (first 60 chars): {detailed[:60]}…")

    # 2) Generate Manim code (fallback)
    try:
        code = generate_manim_code_with_fallback(detailed)
    except Exception as e:
        logger.error(f"Code generation error: {e}")
        raise HTTPException(status_code=500, detail="Code generation failed")

    # 2a) Ensure `from manim import *` is at the top, so constants like BROWN, GREY, etc. exist
    if "from manim import" not in code:
        code = "from manim import *\n\n" + code

    code_len = len(code)
    logger.info(f"Generated Manim code length: {code_len} chars")

    # 3) Delegate to Renderer
    payload = {
        "code": code,
        "quality": req.quality,
        "timeout": req.timeout,
    }
    renderer_endpoint = f"{RENDERER_URL}/render"

    # Measure rendering time separately
    render_start = time.time()
    async with httpx.AsyncClient(timeout=req.timeout + 30) as client:
        try:
            response = await client.post(renderer_endpoint, json=payload)
        except httpx.RequestError as e:
            logger.error(f"Failed to contact renderer: {e}")
            raise HTTPException(status_code=502, detail="Renderer unavailable")

    render_elapsed = time.time() - render_start

    if response.status_code != 200:
        raw_body = response.text
        logger.error(f"Renderer returned {response.status_code} with body:\n{raw_body}")
        try:
            detail = response.json().get("detail", "Unknown error from renderer")
        except Exception:
            detail = f"Non-JSON error from renderer: {raw_body[:200]!r}"
        raise HTTPException(status_code=502, detail=f"Renderer error: {detail}")

    # At this point response.json() should contain something like:
    #   { "videoUrl": "/media/videos/xxxxxxxx/final_animation.mp4", ... }
    resp_json = response.json()

    # ─── Prepend the renderer’s hostname so that front-end can fetch the .mp4 ──────────
    raw_path = resp_json.get("videoUrl", "")
    full_video_url = f"{RENDERER_URL}{raw_path}"
    resp_json["videoUrl"] = full_video_url

    # Fill in our two computed fields:
    resp_json["renderTime"] = round(render_elapsed, 2)
    resp_json["codeLength"] = code_len

    # Add expandedPrompt if < 200 chars
    if len(detailed) < 200:
        resp_json["expandedPrompt"] = detailed

    total_elapsed = time.time() - start_time
    logger.info(f"Total time (LLM + code + render): {total_elapsed:.2f}s")

    return resp_json


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)
