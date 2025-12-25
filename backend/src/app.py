import time
import psutil
import logging
import asyncio
import os
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status, BackgroundTasks, Depends
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, Field

from .config import get_settings
from .validation import PromptValidator, CodeSecurityValidator
from .errors import ErrorResponse, ErrorMessages, get_correlation_id
from .circuit_breaker import CircuitBreakerOpen, groq_circuit_breaker
from .cache import prompt_cache, video_cache, initialize_video_cache
from .rate_limiter import check_rate_limit_middleware, rate_limiter
from .prompt_expander import expand_prompt
from .generator import generate_manim_code_with_fallback
from .executor import render_and_concat_all, MEDIA_ROOT

# ------------------------------------------------------------
# Enhanced logging configuration
# ------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]  # Railway/Render prefers stdout logging
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
    prompt: str = Field(..., min_length=1, max_length=500, description="Animation prompt")
    quality: str = Field("m", pattern="^[lmh]$", description="Render quality: l/m/h")
    timeout: int = Field(300, ge=60, le=600, description="Timeout in seconds")

class GenerateResponse(BaseModel):
    videoUrl: str
    renderTime: float
    codeLength: int
    expandedPrompt: Optional[str] = None

# ------------------------------------------------------------
# Global state for monitoring
# ------------------------------------------------------------
app_state = {
    "active_requests": 0,
    "total_requests": 0,
    "failed_requests": 0,
    "cache_hits": 0,
    "start_time": time.time()
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
    lifespan=lifespan
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
        "documentation": "/docs"
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
        "http://127.0.0.1:8080"
    ] + settings.allowed_origins,
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
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
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
        self.memory_threshold = 99  # Relaxed for cloud containers (often report host memory)
        self.max_concurrent = 2

    async def dispatch(self, request: Request, call_next):
        # Skip health and metrics endpoints and OPTIONS
        if request.url.path in ["/", "/health", "/metrics"] or request.method == "OPTIONS":
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
                    "retry_after": self.cooldown
                },
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                headers={"Retry-After": str(self.cooldown)}
            )

        if memory_usage > self.memory_threshold:
            logger.warning(f"High memory usage: {memory_usage}%")
            return JSONResponse(
                {
                    "error": "Server overloaded - high memory usage",
                    "memory_usage": memory_usage,
                    "retry_after": self.cooldown
                },
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                headers={"Retry-After": str(self.cooldown)}
            )

        # Rate limiting: max concurrent requests
        if app_state["active_requests"] >= self.max_concurrent:
            logger.warning("Too many concurrent requests")
            return JSONResponse(
                {
                    "error": "Too many concurrent requests",
                    "active_requests": app_state["active_requests"],
                    "retry_after": self.cooldown
                },
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": str(self.cooldown)}
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

        logger.info(f"Cleaned up {deleted_count} old video files ({error_count} errors)")
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
    from datetime import datetime, timedelta
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "uptime_seconds": int(time.time() - app_state["start_time"]),
        "checks": {}
    }
    
    # Check Groq API connectivity
    try:
        from .generator import get_client
        client = get_client()
        # Simple connectivity test (doesn't count against rate limits)
        health_status["checks"]["groq_api"] = "connected"
    except Exception as e:
        health_status["checks"]["groq_api"] = f"error: {str(e)[:50]}"
        health_status["status"] = "degraded"
    
    # Check FFmpeg availability
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            timeout=2
        )
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
            "status": "ok" if free_gb > 1 else "low"
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
            "prompt_cache": prompt_cache.get_stats()
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
    from .generator import get_client # Import here to ensure it's available
    
    try:
        # Check critical dependencies
        client = get_client()  # Ensures Groq client initialized
        
        # Check disk space
        disk = shutil.disk_usage(str(MEDIA_ROOT))
        free_gb = disk.free / (1024**3)
        
        # Check circuit breaker
        if groq_circuit_breaker.state.value == "open":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Circuit breaker is open"
            )
        
        # Check minimum disk space
        if free_gb < 0.5:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Insufficient disk space"
            )
        
        return {
            "status": "ready",
            "message": "Service is ready to accept requests"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service not ready: {str(e)[:100]}"
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
            "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None,
        }
    }

