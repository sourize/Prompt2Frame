# manim-llm-service/app.py

import os
import time
import logging
import asyncio
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import httpx

from prompt_expander import expand_prompt_with_fallback, PromptExpansionError
from generator import generate_manim_code_with_fallback

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("llm_service")

# ─── Configuration ────────────────────────────────────────────────────────────
# Use your internal service name and port
RENDERER_URL = os.getenv("RENDERER_URL", "https://manim-renderer-service.onrender.com").rstrip("/")
PORT = int(os.getenv("PORT", 8000))

# ─── FastAPI app ─────────────────────────────────────────────────────────────
app = FastAPI(
    title="Manim LLM Service",
    description="Expand user prompt → generate Manim code → delegate to renderer",
    version="1.0.0",
)

# Allow any frontend to talk to us
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Models ───────────────────────────────────────────────────────────────────
class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=500)
    quality: str = Field("m", regex="^[lmh]$")
    timeout: int = Field(300, ge=60, le=600)

class GenerateResponse(BaseModel):
    videoUrl: str
    renderTime: float
    codeLength: int
    expandedPrompt: Optional[str] = None

# ─── Startup event ────────────────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup():
    logger.info(f"LLM service starting; renderer at {RENDERER_URL}")

# ─── Helper: post with retries ────────────────────────────────────────────────
async def post_to_renderer(
    client: httpx.AsyncClient,
    endpoint: str,
    payload: Dict[str, Any],
    max_attempts: int = 5,
) -> Dict[str, Any]:
    backoff = 1.0
    for attempt in range(1, max_attempts + 1):
        try:
            resp = await client.post(endpoint, json=payload)
            resp.raise_for_status()
            return resp.json()
        except (httpx.RequestError, httpx.HTTPStatusError) as exc:
            logger.warning(f"[Renderer] attempt {attempt} failed: {exc!r}")
            if attempt == max_attempts:
                raise HTTPException(status_code=502, detail="Renderer is unavailable")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 10.0)

# ─── Main endpoint ────────────────────────────────────────────────────────────
@app.post("/generate-code", response_model=GenerateResponse)
async def generate_code_and_delegate(req: GenerateRequest):
    start_time = time.time()
    prompt = req.prompt.strip()
    logger.info("Received /generate-code; expanding prompt")

    # 1) Expand
    try:
        detailed = expand_prompt_with_fallback(prompt)
    except PromptExpansionError:
        logger.exception("Prompt expansion failed")
        raise HTTPException(status_code=500, detail="Prompt expansion failed")
    logger.info(f"Expanded prompt: {detailed[:60]}…")

    # 2) Generate code
    try:
        code = generate_manim_code_with_fallback(detailed)
    except Exception:
        logger.exception("Code generation failed")
        raise HTTPException(status_code=500, detail="Code generation failed")
    logger.info(f"Generated Manim code length: {len(code)} chars")

    # 3) Call renderer with retries
    renderer_endpoint = f"{RENDERER_URL}/render"
    payload = {
        "code": code,
        "quality": req.quality,
        "timeout": req.timeout,
    }
    async with httpx.AsyncClient(timeout=req.timeout + 30) as client:
        resp_json = await post_to_renderer(client, renderer_endpoint, payload)

    # 4) Fix up the returned URL
    raw_url = resp_json.get("videoUrl", "")
    if raw_url.startswith("/"):
        resp_json["videoUrl"] = f"{RENDERER_URL}{raw_url}"

    # 5) Add expanded prompt if short
    if len(detailed) < 200:
        resp_json["expandedPrompt"] = detailed

    # 6) Metrics
    elapsed = time.time() - start_time
    resp_json["renderTime"] = round(elapsed, 2)
    resp_json["codeLength"] = len(code)
    logger.info(f"Total time (LLM+code+render): {elapsed:.2f}s")

    return resp_json

# ─── Healthcheck ──────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok"}

# ─── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=PORT, proxy_headers=True)
