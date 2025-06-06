# llm_service/app.py

import os
import time
import logging
import asyncio
import httpx

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from prompt_expander import expand_prompt_with_fallback, PromptExpansionError
from generator import generate_manim_code_with_fallback  # no more `RuntimeError as CodeGenError`

# ----------------- logging setup -----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("llm_service")

# ----------------- configuration -----------------
# Point this at your deployed renderer service (Project 2)
RENDERER_URL = os.getenv("RENDERER_URL")

# ----------------- FastAPI + CORS -----------------
app = FastAPI(
    title="Manim LLM Service",
    version="1.0.0",
    description="Takes a text prompt, expands it, generates Manim code, then delegates rendering to a separate service."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # in production, restrict to your frontend domain
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=True,
)

# ----------------- request / response models -----------------
class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=500, description="Animation prompt")
    timeout: int = Field(300, ge=60, le=600, description="Timeout in seconds (for rendering)")

class GenerateResponse(BaseModel):
    videoUrl: str

# ----------------- health check -----------------
@app.get("/health")
async def health_check():
    return {"status": "ok"}

# ----------------- /generate-code endpoint -----------------
@app.post("/generate-code", response_model=GenerateResponse)
async def generate_code_and_delegate(req: GenerateRequest):
    """
    1) Expand the prompt via expand_prompt_with_fallback (with retries).
    2) Generate Manim code via generate_manim_code_with_fallback (with retries).
    3) POST <code, "m", timeout> to {RENDERER_URL}/render.
    4) If renderer responds 200 with JSON { "videoUrl": "/media/videos/.../final_animation.mp4" },
       prepend RENDERER_URL to form a full URL and return it.
    5) If the renderer returns non‐JSON or status != 200, raise HTTP 502 with a clear message.
    """
    logger.info("Received /generate-code; expanding prompt")

    # --- 1) Expand prompt ---
    try:
        expanded = await asyncio.to_thread(expand_prompt_with_fallback, req.prompt)
    except PromptExpansionError as e:
        logger.error(f"Prompt expansion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to expand prompt: {e}"
        )

    logger.info(f"Expanded prompt ({len(expanded.split())} words)")

    # --- 2) Generate Manim code ---
    try:
        code = await asyncio.to_thread(generate_manim_code_with_fallback, expanded)
    except Exception as e:
        logger.error(f"Code generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate Manim code: {e}"
        )

    logger.info(f"Generated Manim code length: {len(code)} chars")

    # --- 3) Delegate rendering to renderer service ---
    payload = {
        "code": code,
        "quality": "m",        # always medium quality
        "timeout": req.timeout
    }

    renderer_endpoint = f"{RENDERER_URL.rstrip('/')}/render"
    logger.info(f"POSTing to renderer → {renderer_endpoint}")

    try:
        async with httpx.AsyncClient(timeout=req.timeout + 30) as client:
            response = await client.post(renderer_endpoint, json=payload)
    except httpx.RequestError as exc:
        logger.error(f"Failed to reach renderer: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to reach renderer service"
        )

    # If renderer responded with non‐200, try to parse JSON error if any
    if response.status_code != 200:
        text = response.text.strip()
        try:
            body = response.json()
            detail = body.get("detail") or body.get("error") or str(body)
        except ValueError:
            detail = "Renderer returned non‐JSON: " + text.splitlines()[0]
        logger.error(f"Renderer error: HTTP {response.status_code} → {detail}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Renderer failed: {detail}"
        )

    # At this point, status_code == 200. Expect JSON like { "videoUrl": "/media/videos/.../final_animation.mp4" }
    try:
        data = response.json()
    except ValueError:
        logger.error("Renderer returned 200 but non‐JSON body")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Renderer returned invalid JSON"
        )

    if "videoUrl" not in data:
        logger.error(f"Renderer JSON missing videoUrl field: {data}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Renderer response missing 'videoUrl'"
        )

    # Build a full URL for frontend (cache‐bust with timestamp)
    partial = data["videoUrl"].lstrip("/")  # e.g. "media/videos/abcd1234/final_animation.mp4"
    full_url = f"{RENDERER_URL.rstrip('/')}/{partial}?t={int(time.time())}"
    logger.info(f"Returning full videoUrl → {full_url}")

    return GenerateResponse(videoUrl=full_url)


# ----------------- main (Uvicorn entrypoint) -----------------
if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