# ------------------------------------------------------------
# Generate animation endpoint
# ------------------------------------------------------------
@app.post("/generate", response_model=GenerateResponse)
async def generate_animation(
    request: GenerateRequest,
    background_tasks: BackgroundTasks,
    _rate_limit_check: None = Depends(check_rate_limit_middleware)  # Rate limiting
):
    """
    Generate 2D Manim animation from text prompt.
    
    This endpoint takes a textual description and generates a professional 2D animation
    video using the Manim library. The process includes:
    1. Prompt expansion for detailed descriptions
    2. AI-powered code generation
    3. Video rendering with Manim
    
    **Rate Limits:**
    - 5 requests per minute per IP
    - 20 requests per hour per IP
    
    **Caching:**
    - Duplicate prompts return cached videos instantly (<1s)
    - Prompt expansions are cached for 24 hours
    - Videos are cached for 7 days
    
    **Args:**
    - prompt (str): Description of the animation (3-500 characters)
    - quality (str): Video quality - 'l' (low), 'm' (medium), 'h' (high)
    - timeout (int): Maximum generation time in seconds (default: 300)
    
    **Returns:**
    - videoUrl: Relative URL to the generated video
    - renderTime: Total generation time in seconds
    - codeLength: Length of generated Manim code
    - expandedPrompt: Enhanced prompt description (if <200 chars)
    
    **Example Request:**
    ```json
    {
        "prompt": "A blue circle transforming into a red square",
        "quality": "m",
        "timeout": 300
    }
    ```
    
    **Example Success Response (200):**
    ```json
    {
        "videoUrl": "/media/videos/abc123/final_animation.mp4",
        "renderTime": 12.45,
        "codeLength": 523,
        "expandedPrompt": "Create a smooth animation where..."
    }
    ```
    
    **Error Responses:**
    - 400: Invalid prompt (too short, too long, dangerous content)
    - 408: Request timeout (generation took too long)
    - 429: Rate limit exceeded (too many requests)
    - 500: Internal server error (code generation or rendering failed)
    - 503: Service unavailable (circuit breaker open)
    
    **Example Error Response (429):**
    ```json
    {
        "error": "Rate limit exceeded",
        "message": "Too many requests. Limit: minute",
        "retry_after": 42,
        "suggestion": "Please wait 42 seconds before trying again."
    }
    ```
    """
    correlation_id = get_correlation_id()
    start_time = time.time()
    logger.info(
        f"[{correlation_id}] Starting generation for prompt: {request.prompt[:100]}..."
    )

    try:
        # === PHASE 1.2: Input Validation ===
        # Validate and sanitize prompt
        is_valid, error_msg = PromptValidator.validate_prompt(request.prompt)
        if not is_valid:
            logger.warning(f"Prompt validation failed: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Invalid prompt",
                    "message": error_msg,
                    "suggestion": "Please provide a descriptive prompt for a 2D animation."
                }
            )
        
        # Sanitize the prompt
        sanitized_prompt = PromptValidator.sanitize_prompt(request.prompt)
        
        # === PHASE 2.1: Check Video Cache ===
        if video_cache:
            cached_video_path = video_cache.get(sanitized_prompt, request.quality)
            if cached_video_path:
                # Video already generated!
                app_state["cache_hits"] += 1
                render_time = time.time() - start_time
                logger.info(
                    f"[{correlation_id}] ⚡ CACHE HIT! Returning cached video in {render_time:.2f}s"
                )
                return GenerateResponse(
                    videoUrl=f"/media/videos/{Path(cached_video_path).parent.name}/{Path(cached_video_path).name}",
                    renderTime=render_time,
                    codeLength=0,  # Not re-generated
                    expandedPrompt=None
                )
        
        # === PHASE 2.1: Check Prompt Cache ===
        cached_expansion = prompt_cache.get(sanitized_prompt)
        if cached_expansion:
            detailed_prompt = cached_expansion
            logger.info(f"[{correlation_id}] ⚡ Prompt cache HIT, using cached expansion")
        else:
            # 1) Expand the prompt (using sanitized version)
            logger.info("Expanding prompt...")
            try:
                detailed_prompt = await asyncio.wait_for(
                    asyncio.create_task(asyncio.to_thread(expand_prompt, sanitized_prompt)),
                    timeout=30
                )
                logger.info("Prompt expansion completed")
                
                # Cache the expansion
                prompt_cache.set(sanitized_prompt, detailed_prompt)
                logger.debug(f"Cached prompt expansion")
            except asyncio.TimeoutError:
                raise HTTPException(
                    status_code=status.HTTP_408_REQUEST_TIMEOUT,
                    detail="Prompt expansion timed out"
                )
            except Exception as e:
                logger.error(f"Prompt expansion failed: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Prompt expansion failed: {str(e)}"
                )

        # 2) Generate Manim code
        logger.info("Generating Manim code...")
        try:
            code = await asyncio.wait_for(
                asyncio.create_task(asyncio.to_thread(generate_manim_code_with_fallback, detailed_prompt)),
                timeout=60
            )
            logger.info(f"Code generation completed ({len(code)} chars)")
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                detail="Code generation timed out"
            )
        except Exception as e:
            logger.error(f"Code generation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Code generation failed: {str(e)}"
            )

        # 3) Render video
        logger.info("Starting video rendering...")
        try:
            video_path = await asyncio.wait_for(
                asyncio.create_task(asyncio.to_thread(render_and_concat_all, code, request.quality, request.timeout)),
                timeout=request.timeout + 30
            )
            logger.info(f"Video rendering completed: {video_path}")
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                detail="Video rendering timed out"
            )
        except Exception as e:
            logger.error(f"Video rendering failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Video rendering failed: {str(e)}"
            )

        # 4) Build video URL
        try:
            relative_path = video_path.resolve().relative_to(MEDIA_ROOT.resolve())
            video_url = f"/media/videos/{relative_path.as_posix()}"
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate video URL"
            )

        # Schedule cleanup of old files
        background_tasks.add_task(cleanup_old_files)
        # Calculate total time
        total_time = time.time() - start_time
        
        # === PHASE 2.1: Cache the Generated Video ===
        if video_cache:
            try:
                video_cache.set(sanitized_prompt, str(video_path), request.quality)
                logger.info(f"[{correlation_id}] ✔ Video cached for future requests")
            except Exception as e:
                logger.error(f"Failed to cache video: {e}")
        
        logger.info(f"Generation completed in {total_time:.2f}s")

        return GenerateResponse(
            videoUrl=video_url,
            renderTime=total_time,
            codeLength=len(code),
            expandedPrompt=(detailed_prompt if len(detailed_prompt) < 200 else None)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in generation pipeline: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )

# ------------------------------------------------------------
# Serve generated video files
# ------------------------------------------------------------
@app.get("/media/videos/{path:path}")
async def serve_video(path: str):
    """Serve generated video files with proper headers."""
    file_path = MEDIA_ROOT / path

    if not file_path.exists():
        logger.warning(f"Video file not found: {file_path}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video file not found"
        )

    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path"
        )

    file_size = file_path.stat().st_size

    return FileResponse(
        str(file_path),
        media_type="video/mp4",
        headers={
            "Cache-Control": "public, max-age=3600",
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
            "X-Content-Type-Options": "nosniff"
        }
    )

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
            headers={"X-Correlation-ID": correlation_id}
        )
    
    # Otherwise create structured response
    return ErrorResponse.create(
        status_code=exc.status_code,
        error_type="HTTPError",
        message=str(exc.detail),
        correlation_id=correlation_id
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
        details={"retry_after": 60}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    correlation_id = get_correlation_id()
    logger.error(
        f"[{correlation_id}] Unhandled exception: {str(exc)} - {request.url}",
        exc_info=True
    )
    return ErrorResponse.create(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_type="InternalError",
        message=ErrorMessages.INTERNAL_ERROR,
        correlation_id=correlation_id,
        details={"error_type": type(exc).__name__}
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
        workers=1,              # Reduced to 1 for smaller/limited containers
        proxy_headers=True,
        forwarded_allow_ips="*"
    )
