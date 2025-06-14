# ===== app.py =====
import os
import time
import logging
import asyncio
from typing import Dict, Any

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from prompt_expander import expand_prompt_with_fallback, PromptExpansionError
from generator import generate_manim_code_with_fallback

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("llm_service")

# Renderer service URL
RENDERER_URL = os.getenv("RENDERER_URL", "").rstrip("/")
if not RENDERER_URL:
    raise RuntimeError("Please set RENDERER_URL to your renderer service's base URL")

# Service-wide constants
MAX_TIMEOUT = 600  # seconds
INTERNAL_PORT = int(os.getenv("PORT", 8000))

class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=500)
    quality: str = Field("m", pattern="^[lmh]$")
    timeout: int = Field(300, ge=60, le=MAX_TIMEOUT)

class GenerateResponse(BaseModel):
    videoUrl: str
    renderTime: float
    codeLength: int
    expandedPrompt: str | None = None

app = FastAPI(title="Manim LLM Service", version="1.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "OPTIONS", "GET"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def keep_awake():
    url = f"http://localhost:{INTERNAL_PORT}/health"
    async def ping_loop():
        async with httpx.AsyncClient(timeout=5) as client:
            while True:
                try:
                    await client.get(url)
                except Exception:
                    pass
                await asyncio.sleep(60)

    asyncio.create_task(ping_loop())
    logger.info("Started self-ping loop to /health every 60s")

async def post_with_retries(endpoint: str, payload: Dict[str, Any], timeout: int) -> Dict[str, Any]:
    backoff = 1.0
    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(1, 6):
            try:
                response = await client.post(endpoint, json=payload)
                response.raise_for_status()
                return response.json()
            except Exception as exc:
                logger.warning(f"[Renderer] attempt {attempt} failed: {exc}")
                if attempt == 5:
                    raise HTTPException(status_code=502, detail=f"Renderer unavailable: {exc}")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 10)

@app.post("/generate-code", response_model=GenerateResponse)
async def generate_code_and_delegate(req: GenerateRequest) -> GenerateResponse:
    start_total = time.time()
    logger.info("Received /generate-code; expanding prompt")

    try:
        detailed = expand_prompt_with_fallback(req.prompt.strip())
    except PromptExpansionError as e:
        logger.error(f"Prompt expansion failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid prompt input")
    logger.info(f"Expanded prompt: {detailed[:60]}…")

    try:
        code = generate_manim_code_with_fallback(detailed)
    except Exception as e:
        logger.error(f"Code generation failed: {e}")
        raise HTTPException(status_code=500, detail="Code generation failed")

    code_length = len(code)
    payload = {"code": code, "quality": req.quality, "timeout": req.timeout}
    render_endpoint = f"{RENDERER_URL}/render"
    start_render = time.time()
    result = await post_with_retries(render_endpoint, payload, timeout=req.timeout + 10)
    render_time = time.time() - start_render

    video_path = result.get("videoUrl")
    if not video_path:
        raise HTTPException(status_code=502, detail="Renderer response missing videoUrl")
    video_url = video_path if video_path.startswith("http") else f"{RENDERER_URL}{video_path}"

    response = GenerateResponse(
        videoUrl=video_url,
        renderTime=round(render_time, 2),
        codeLength=code_length,
        expandedPrompt=detailed if len(detailed) < 200 else None,
    )
    logger.info(f"Total service time: {time.time() - start_total:.2f}s")
    return response

@app.get("/health")
async def health(request: Request) -> Dict[str, str]:
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=INTERNAL_PORT,
        log_level="info",
    )