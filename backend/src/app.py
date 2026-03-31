import time
import psutil
import logging
import asyncio
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, status, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, Field

from .config import get_settings
from .validation import PromptValidator
from .errors import ErrorResponse, ErrorMessages, get_correlation_id
from .circuit_breaker import CircuitBreakerOpen, groq_circuit_breaker
from .cache import prompt_cache, video_cache, initialize_video_cache
from .rate_limiter import check_rate_limit_middleware, rate_limiter
from .prompt_expander import expand_prompt_with_fallback
from .generator import generate_code_with_retries
from .executor import render_and_concat_all, MEDIA_ROOT

# ------------------------------------------------------------
# Enhanced logging configuration
# ------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],  # Railway/Render prefers stdout logging
)
logger = logging.getLogger("manim_app")

# ------------------------------------------------------------
# Load and validate configuration
# ------------------------------------------------------------
settings = get_settings()
PORT = settings.port


# ------------------------------------------------------------
# Request/Response models
# ------------------------------------------------------------
class GenerateRequest(BaseModel):
    prompt: str = Field(
        ..., min_length=1, max_length=1500, description="Animation prompt"
    )
    quality: str = Field("m", pattern="^[lmh]$", description="Render quality: l/m/h")
    timeout: int = Field(
        150,
        ge=30,
        le=180,
        description="Timeout in seconds (capped at 180 for HF Spaces free tier)",
    )


class GenerateResponse(BaseModel):
    videoUrl: str
    renderTime: float
    codeLength: int
    expandedPrompt: Optional[str] = None
    generationMethod: Optional[str] = None  # "template" | "ai" | "fallback"


# ------------------------------------------------------------
# Global state for monitoring
# ------------------------------------------------------------
app_state = {
    "active_requests": 0,
    "total_requests": 0,
    "failed_requests": 0,
    "cache_hits": 0,
    "start_time": time.time(),
}


# ------------------------------------------------------------
# Lifespan context (non-blocking cleanup)
# ------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    logger.info("Starting Manim Animation Service")
    # Ensure media directory exists
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)

    # Initialize video cache
    initialize_video_cache(MEDIA_ROOT)
    logger.info(f"Initialized video cache at {MEDIA_ROOT}")

    # Launch cleanup task asynchronously
    asyncio.create_task(cleanup_old_files())

    # Cleanup expired cache entries
    if video_cache:
        try:
            expired = video_cache.cleanup_expired()
            logger.info(f"Cleaned up {expired} expired cache entries")
        except Exception as e:
            logger.error(f"Cache cleanup failed: {e}")

    yield
    logger.info("Shutting down Manim Animation Service")


# ------------------------------------------------------------
# FastAPI application instance
# ------------------------------------------------------------
app = FastAPI(
    title="Prompt2Frame API",
    description="""
## 🎬 Prompt2Frame - AI-Powered 2D Animation Generator

Transform text descriptions into professional 2D animations using AI and Manim.

### Features
- 🤖 AI-powered prompt expansion  
- ⚡ Smart caching (10-15x faster for duplicates)
- 🛡️ Rate limiting & security
- 🔄 Circuit breaker for resilience
- 📊 Comprehensive health checks

### Quick Start
1. Submit a prompt describing your animation
2. Receive a professional video in ~10-15 seconds
3. Download or embed the generated video

### Rate Limits
- 5 requests/minute per IP
- 20 requests/hour per IP

View detailed API documentation below.
    """,
    version="2.0.0",
    lifespan=lifespan,
)


# ------------------------------------------------------------
# Configure CORS with environment-based origins
# ------------------------------------------------------------
# ------------------------------------------------------------
# Root endpoint for easy verification
# ------------------------------------------------------------
@app.get("/")
async def root():
    """Simple status check."""
    return {
        "status": "online",
        "service": "Prompt2Frame Backend",
        "documentation": "/docs",
    }


# ------------------------------------------------------------
# Configure CORS with environment-based origins
# ------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]
    + settings.allowed_origins,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=True,
)


# ------------------------------------------------------------
# Security Headers Middleware (Phase 1.4)
# ------------------------------------------------------------
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Prevent MIME-sniffing attacks
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Note: X-Frame-Options removed to allow embedding in Hugging Face Spaces iframe

        # Enable XSS protection (legacy browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer policy for privacy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions policy (restrict features)
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )

        return response


app.add_middleware(SecurityHeadersMiddleware)


