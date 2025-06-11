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

# ← Set this to your renderer’s base URL, internal or public
RENDERER_URL = os.getenv("RENDERER_URL", "").rstrip("/")
if not RENDERER_URL:
    raise RuntimeError("Please set RENDERER_URL to your renderer service’s base URL")

# Max total pipeline time
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

app = FastAPI(
    title="Manim LLM Service",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST","OPTIONS"],
    allow_headers=["*"],
    allow_credentials=True,
)

# Helper: post to renderer with retries
async def post_with_retries(
    endpoint: str, payload: Dict[str, Any], timeout: int
) -> Dict[str, Any]:
    backoff = 1.0
    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(1, 6):
            try:
                resp = await client.post(endpoint, json=payload)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                logger.warning(f"[Renderer] attempt {attempt} failed: {e}")
                if attempt == 5:
                    raise HTTPException(502, f"Renderer unavailable: {e}")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 10)

@app.post("/generate-code", response_model=GenerateResponse)
async def generate_code_and_delegate(req: GenerateRequest):
    start_total = time.time()
    user_prompt = req.prompt.strip()
    logger.info("Received /generate-code; expanding prompt")

    # 1) Expand prompt
    try:
        detailed = expand_prompt_with_fallback(user_prompt)
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
    logger.info(f"Generated code length: {code_len}")

    # 3) Delegate to renderer
    endpoint = f"{RENDERER_URL}/render"
    payload = {"code": code, "quality": req.quality, "timeout": req.timeout}
    render_start = time.time()
    data = await post_with_retries(endpoint, payload, req.timeout + 30)
    render_time = time.time() - render_start

    # 4) Build final URL
    raw_url = data.get("videoUrl")
    if not raw_url:
        raise HTTPException(502, "Renderer returned no videoUrl")
    full_url = raw_url if raw_url.startswith("http") else f"{RENDERER_URL}{raw_url}"

    # 5) Prepare response
    resp = {
        "videoUrl": full_url,
        "renderTime": round(render_time, 2),
        "codeLength": code_len,
    }
    if len(detailed) < 200:
        resp["expandedPrompt"] = detailed

    total_time = time.time() - start_total
    logger.info(f"Total pipeline time: {total_time:.2f}s")
    return resp

# Health endpoint allows GET & HEAD
@app.api_route("/health", methods=["GET","HEAD"] )
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), log_level="info")
