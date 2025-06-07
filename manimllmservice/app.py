# manim-llm-service/app.py

import os
import time
import logging
import asyncio
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

RENDERER_URL = os.getenv("RENDERER_URL", "").rstrip("/")
if not RENDERER_URL:
    raise RuntimeError("Please set RENDERER_URL to your renderer service base URL")

PORT = int(os.getenv("PORT", 8000))
MAX_RENDERER_RETRIES = 3
BACKOFF_DELAYS = [1, 2, 4]  # seconds between retries

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
    version="1.0.0",
)
# Allow any origin so your React app can call this freely
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    # wait up to 15s for the renderer to be healthy
    async with httpx.AsyncClient() as client:
        for attempt in range(15):
            try:
                r = await client.get(f"{RENDERER_URL}/health")
                if r.status_code == 200:
                    break
            except httpx.RequestError:
                pass
            await asyncio.sleep(1)
        else:
            raise HTTPException(
                status_code=502,
                detail="Renderer never became healthy"
            )

@app.post("/generate-code", response_model=GenerateResponse)
async def generate_code_and_delegate(req: GenerateRequest):
    start = time.time()

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

    logger.info(f"Generated code length: {len(code)} chars")

    # 3) Call renderer with retries
    payload = {"code": code, "quality": req.quality, "timeout": req.timeout}
    endpoint = f"{RENDERER_URL}/render"
    last_error = None
    for attempt in range(1, MAX_RENDERER_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=req.timeout + 30) as client:
                resp = await client.post(endpoint, json=payload)
        except Exception as e:
            last_error = e
            logger.warning(f"[Renderer] network error on attempt {attempt}: {e}")
        else:
            if 200 <= resp.status_code < 300:
                data = resp.json()
                break
            else:
                last_error = RuntimeError(f"HTTP {resp.status_code}")
                snippet = resp.text[:200].replace("\n"," ")
                logger.warning(f"[Renderer] HTTP {resp.status_code} on attempt {attempt}: {snippet!r}")
        # backoff if more retries remain
        if attempt < MAX_RENDERER_RETRIES:
            delay = BACKOFF_DELAYS[attempt - 1]
            logger.info(f"Waiting {delay}s before retrying renderer…")
            await asyncio.sleep(delay)
    else:
        logger.error(f"All renderer attempts failed: {last_error}")
        raise HTTPException(502, f"Renderer unavailable: {last_error}")

    # 4) Patch up the response
    # renderer returns {"videoUrl": "/media/videos/...", "renderTime": X, "codeLength": Y}
    raw_url = data.get("videoUrl", "")
    data["videoUrl"] = f"{RENDERER_URL}{raw_url}"
    if len(detailed) < 200:
        data["expandedPrompt"] = detailed

    total = time.time() - start
    logger.info(f"Total time (LLM+code+render): {total:.2f}s")
    return data

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