# ------------------------------------------------------------
# Middleware: Resource monitoring and rate limiting
# ------------------------------------------------------------
class EnhancedResourceGuard(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.last_check = 0
        self.cooldown = 5  # seconds between CPU checks
        self.cpu_threshold = 98
        self.memory_threshold = (
            99  # Relaxed for cloud containers (often report host memory)
        )
        self.max_concurrent = 2

    async def dispatch(self, request: Request, call_next):
        # Skip health and metrics endpoints and OPTIONS
        if (
            request.url.path in ["/", "/health", "/metrics"]
            or request.method == "OPTIONS"
        ):
            return await call_next(request)

        start_time = time.time()

        # Throttle CPU/memory checks
        current_time = time.time()
        if current_time - self.last_check < self.cooldown:
            return await call_next(request)
        self.last_check = current_time

        # Resource checks
        cpu_usage = psutil.cpu_percent(interval=0.1)
        memory_usage = psutil.virtual_memory().percent

        if cpu_usage > self.cpu_threshold:
            logger.warning(f"High CPU usage: {cpu_usage}%")
            return JSONResponse(
                {
                    "error": "Server overloaded - high CPU usage",
                    "cpu_usage": cpu_usage,
                    "retry_after": self.cooldown,
                },
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                headers={"Retry-After": str(self.cooldown)},
            )

        if memory_usage > self.memory_threshold:
            logger.warning(f"High memory usage: {memory_usage}%")
            return JSONResponse(
                {
                    "error": "Server overloaded - high memory usage",
                    "memory_usage": memory_usage,
                    "retry_after": self.cooldown,
                },
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                headers={"Retry-After": str(self.cooldown)},
            )

        # Rate limiting: max concurrent requests
        if app_state["active_requests"] >= self.max_concurrent:
            logger.warning("Too many concurrent requests")
            return JSONResponse(
                {
                    "error": "Too many concurrent requests",
                    "active_requests": app_state["active_requests"],
                    "retry_after": self.cooldown,
                },
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": str(self.cooldown)},
            )

        app_state["active_requests"] += 1
        app_state["total_requests"] += 1

        try:
            response = await call_next(request)
            elapsed = time.time() - start_time

            # Add performance headers
            response.headers["X-Response-Time"] = f"{elapsed:.3f}s"
            response.headers["X-CPU-Usage"] = f"{cpu_usage:.1f}%"
            response.headers["X-Memory-Usage"] = f"{memory_usage:.1f}%"
            return response

        except Exception as e:
            app_state["failed_requests"] += 1
            logger.error(f"Request failed: {str(e)}")
            raise
        finally:
            app_state["active_requests"] -= 1


app.add_middleware(EnhancedResourceGuard)


# ------------------------------------------------------------
# Background cleanup of old files
# ------------------------------------------------------------
async def cleanup_old_files(max_age_hours: int = 24):
    """Clean up old video files to prevent disk space issues."""
    try:
        cutoff_time = time.time() - (max_age_hours * 3600)
        deleted_count = 0
        error_count = 0

        for file_path in MEDIA_ROOT.rglob("*.mp4"):
            try:
                if file_path.stat().st_mtime < cutoff_time:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                    except PermissionError:
                        logger.warning(f"Permission denied deleting {file_path}")
                        error_count += 1
                    except OSError as e:
                        logger.warning(f"Failed to delete {file_path}: {e}")
                        error_count += 1
            except OSError as e:
                logger.warning(f"Failed to stat {file_path}: {e}")
                error_count += 1

        logger.info(
            f"Cleaned up {deleted_count} old video files ({error_count} errors)"
        )
    except Exception as e:
        logger.error(f"File cleanup failed: {e}")


# Enhanced health check endpoint (Phase 3.1)
# ------------------------------------------------------------
@app.get("/health")
async def health_check():
    """
    Comprehensive health check with dependency status.

    Returns detailed status of all critical services and resources.
    """
    import shutil
    import subprocess
    from datetime import datetime

    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "uptime_seconds": int(time.time() - app_state["start_time"]),
        "checks": {},
    }

    # Check Groq API connectivity
    try:
        from .generator import get_client  # Fix #1: now correctly exported

        get_client()  # Validates the client can be initialised
        health_status["checks"]["groq_api"] = "connected"
    except Exception as e:
        safe_msg = str(e)[:100]
        health_status["checks"]["groq_api"] = f"error: {safe_msg}"
        health_status["status"] = "degraded"

    # Check FFmpeg availability
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=2)
        if result.returncode == 0:
            health_status["checks"]["ffmpeg"] = "available"
        else:
            health_status["checks"]["ffmpeg"] = "not_found"
            health_status["status"] = "degraded"
    except FileNotFoundError:
        health_status["checks"]["ffmpeg"] = "not_installed"
        health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["ffmpeg"] = f"error: {str(e)[:30]}"

    # Check disk space
    try:
        disk = shutil.disk_usage(str(MEDIA_ROOT))
        free_gb = disk.free / (1024**3)
        total_gb = disk.total / (1024**3)
        used_percent = (disk.used / disk.total) * 100

        health_status["checks"]["disk_space"] = {
            "free_gb": round(free_gb, 2),
            "total_gb": round(total_gb, 2),
            "used_percent": round(used_percent, 1),
            "status": "ok" if free_gb > 1 else "low",
        }

        if free_gb < 1:
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["disk_space"] = f"error: {str(e)[:30]}"

    # Check cache status
    if video_cache:
        health_status["checks"]["cache"] = "operational"
        health_status["cache_stats"] = {
            "video_cache": video_cache.get_stats(),
            "prompt_cache": prompt_cache.get_stats(),
        }
    else:
        health_status["checks"]["cache"] = "not_initialized"

    # Check circuit breaker status
    health_status["checks"]["circuit_breaker"] = groq_circuit_breaker.state.value
    if groq_circuit_breaker.state.value == "open":
        health_status["status"] = "degraded"

    # Check rate limiter
    rate_limit_stats = rate_limiter.get_stats()
    health_status["checks"]["rate_limiter"] = "operational"
    health_status["rate_limit_stats"] = rate_limit_stats

    return health_status


