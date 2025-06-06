import time
import psutil
import logging
import asyncio
import os
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, Field

from .prompt_expander import expand_prompt
from .generator import generate_manim_code_with_fallback
from .executor import render_and_concat_all, MEDIA_ROOT

# Enhanced logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()  # Railway prefers stdout logging
    ]
)

logger = logging.getLogger("manim_app")

# Get port from environment variable (Railway requirement)
PORT = int(os.getenv("PORT", 8000))

# Request/Response models
class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=500, description="Animation prompt")
    quality: str = Field("m", pattern="^[lmh]$", description="Render quality: l/m/h")
    timeout: int = Field(300, ge=60, le=600, description="Timeout in seconds")

class GenerateResponse(BaseModel):
    videoUrl: str
    renderTime: float
    codeLength: int
    expandedPrompt: Optional[str] = None

# Global state for monitoring
app_state = {
    "active_requests": 0,
    "total_requests": 0,
    "failed_requests": 0,
    "cache_hits": 0,
    "start_time": time.time()
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Manim Animation Service")
    
    # Ensure media directory exists
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    
    # Clean up old files on startup
    await cleanup_old_files()
    
    yield
    
    logger.info("Shutting down Manim Animation Service")

app = FastAPI(
    title="Manim Animation Generator",
    description="Generate Manim animations from text prompts",
    version="2.0.0",
    lifespan=lifespan
)

# Configure CORS for Railway
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend domain
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=True,
)

class EnhancedResourceGuard(BaseHTTPMiddleware):
    """Enhanced middleware for resource monitoring and rate limiting."""
    
    def __init__(self, app):
        super().__init__(app)
        self.last_check = 0
        self.cooldown = 5  # seconds between CPU checks
        self.cpu_threshold = 95  # Increased threshold
        self.memory_threshold = 90
        self.max_concurrent = 2  # Reduced from 3 to 2
    
    async def dispatch(self, request: Request, call_next):
        # Skip health checks and OPTIONS requests
        if request.url.path in ["/health", "/metrics"] or request.method == "OPTIONS":
            return await call_next(request)
        
        start_time = time.time()
        
        # Add cooldown period for CPU checks
        current_time = time.time()
        if current_time - self.last_check < self.cooldown:
            return await call_next(request)
        self.last_check = current_time
        
        # Resource checks with exponential backoff
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
        
        # Rate limiting - max 2 concurrent requests
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
            
            # Check for timeout
            elapsed = time.time() - start_time
            if elapsed > 300:
                logger.error(f"Request timeout: {elapsed:.2f}s")
                return JSONResponse(
                    {"error": "Request timed out", "elapsed_time": elapsed},
                    status_code=status.HTTP_408_REQUEST_TIMEOUT
                )
            
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
                        logger.warning(f"Permission denied when deleting {file_path}")
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

@app.get("/health")
async def health_check():
    """Enhanced health check with system metrics and startup verification."""
    try:
        logger.info("Health check started")
        
        # Basic application state check
        if not hasattr(app, 'state'):
            logger.error("Application state not initialized")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Application not initialized"
            )
        
        # Check if media directory exists and is writable
        if not MEDIA_ROOT.exists():
            logger.error(f"Media directory does not exist at {MEDIA_ROOT}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Media directory not found at {MEDIA_ROOT}"
            )
            
        if not os.access(MEDIA_ROOT, os.W_OK):
            logger.error(f"Media directory is not writable: {MEDIA_ROOT}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Media directory not writable: {MEDIA_ROOT}"
            )
        
        # Test file operations
        test_file = MEDIA_ROOT / "health_check.txt"
        try:
            test_file.touch()
            test_file.unlink()
            logger.info("File system operations successful")
        except Exception as e:
            logger.error(f"File system operations failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"File system operations failed: {str(e)}"
            )
        
        # Get system metrics
        try:
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            logger.info(f"System metrics - CPU: {cpu_percent}%, Memory: {memory.percent}%, Disk: {disk.percent}%")
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to get system metrics: {str(e)}"
            )
        
        # Check if we can access the application state
        try:
            app_state_copy = app_state.copy()
            logger.info("Application state check successful")
        except Exception as e:
            logger.error(f"Failed to access application state: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to access application state: {str(e)}"
            )
        
        response = {
            "status": "healthy",
            "timestamp": time.time(),
            "uptime": time.time() - app_state["start_time"],
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": disk.percent,
            },
            "app_state": app_state_copy,
            "media_root": str(MEDIA_ROOT),
            "python_path": os.environ.get("PYTHONPATH", ""),
            "working_directory": os.getcwd()
        }
        
        logger.info("Health check completed successfully")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Health check failed with unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Health check failed: {str(e)}"
        )

@app.get("/metrics")
async def get_metrics():
    """Get application metrics."""
    return {
        "requests": app_state.copy(),
        "system": {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage("/").percent,
            "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None,
        }
    }

@app.post("/generate", response_model=GenerateResponse)
async def generate_animation(
    request: GenerateRequest,
    background_tasks: BackgroundTasks
):
    """Generate Manim animation from prompt with enhanced error handling."""
    start_time = time.time()
    
    logger.info(f"Starting generation for prompt: {request.prompt[:100]}...")
    
    try:
        # 1) Expand the prompt
        logger.info("Expanding prompt...")
        try:
            detailed_prompt = await asyncio.wait_for(
                asyncio.create_task(asyncio.to_thread(expand_prompt, request.prompt)),
                timeout=30
            )
            logger.info("Prompt expansion completed")
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
            logger.info(f"Code generation completed ({len(code)} characters)")
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

        # Calculate relative path for serving
        try:
            relative_path = video_path.resolve().relative_to(MEDIA_ROOT.resolve())
            video_url = f"/media/videos/{relative_path.as_posix()}"
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate video URL"
            )

        # Schedule cleanup of temporary files
        background_tasks.add_task(cleanup_old_files)

        render_time = time.time() - start_time
        logger.info(f"Generation completed successfully in {render_time:.2f}s")

        return GenerateResponse(
            videoUrl=video_url,
            renderTime=render_time,
            codeLength=len(code),
            expandedPrompt=detailed_prompt if len(detailed_prompt) < 200 else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in generation pipeline: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )

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
    
    # Get file size for range requests
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

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler with logging."""
    logger.warning(f"HTTP {exc.status_code}: {exc.detail} - {request.url}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unhandled exception: {str(exc)} - {request.url}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error", "status_code": 500}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
        workers=4,
        proxy_headers=True,
        forwarded_allow_ips="*"
    )
