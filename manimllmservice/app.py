# manim-llm-service/app.py

import os
import time
import logging
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from prompt_expander import expand_prompt_with_fallback, PromptExpansionError
from generator import generate_manim_code_with_fallback

# ─── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("llm_service")

# ─── Read environment variables ─────────────────────────────────────────────────
RENDERER_URL = os.getenv("RENDERER_URL", "").rstrip("/")
if not RENDERER_URL:
    raise RuntimeError("Please set RENDERER_URL to Project 2’s base URL (e.g. https://…/render)")

PORT = int(os.getenv("PORT", 8000))


# ─── Request / Response Schemas ─────────────────────────────────────────────────
class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=500)
    quality: str = Field("m", pattern="^[lmh]$")   # still accept, but we'll only send "m" to renderer
    timeout: int = Field(300, ge=60, le=600)       # seconds


class GenerateResponse(BaseModel):
    videoUrl: str
    renderTime: float
    codeLength: int
    expandedPrompt: Optional[str] = None


# ─── FastAPI + CORS ─────────────────────────────────────────────────────────────
app = FastAPI(
    title="Manim LLM Service",
    description="Expand user prompt & generate Manim code, then forward to renderer",
    version="1.0.0",
)

# Allow all origins (so your React app can call this endpoint)
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
    # 1) Expand the user prompt (with fallback)
    try:
        detailed: str = expand_prompt_with_fallback(user_prompt)
    except PromptExpansionError as e:
        logger.error(f"Prompt expansion error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Prompt expansion failed"
        )

    logger.info(f"Expanded prompt (first 60 chars): {detailed[:60]}…")

    # 2) Generate Manim code from the expanded prompt (with fallback)
    try:
        code: str = generate_manim_code_with_fallback(detailed)
    except Exception as e:
        logger.error(f"Code generation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Code generation failed"
        )

    code_length = len(code)
    logger.info(f"Generated Manim code length: {code_length} chars")

    # 3) Delegate to the Renderer Service
    payload = {
        "code": code,
        # Always send "m" to the renderer, ignoring req.quality for now:
        "quality": "m",
        "timeout": req.timeout,
    }
    renderer_endpoint = f"{RENDERER_URL}/render"

    # Send the POST; catch network errors
    try:
        async with httpx.AsyncClient(timeout=req.timeout + 30) as client:
            response = await client.post(renderer_endpoint, json=payload)
    except httpx.RequestError as e:
        logger.error(f"Failed to contact renderer: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Renderer unavailable"
        )

    # 4) Handle non-200 status from renderer
    if response.status_code != 200:
        # Try to parse JSON.detail if possible
        detail_msg = None
        try:
            detail_msg = response.json().get("detail")
        except Exception:
            # If it’s not valid JSON, grab the first 500 chars of HTML/text
            raw_text = response.text[:500]
            detail_msg = f"Non-JSON error ({response.status_code}): {raw_text}"

        logger.error(f"Renderer returned {response.status_code}: {detail_msg}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Renderer error: {detail_msg}"
        )

    # 5) At this point, we have a 200 from the renderer
    try:
        renderer_data = response.json()
    except Exception as e:
        logger.error(f"Renderer response JSON parse error: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not parse renderer response"
        )

    # The renderer should at minimum return {"videoUrl": "..."}
    video_url = renderer_data.get("videoUrl")
    if not video_url:
        logger.error("Renderer response missing key 'videoUrl'")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Renderer response missing videoUrl"
        )

    # 6) Compute total elapsed time
    total_elapsed = time.time() - start_time
    logger.info(f"Total time (LLM→code→render): {total_elapsed:.2f}s")

    # Optionally include the expandedPrompt (only if it’s not too large)
    optional_expanded = detailed if len(detailed) < 200 else None

    return GenerateResponse(
        videoUrl=video_url,
        renderTime=round(total_elapsed, 2),
        codeLength=code_length,
        expandedPrompt=optional_expanded,
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=PORT,
        log_level="info",
    )
