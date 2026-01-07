import uuid
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import List, Optional, Union
import ast
import logging
import time
import concurrent.futures
import os

logger = logging.getLogger(__name__)

# Use absolute path for MEDIA_ROOT
MEDIA_ROOT = Path(os.path.abspath("media/videos"))
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)

class RenderError(Exception):
    """Custom exception for rendering errors."""
    pass

class ManimRenderer:
    """Enhanced Manim renderer with better error handling and optimization."""
    
    def __init__(self, quality: str = "m", timeout: int = 300):
        self.quality = quality
        self.timeout = timeout
        self.temp_dirs = []
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup_temp_dirs()
    
    def cleanup_temp_dirs(self):
        """Clean up temporary directories."""
        for temp_dir in self.temp_dirs:
            try:
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp dir {temp_dir}: {e}")
        self.temp_dirs.clear()

def _extract_scene_names(code: str) -> List[str]:
    """
    Parse the Python AST and return all Scene subclass names in definition order.
    Enhanced with better error handling.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise RenderError(f"Invalid Python syntax in generated code: {e}")
    
    scene_names = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                if isinstance(base, ast.Name) and base.id == "Scene":
                    scene_names.append(node.name)
                elif isinstance(base, ast.Attribute) and base.attr == "Scene":
                    scene_names.append(node.name)
    
    if not scene_names:
        raise RenderError("No Scene subclasses found in generated code")
    
    logger.info(f"Found {len(scene_names)} scene(s): {', '.join(scene_names)}")
    return scene_names

def _validate_code_safety(code: str) -> None:
    """Validate code for potentially dangerous operations."""
    dangerous_patterns = [
        "import os",
        "import sys", 
        "import subprocess",
        "__import__",
        "eval(",
        "exec(",
        "open(",
        "file(",
        "input(",
        "raw_input("
    ]
    
    for pattern in dangerous_patterns:
        if pattern in code.lower():
            logger.warning(f"Potentially unsafe pattern detected: {pattern}")
            # In production, you might want to raise an error here
            # raise RenderError(f"Unsafe code pattern detected: {pattern}")

def _create_render_environment() -> Path:
    """
    Create a clean, temporary environment for rendering.
    """
    temp_dir = Path(tempfile.mkdtemp(prefix="manim_render_"))
    
    # Create subdirectories
    (temp_dir / "media").mkdir(exist_ok=True)
    (temp_dir / "scenes").mkdir(exist_ok=True)
    
    return temp_dir

def _run_manim_command(cmd: List[str], timeout: int = 300) -> tuple[int, str, str]:
    """
    Run a Manim command with proper error handling and timeout.
    """
    logger.info(f"Running command: {' '.join(cmd)}")
    process = None
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={**os.environ, "MANIM_DISABLE_CACHING": "1"}
        )
        
        stdout, stderr = process.communicate(timeout=timeout)
        return process.returncode, stdout, stderr
        
    except subprocess.TimeoutExpired:
        if process:
            try:
                process.kill()
                process.wait(timeout=5)  # Wait for process to terminate
            except subprocess.TimeoutExpired:
                process.terminate()  # Force terminate if kill doesn't work
                process.wait(timeout=5)
        stdout, stderr = process.communicate() if process else ("", "")
        raise RenderError(f"Manim command timed out after {timeout} seconds")
    except Exception as e:
        if process:
            try:
                process.kill()
                process.wait(timeout=5)
            except:
                pass
        raise RenderError(f"Failed to execute Manim command: {e}")
    finally:
        if process and process.poll() is None:
            try:
                process.kill()
                process.wait(timeout=5)
            except:
                pass

def _concatenate_videos(video_paths: List[Path], output_path: Path) -> None:
    """
    Concatenate multiple video files using ffmpeg with better error handling.
    """
    if len(video_paths) == 1:
        # Just copy the single file
        try:
            shutil.copy2(video_paths[0], output_path)
            return
        except (PermissionError, OSError) as e:
            raise RenderError(f"Failed to copy video file: {e}")
    
    # Create a temporary file list for ffmpeg
    concat_file = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            concat_file = Path(f.name)
            valid_videos = []
            for video_path in video_paths:
                if not video_path.exists():
                    logger.warning(f"Input video file not found: {video_path}")
                    continue
                
                # Check for zero-byte files
                if video_path.stat().st_size == 0:
                    logger.warning(f"Skipping empty video file: {video_path}")
                    continue
                    
                valid_videos.append(video_path)
                # Use as_posix() to ensure forward slashes, avoiding escape char issues on Windows
                f.write(f"file '{video_path.resolve().as_posix()}'\n")

            if not valid_videos:
                raise RenderError("No valid video files found to concatenate")
        
        # Try lossless concatenation first
        cmd = [
            "ffmpeg", "-y", 
            "-f", "concat", 
            "-safe", "0",
            "-i", str(concat_file),
            "-c", "copy",
            str(output_path)
        ]
        
        returncode, stdout, stderr = _run_manim_command(cmd, timeout=120)
        
        if returncode != 0:
            logger.warning("Lossless concatenation failed, trying re-encoding...")
            
            # Fallback to re-encoding
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0", 
                "-i", str(concat_file),
                "-c:v", "libx264",
                "-c:a", "aac",
                "-preset", "fast",
                str(output_path)
            ]
            
            returncode, stdout, stderr = _run_manim_command(cmd, timeout=120)
            
            if returncode != 0:
                raise RenderError(f"Video concatenation failed: {stderr}")
    
    except (PermissionError, OSError) as e:
        raise RenderError(f"Failed to concatenate videos: {e}")
    finally:
        # Clean up temporary concat file
        if concat_file and concat_file.exists():
            try:
                concat_file.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete temporary concat file: {e}")

def render_and_concat_all(
    code: str, 
    quality: str = "m", 
    timeout: int = 300
) -> Path:
    """
    Enhanced rendering function with better error handling, validation, and performance.
    
    Args:
        code: Python code containing Manim scene(s)
        quality: Render quality ("l", "m", "h")
        timeout: Maximum time allowed for rendering
        
    Returns:
        Path to the final rendered video
        
    Raises:
        RenderError: If rendering fails
    """
    start_time = time.time()
    
    # Validate inputs
    if not isinstance(code, str) or not code.strip():
        raise RenderError("Code must be a non-empty string")
    
    if quality not in ["l", "m", "h"]:
        raise RenderError(f"Invalid quality '{quality}'. Must be 'l', 'm', or 'h'")
    
    # Safety validation
    _validate_code_safety(code)
    
    # Extract scene names
    scene_names = _extract_scene_names(code)
    
    with ManimRenderer(quality, timeout) as renderer:
        # Create temporary working directory
        work_dir = _create_render_environment()
        renderer.temp_dirs.append(work_dir)
        
        # Create unique run ID
        run_id = f"{uuid.uuid4().hex}_{int(time.time())}"
        final_output_dir = MEDIA_ROOT / run_id
        final_output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Write code to script file
            script_path = work_dir / "animation_script.py"
            script_path.write_text(code, encoding="utf-8")
            
            # Setup media directory
            media_dir = work_dir / "media"
            
            # Build Manim command
            # Build Manim command
            # NOTE: We do NOT use -q/--quality here because it conflicts with some setups.
            # We rely on config.quality being set or default.
            # Actually, standard Manim CLI requires -q{quality} for quality.
            # But we must ensure NO duplicates.
            
            cmd = [
                "manim",
                "render",
                str(script_path),
                *scene_names,
                f"-q{quality}",
                "--media_dir", str(media_dir),
                "--verbosity", "WARNING",
            ]
            
            # Explicitly add only non-default flags
            if not "--disable_caching" in cmd:
                 cmd.append("--disable_caching")
            
            # Add performance optimizations
            if quality == "l":
                cmd.extend(["--frame_rate", "15"])
            
            # Execute Manim rendering
            logger.info(f"Starting Manim render for {len(scene_names)} scene(s)")
            returncode, stdout, stderr = _run_manim_command(cmd, timeout)
            
            if returncode != 0:
                error_msg = f"Manim rendering failed (exit code {returncode})"
                if stderr:
                    error_msg += f"\nError output:\n{stderr}"
                if stdout:
                    error_msg += f"\nStandard output:\n{stdout}"
                raise RenderError(error_msg)
            
            # Find generated video files
            video_files = sorted(list(media_dir.rglob("*.mp4")), key=lambda f: f.stat().st_mtime)
            if not video_files:
                raise RenderError(f"No video files generated in {media_dir}")
            
            logger.info(f"Found {len(video_files)} video file(s)")
            
            # BOUNDING: Max Clips
            MAX_CLIPS = 6
            if len(video_files) > MAX_CLIPS:
                raise RenderError(f"Render exceeded safe limits: {len(video_files)} clips produced (max {MAX_CLIPS}). Reduce animation complexity.")
            
            # Define final output path
            final_video_path = final_output_dir / "output.mp4"
            
            if len(video_files) == 1:
                # Direct copy for single clip
                logger.info("Single clip detected. Copying to final output.")
                shutil.copy2(video_files[0], final_video_path)
            else:
                # Concatenate multiple clips
                logger.info(f"Concatenating {len(video_files)} clips...")
                try:
                    _concatenate_videos(video_files, final_video_path)
                except Exception as e:
                    raise RenderError(f"Compilation failed: {str(e)}")
            
            # Verify final video and check DURATION BOUND
            if not final_video_path.exists():
                raise RenderError("Final video file was not created")
            
            # Check duration (Max 6.0s)
            MAX_DUR = 6.0
            duration = _get_video_duration(final_video_path)
            if duration > MAX_DUR:
                 raise RenderError(f"Render exceeded duration limit: {duration:.2f}s (max {MAX_DUR}s).")
            
            file_size = final_video_path.stat().st_size
            if file_size < 1024:
                raise RenderError(f"Generated video file is too small ({file_size} bytes)")
            
            elapsed_time = time.time() - start_time
            logger.info(f"Rendering completed successfully in {elapsed_time:.2f}s, output: {final_video_path}")
            
            return final_video_path
            
        except Exception as e:
            logger.error(f"Rendering failed: {str(e)}")
            # Clean up failed output directory
            if final_output_dir.exists():
                try:
                    shutil.rmtree(final_output_dir)
                except Exception:
                    pass
            raise e  # Re-raise explicit RenderError or generic Exception as is

def _get_video_duration(video_path: Path) -> float:
    """Get video duration using ffprobe."""
    try:
        cmd = [
            "ffprobe", 
            "-v", "error", 
            "-show_entries", "format=duration", 
            "-of", "default=noprint_wrappers=1:nokey=1", 
            str(video_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except Exception as e:
        logger.warning(f"Could not check duration: {e}")
        return 0.0

def _concatenate_videos(video_files: List[Path], output_path: Path):
    """
    Concatenate video files using ffmpeg concat demuxer.
    Determinisitic linking of N clips into 1.
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        for video_file in video_files:
            # Escape path for ffmpeg safe filename
            path_str = str(video_file.absolute()).replace("'", "'\\''")
            f.write(f"file '{path_str}'\n")
        list_file = f.name
    
    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", list_file,
            "-c", "copy",
            str(output_path)
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFmpeg concat failed: {e.stderr.decode() if e.stderr else str(e)}")
    finally:
        os.unlink(list_file)