@app.get("/ready")
async def readiness_check():
    """
    Readiness probe for K8s/container orchestration.

    Returns 200 only if service is fully operational and ready to serve traffic.
    Returns 503 if service is starting up or degraded.
    """
    import shutil
    from .generator import get_client  # Import here to ensure it's available

    try:
        # Check critical dependencies — get_client() raises RuntimeError if key is missing
        get_client()  # Validates Groq client can be initialised

        # Check disk space
        disk = shutil.disk_usage(str(MEDIA_ROOT))
        free_gb = disk.free / (1024**3)

        # Check circuit breaker
        if groq_circuit_breaker.state.value == "open":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Circuit breaker is open",
            )

        # Check minimum disk space
        if free_gb < 0.5:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Insufficient disk space",
            )

        return {"status": "ready", "message": "Service is ready to accept requests"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service not ready: {str(e)[:100]}",
        )


# ------------------------------------------------------------
# Metrics endpoint (detailed)
# ------------------------------------------------------------
@app.get("/metrics")
async def get_metrics():
    """Get application and system metrics."""
    return {
        "requests": app_state.copy(),
        "system": {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage("/").percent,
            "load_average": psutil.getloadavg()
            if hasattr(psutil, "getloadavg")
            else None,
        },
    }


# ------------------------------------------------------------
# Generate animation endpoint
# ------------------------------------------------------------
"""
PATCH for backend/src/app.py
============================
Replace ONLY the generate_animation() endpoint function (the @app.post("/generate") block).
Everything else in app.py stays the same.

Key change: if Manim rendering fails, the error is fed back to the generator
(self-healing loop) and rendering is retried up to MAX_RENDER_RETRIES times.
This is the main robustness improvement inspired by rohitg00/manim-video-generator.
"""


