import os
import time
import logging
import asyncio
from typing import Optional, Dict, Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from pydantic import BaseModel, Field

from prompt_expander import expand_prompt_with_fallback, PromptExpansionError
from generator import generate_manim_code_with_fallback

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("llm_service")

# Renderer URL (internal or public)
RENDERER_URL = os.getenv("RENDERER_URL", "").rstrip("/")
if not RENDERER_URL:
    raise RuntimeError("Please set RENDERER_URL to your renderer service’s base URL")

# App settings
MAX_TIMEOUT = 600

class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=500)
    quality: str = Field("m", pattern="^[lmh]$")
    timeout: int = Field(300, ge=60, le=MAX_TIMEOUT)

class GenerateResponse(BaseModel):
    videoUrl: str
    renderTime: float
    codeLength: int
    expandedPrompt: Optional[str] = None

app = FastAPI(title="Manim LLM Service", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST","OPTIONS"],
    allow_headers=["*"],
)

# Self-ping to keep alive
@app.on_event("startup")
async def keep_awake():
    async def ping_loop():
        async with httpx.AsyncClient() as client:
            while True:
                try:
                    await client.get("http://localhost:8000/health")
                except:
                    pass
                await asyncio.sleep(60)
    asyncio.create_task(ping_loop())
    logger.info("Started self-ping loop to /health every 60s")

# Helper: retry POST /render
async def post_with_retries(endpoint: str, payload: Dict[str, Any], timeout: int):
    backoff = 1.0
    async with httpx.AsyncClient(timeout=timeout) as client:
        for i in range(1, 6):
            try:
                r = await client.post(endpoint, json=payload)
                r.raise_for_status()
                return r.json()
            except Exception as e:
                logger.warning(f"[Renderer] attempt {i} failed: {e}")
                if i == 5:
                    raise HTTPException(502, f"Renderer unavailable: {e}")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 10)

@app.post("/generate-code", response_model=GenerateResponse)
async def generate_code_and_delegate(req: GenerateRequest):
    t0 = time.time()
    logger.info("Received /generate-code; expanding prompt")

    # 1) Expand
    try:
        detailed = expand_prompt_with_fallback(req.prompt.strip())
    except PromptExpansionError as e:
        logger.error(f"Prompt expansion failed: {e}")
        raise HTTPException(500, "Prompt expansion failed")
    logger.info(f"Expanded prompt: {detailed[:60]}…")

    # 2) Generate code
    try:
        code = generate_manim_code_with_fallback(detailed)
    except Exception as e:
        logger.error(f"Code generation failed: {e}")
        raise HTTPException(500, "Code generation failed")
    code_len = len(code)

    # 3) Delegate to renderer
    payload = {"code": code, "quality": req.quality, "timeout": req.timeout}
    endpoint = f"{RENDERER_URL}/render"
    rt0 = time.time()
    data = await post_with_retries(endpoint, payload, req.timeout + 60)
    render_time = time.time() - rt0

    # 4) Build response
    raw = data.get("videoUrl", "")
    video_url = raw if raw.startswith("http") else f"{RENDERER_URL}{raw}"
    resp = {
        "videoUrl": video_url,
        "renderTime": round(render_time,2),
        "codeLength": code_len,
    }
    if len(detailed) < 200:
        resp["expandedPrompt"] = detailed

    logger.info(f"Total service time: {time.time()-t0:.2f}s")
    return resp

# Health responds to GET & HEAD
@app.api_route("/health", methods=["GET","HEAD"])
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=int(os.getenv("PORT",8000)), log_level="info")
