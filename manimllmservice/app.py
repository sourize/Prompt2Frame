import os
import time
import logging

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

LLM_SERVICE_URL = os.getenv("LLM_SERVICE_URL", "https://manim-llm-service.onrender.com")
RENDERER_URL    = os.getenv("RENDERER_URL")  # e.g. "https://manim-renderer-service.onrender.com"

if not RENDERER_URL:
    raise RuntimeError("Please set RENDERER_URL to your deployed renderer service URL")

PORT = int(os.getenv("PORT", 8000))


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=500)
    quality: str = Field("m", pattern="^[lmh]$")
    timeout: int = Field(300, ge=60, le=600)


class GenerateResponse(BaseModel):
    videoUrl: str
    renderTime: float
    codeLength: int
    expandedPrompt: str | None = None


app = FastAPI(
    title="Manim LLM Service",
    description="Expand user prompt & generate Manim code, then forward to renderer",
    version="1.0.0",
)

# Enable CORS so your React frontend can access /generate-code
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # in production, lock this down to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
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

    logger.info(f"Expanded prompt: {detailed[:60]}...")

    # 2) Generate Manim code (with fallback)
    try:
        code = generate_manim_code_with_fallback(detailed)
    except Exception as e:
        logger.error(f"Code generation error: {e}")
        raise HTTPException(status_code=500, detail="Code generation failed")

    logger.info(f"Generated code length: {len(code)} chars")

    # 3) Delegate to the Renderer Service
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
        detail = response.json().get("detail", "Unknown error from renderer")
        logger.error(f"Renderer returned {response.status_code}: {detail}")
        raise HTTPException(status_code=502, detail=f"Renderer error: {detail}")

    resp_json = response.json()
    # ───────────────────────────────────────────────────────────────────────────
    # Fix #1: convert the relative videoUrl into a full URL
    raw_video = resp_json.get("videoUrl", "")
    if raw_video.startswith("/"):
        # e.g. raw_video = "/media/videos/abcd1234/final_animation.mp4"
        resp_json["videoUrl"] = f"{RENDERER_URL}{raw_video}"
    # ───────────────────────────────────────────────────────────────────────────

    # Include expandedPrompt if it isn’t too long
    if len(detailed) < 200:
        resp_json["expandedPrompt"] = detailed

    elapsed = time.time() - start_time
    logger.info(f"Total time (LLM+code+render): {elapsed:.2f}s")
    return resp_json


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
