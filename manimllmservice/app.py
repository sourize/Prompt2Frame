# manim-llm-service/app.py

import os
import time
import logging
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import httpx
import asyncio

from prompt_expander import expand_prompt_with_fallback, PromptExpansionError
from generator import generate_manim_code_with_fallback

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("llm_service")

RENDERER_URL = os.getenv("RENDERER_URL", "").rstrip("/")
if not RENDERER_URL:
    raise RuntimeError("Please set RENDERER_URL to your renderer’s base URL")

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

app = FastAPI(title="Manim LLM Service", version="1.0.0")

# Allow our frontend to talk to us
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/generate-code", response_model=GenerateResponse)
async def generate_code_and_delegate(req: GenerateRequest):
    start_total = time.time()
    user_prompt = req.prompt.strip()

    # 1) Expand
    try:
        detailed = expand_prompt_with_fallback(user_prompt)
    except PromptExpansionError:
        logger.exception("Prompt expansion failed")
        raise HTTPException(500, "Prompt expansion failed")

    # 2) Generate code
    try:
        code = generate_manim_code_with_fallback(detailed)
    except Exception:
        logger.exception("Code generation failed")
        raise HTTPException(500, "Code generation failed")

    code_len = len(code)

    # 3) Call renderer with retries
    payload = {"code": code, "quality": req.quality, "timeout": req.timeout}
    url = f"{RENDERER_URL}/render"
    render_start = time.time()
    last_err = None

    async with httpx.AsyncClient(timeout=req.timeout + 30) as client:
        for attempt in range(1, 4):
            try:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    break
                # capture detail
                detail = resp.json().get("detail", resp.text[:200])
                logger.warning(f"[Renderer] attempt {attempt} returned {resp.status_code}: {detail}")
            except Exception as e:
                last_err = e
                logger.warning(f"[Renderer] attempt {attempt} threw: {e!r}")
            await asyncio.sleep(attempt)  # backoff
        else:
            msg = last_err if last_err else f"Renderer failed after 3 attempts"
            logger.error(msg)
            raise HTTPException(502, str(msg))

    render_end = time.time()

    data = resp.json()
    rel_path = data.get("videoUrl", "")
    full_url = f"{RENDERER_URL}{rel_path}"

    out = {
        "videoUrl": full_url,
        "renderTime": round(render_end - render_start, 2),
        "codeLength": code_len,
    }
    if len(detailed) < 200:
        out["expandedPrompt"] = detailed

    logger.info(f"Total pipeline time: {time.time() - start_total:.2f}s")
    return out

@app.get("/health")
def health():
    return {"status": "ok"}
