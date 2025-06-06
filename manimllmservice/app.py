# manim-llm-service/app.py

import os
import time
import logging
import asyncio
from typing import Optional
from fastapi import FastAPI, HTTPException, status
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import httpx

from prompt_expander import expand_prompt_with_fallback, PromptExpansionError
from generator import generate_manim_code_with_fallback

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("llm_service")

# Pull in RENDERER_URL (no trailing slash)
RENDERER_URL = os.getenv("RENDERER_URL", "").rstrip("/")
if not RENDERER_URL:
    raise RuntimeError("Please set RENDERER_URL to Project 2’s base URL (no /render at the end)")

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


@app.post("/generate-code", response_model=GenerateResponse)
async def generate_code_and_delegate(req: GenerateRequest):
    start_time = time.time()
    user_prompt = req.prompt.strip()
    logger.info("Received /generate-code; expanding prompt")

    # 1) Expand prompt (fallback if needed)
    try:
        detailed = expand_prompt_with_fallback(user_prompt)
    except PromptExpansionError as e:
        logger.error(f"Prompt expansion error: {e}")
        raise HTTPException(status_code=500, detail="Prompt expansion failed")

    logger.info(f"Expanded prompt (first 60 chars): {detailed[:60]}…")

    # 2) Generate Manim code (fallback if needed)
    try:
        code = generate_manim_code_with_fallback(detailed)
    except Exception as e:
        logger.error(f"Code generation error: {e}")
        raise HTTPException(status_code=500, detail="Code generation failed")

    logger.info(f"Generated Manim code length: {len(code)} chars")

    # 3) Send code → renderer
    payload = {
        "code": code,
        "quality": req.quality,
        "timeout": req.timeout,
    }
    renderer_endpoint = f"{RENDERER_URL}/render"

    async with httpx.AsyncClient(timeout=req.timeout + 30) as client:
        try:
            response = await client.post(renderer_endpoint, json=payload)
        except httpx.RequestError as e:
            logger.error(f"Failed to contact renderer: {e}")
            raise HTTPException(status_code=502, detail="Renderer unavailable")

    if response.status_code != 200:
        # If renderer’s error body isn’t JSON, response.json() will fail—catch it
        try:
            detail = response.json().get("detail", "Unknown error from renderer")
        except Exception:
            detail = "Non‐JSON error from renderer"
        logger.error(f"Renderer returned {response.status_code}: {detail}")
        raise HTTPException(status_code=502, detail=f"Renderer error: {detail}")

    resp_json = response.json()
    # resp_json looks like { "videoUrl": "/media/videos/…", "…": … }
    # We must prepend RENDERER_URL so that front end can fetch it directly:
    raw_path = resp_json.get("videoUrl", "")
    full_video_url = f"{RENDERER_URL}{raw_path}"
    resp_json["videoUrl"] = full_video_url

    # Include expandedPrompt if small enough
    if len(detailed) < 200:
        resp_json["expandedPrompt"] = detailed

    elapsed = time.time() - start_time
    logger.info(f"Total time (LLM + code + render): {elapsed:.2f}s")
    return resp_json


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