def get_video_info(video_path: Path) -> dict:
    """
    Get information about a rendered video file.
    """
    if not video_path.exists():
        return {"error": "Video file not found"}
    
    try:
        stat = video_path.stat()
        return {
            "path": str(video_path),
            "size_bytes": stat.st_size,
            "size_mb": round(stat.st_size / 1024 / 1024, 2),
            "created_time": stat.st_ctime,
            "modified_time": stat.st_mtime,
        }
    except Exception as e:
        return {"error": f"Failed to get video info: {e}"}

def cleanup_old_renders(max_age_hours: int = 24, max_total_size_gb: float = 5.0):
    """
    Clean up old render directories to manage disk space.
    
    Args:
        max_age_hours: Delete files older than this many hours
        max_total_size_gb: If total size exceeds this, delete oldest first
    """
    try:
        current_time = time.time()
        cutoff_time = current_time - (max_age_hours * 3600)
        
        render_dirs = []
        total_size = 0
        
        # Collect all render directories with metadata
        for item in MEDIA_ROOT.iterdir():
            if item.is_dir():
                try:
                    dir_size = sum(f.stat().st_size for f in item.rglob('*') if f.is_file())
                    dir_mtime = max((f.stat().st_mtime for f in item.rglob('*') if f.is_file()), default=0)
                    
                    render_dirs.append({
                        'path': item,
                        'size': dir_size,
                        'mtime': dir_mtime,
                        'age_hours': (current_time - dir_mtime) / 3600
                    })
                    total_size += dir_size
                except Exception:
                    continue
        
        deleted_count = 0
        freed_space = 0
        
        # Sort by modification time (oldest first)
        render_dirs.sort(key=lambda x: x['mtime'])
        
        # Delete old directories
        for dir_info in render_dirs:
            should_delete = False
            
            # Delete if too old
            if dir_info['mtime'] < cutoff_time:
                should_delete = True
                reason = f"older than {max_age_hours} hours"
            
            # Delete oldest if total size too large
            elif total_size > max_total_size_gb * 1024 * 1024 * 1024:
                should_delete = True
                reason = f"total size exceeded {max_total_size_gb}GB"
            
            if should_delete:
                try:
                    shutil.rmtree(dir_info['path'])
                    deleted_count += 1
                    freed_space += dir_info['size']
                    total_size -= dir_info['size']
                    logger.info(f"Deleted render directory {dir_info['path'].name} ({reason})")
                except Exception as e:
                    logger.warning(f"Failed to delete {dir_info['path']}: {e}")
        
        if deleted_count > 0:
            logger.info(f"Cleanup completed: deleted {deleted_count} directories, freed {freed_space / 1024 / 1024:.1f} MB")
        
        return {
            "deleted_directories": deleted_count,
            "freed_space_mb": round(freed_space / 1024 / 1024, 1),
            "remaining_directories": len(render_dirs) - deleted_count,
            "total_size_mb": round(total_size / 1024 / 1024, 1)
        }
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return {"error": str(e)}