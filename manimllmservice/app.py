import os
import time
import logging
import asyncio
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from prompt_expander import expand_prompt_with_fallback, PromptExpansionError
from generator import generate_manim_code_with_fallback

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("llm_service")

# ← Set this to your renderer’s base URL, e.g. "https://manim-renderer-service.onrender.com"
RENDERER_URL = os.getenv("RENDERER_URL", "").rstrip("/")
if not RENDERER_URL:
    raise RuntimeError("Please set RENDERER_URL to your renderer service’s base URL")

# Total timeout for user request (LLM+render)
MAX_TOTAL_TIMEOUT = 600  # seconds

class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=500)
    quality: str = Field("m", pattern="^[lmh]$")
    timeout: int = Field(300, ge=60, le=MAX_TOTAL_TIMEOUT)

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

@app.post("/generate-code", response_model=GenerateResponse)
async def generate_code_and_delegate(req: GenerateRequest):
    start_time = time.time()
    user_prompt = req.prompt.strip()
    logger.info("Received /generate-code; expanding prompt")

    # 1) Expand prompt (with fallback)
    try:
        detailed = expand_prompt_with_fallback(user_prompt)
    except PromptExpansionError as e:
        logger.error(f"Prompt expansion error: {e}")
        raise HTTPException(status_code=500, detail="Prompt expansion failed")
    logger.info(f"Expanded prompt: {detailed[:60]}…")

    # 2) Generate Manim code (with fallback)
    try:
        code = generate_manim_code_with_fallback(detailed)
    except Exception as e:
        logger.error(f"Code generation error: {e}")
        raise HTTPException(status_code=500, detail="Code generation failed")
    logger.info(f"Generated Manim code length: {len(code)} chars")

    # 3) Prepare payload & endpoint
    payload = {"code": code, "quality": req.quality, "timeout": req.timeout}
    renderer_endpoint = f"{RENDERER_URL}/render"

    # 4) Call renderer with retries/back-off (to survive cold starts)
    render_start = time.time()
    last_error = None
    backoff = 1
    async with httpx.AsyncClient(timeout=req.timeout + 60) as client:
        for attempt in range(1, 5):
            try:
                resp = await client.post(renderer_endpoint, json=payload)
            except httpx.RequestError as exc:
                last_error = exc
                logger.warning(f"[Renderer] attempt {attempt} network error: {exc}")
            else:
                if resp.status_code == 200:
                    break
                # try to parse JSON error detail if possible
                detail = None
                try:
                    detail = resp.json().get("detail")
                except Exception:
                    detail = resp.text[:200]
                last_error = f"HTTP {resp.status_code}: {detail}"
                logger.warning(f"[Renderer] attempt {attempt} returned {last_error}")
            # back-off before retrying
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 10)
        else:
            logger.error(f"All renderer attempts failed: {last_error}")
            raise HTTPException(status_code=502, detail=f"Renderer error: {last_error}")

    # 5) Process successful response
    data = resp.json()
    rel_url = data.get("videoUrl")
    if not rel_url:
        raise HTTPException(status_code=502, detail="Renderer response missing videoUrl")

    # prepend full host so frontend can fetch directly
    full_url = f"{RENDERER_URL}{rel_url}"
    render_time = time.time() - render_start

    # optionally include expanded prompt
    if len(detailed) < 200:
        data["expandedPrompt"] = detailed

    result = {
        "videoUrl": full_url,
        "renderTime": round(render_time, 2),
        "codeLength": len(code),
        **({k: data[k] for k in ("expandedPrompt",) if k in data}),
    }
    total_time = time.time() - start_time
    logger.info(f"Completed in {total_time:.2f}s (render {render_time:.2f}s)")
    return result

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), log_level="info")