@app.post("/generate", response_model=GenerateResponse)
async def generate_animation(
    request: GenerateRequest,
    background_tasks: BackgroundTasks,
    _rate_limit_check: None = Depends(check_rate_limit_middleware),
):
    """
    Generate 2D Manim animation from text prompt.

    Pipeline:
    1. Validate & sanitize prompt
    2. Expand prompt (add spatial/timing detail)
    3. Generate Manim code (AI, no templates)
    4. Render video — if it fails, feed the error back to the generator
       and retry up to MAX_RENDER_RETRIES times (self-healing loop)
    """
    MAX_RENDER_RETRIES = 2  # How many times to attempt self-healing on render failure

    correlation_id = get_correlation_id()
    start_time = time.time()
    logger.info(f"[{correlation_id}] Starting generation: {request.prompt[:80]}")

    try:
        # ── Step 1: Validate ────────────────────────────────────────────
        is_valid, error_msg = PromptValidator.validate_prompt(request.prompt)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Invalid prompt", "message": error_msg},
            )
        sanitized_prompt = PromptValidator.sanitize_prompt(request.prompt)

        # ── Step 2: Expand prompt ───────────────────────────────────────
        logger.info("Expanding prompt...")
        try:
            expanded_prompt = await asyncio.wait_for(
                asyncio.create_task(
                    asyncio.to_thread(expand_prompt_with_fallback, sanitized_prompt)
                ),
                timeout=30,
            )
        except asyncio.TimeoutError:
            logger.warning("Prompt expansion timed out, using original")
            expanded_prompt = sanitized_prompt
        except Exception as e:
            logger.warning(f"Prompt expansion failed ({e}), using original")
            expanded_prompt = sanitized_prompt

        # ── Step 3 + 4: Generate code → Render → Self-heal loop ────────
        code = None
        generation_method = "ai"
        video_path = None
        render_error_ctx = None  # Carries "broken_code|||error_msg" between retries

        for render_attempt in range(1, MAX_RENDER_RETRIES + 2):
            # Generate (or re-generate with error context on retries)
            logger.info(f"Code generation, render attempt {render_attempt}")
            try:
                code, generation_method = await asyncio.wait_for(
                    asyncio.create_task(
                        asyncio.to_thread(
                            generate_code_with_retries,
                            expanded_prompt,
                            2,  # max_attempts inside generator
                            render_error_ctx,  # None on first pass, error on retries
                        )
                    ),
                    timeout=60,
                )
            except asyncio.TimeoutError:
                raise HTTPException(
                    status_code=status.HTTP_408_REQUEST_TIMEOUT,
                    detail="Code generation timed out",
                )
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Code generation failed: {str(e)}",
                )

            # Try rendering
            logger.info(f"Rendering attempt {render_attempt}...")
            try:
                video_path = await asyncio.wait_for(
                    asyncio.create_task(
                        asyncio.to_thread(
                            render_and_concat_all,
                            code,
                            request.quality,
                            request.timeout,
                        )
                    ),
                    timeout=request.timeout + 30,
                )
                logger.info(f"Render succeeded on attempt {render_attempt}")
                break  # Success — exit the retry loop

            except asyncio.TimeoutError:
                raise HTTPException(
                    status_code=status.HTTP_408_REQUEST_TIMEOUT,
                    detail="Video rendering timed out",
                )
            except Exception as render_exc:
                render_err_str = str(render_exc)
                logger.warning(
                    f"Render attempt {render_attempt} failed: {render_err_str[:200]}"
                )

                if render_attempt > MAX_RENDER_RETRIES:
                    # Exhausted all retries
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Video rendering failed after {MAX_RENDER_RETRIES + 1} attempts: {render_err_str}",
                    )

                # Build self-healing context: pass both the broken code AND the error
                render_error_ctx = f"{code}|||{render_err_str}"
                logger.info("Feeding render error back to generator (self-healing)...")

        if video_path is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Rendering did not produce a video",
            )

        # ── Step 5: Build response ──────────────────────────────────────
        try:
            relative_path = video_path.resolve().relative_to(MEDIA_ROOT.resolve())
            video_url = f"/media/videos/{relative_path.as_posix()}"
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to build video URL",
            )

        background_tasks.add_task(cleanup_old_files)
        total_time = time.time() - start_time
        logger.info(
            f"[{correlation_id}] Done in {total_time:.2f}s via '{generation_method}'"
        )

        return GenerateResponse(
            videoUrl=video_url,
            renderTime=total_time,
            codeLength=len(code) if code else 0,
            expandedPrompt=(expanded_prompt if len(expanded_prompt) < 300 else None),
            generationMethod=generation_method,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{correlation_id}] Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}",
        )


# ------------------------------------------------------------
# Static File Serving (Robust)
# ------------------------------------------------------------
from fastapi.staticfiles import StaticFiles  # noqa: E402 — must follow app creation

# Ensure media root exists
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)

# Mount media directory with CORS support implicitly handled by middleware
app.mount("/media/videos", StaticFiles(directory=str(MEDIA_ROOT)), name="videos")


# ------------------------------------------------------------
# Enhanced exception handlers with structured responses
# ------------------------------------------------------------
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    correlation_id = get_correlation_id()
    logger.warning(
        f"[{correlation_id}] HTTP {exc.status_code}: {exc.detail} - {request.url}"
    )

    # If detail is a dict, it's already structured
    if isinstance(exc.detail, dict):
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail,
            headers={"X-Correlation-ID": correlation_id},
        )

    # Otherwise create structured response
    return ErrorResponse.create(
        status_code=exc.status_code,
        error_type="HTTPError",
        message=str(exc.detail),
        correlation_id=correlation_id,
    )


@app.exception_handler(CircuitBreakerOpen)
async def circuit_breaker_handler(request: Request, exc: CircuitBreakerOpen):
    correlation_id = get_correlation_id()
    return ErrorResponse.create(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        error_type="ServiceUnavailable",
        message=ErrorMessages.GROQ_API_UNAVAILABLE,
        suggestion=ErrorMessages.SUGGEST_RETRY,
        correlation_id=correlation_id,
        details={"retry_after": 60},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    correlation_id = get_correlation_id()
    logger.error(
        f"[{correlation_id}] Unhandled exception: {str(exc)} - {request.url}",
        exc_info=True,
    )
    return ErrorResponse.create(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_type="InternalError",
        message=ErrorMessages.INTERNAL_ERROR,
        correlation_id=correlation_id,
        details={"error_type": type(exc).__name__},
    )


# ------------------------------------------------------------
# Uvicorn entry point
# ------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
        workers=1,  # Reduced to 1 for smaller/limited containers
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
