import os
import uuid
import subprocess
import ast
import re
from pathlib import Path

MEDIA_ROOT = Path("media/videos")

def execute_manim_code(
    code: str,
    scene_name: str,
    quality: str = "l",     # one of 'l','m','h','p','k'
    timeout: int = 300
) -> Path:
    """
    1) Pre-rewrite any `.animate.set_points(...)` patterns into Transform calls.
    2) Syntax-check the code.
    3) Write it to run_dir/scene.py.
    4) Call manim with media_dir=run_dir/media.
    5) Find the generated .mp4 anywhere under run_dir.
    """
    # ── 1) Rewrite bad set_points animations ──────────────────────────────────
    # Pattern: <obj>.animate.set_points(Square(...))
    bad_pattern = re.compile(
        r'(\w+)\.animate\.set_points\(\s*(Square\([^)]*\))\s*\)'
    )
    def _rewrite_set_points(match):
        obj = match.group(1)
        square_ctor = match.group(2)
        # Replace with a Transform(obj, Square(...))
        return f'Transform({obj}, {square_ctor})'
    code = re.sub(bad_pattern, _rewrite_set_points, code)

    # ── 2) Syntax validation ─────────────────────────────────────────────────
    try:
        ast.parse(code)
    except SyntaxError as e:
        raise RuntimeError(f"Generated code has a syntax error: {e}")

    # ── 3) Prepare directories & write scene.py ──────────────────────────────
    run_id = uuid.uuid4().hex
    run_dir = MEDIA_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    scene_py = run_dir / "scene.py"
    scene_py.write_text(code, encoding="utf-8")

    # ── 4) Invoke Manim ──────────────────────────────────────────────────────
    media_dir = run_dir / "media"
    media_dir.mkdir(exist_ok=True, parents=True)
    cmd = [
        "manim", "render",
        str(scene_py),
        scene_name,
        f"-q{quality}",              # e.g. '-ql'
        "--disable_caching",
        "--media_dir", str(media_dir),
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        if proc.returncode != 0:
            stderr = proc.stderr or ""
            # Known failure modes:
            if "Camera' object has no attribute 'frame" in stderr:
                raise RuntimeError("Unsupported camera operation: camera.frame")
            if "Unexpected argument False passed to Scene.play" in stderr:
                raise RuntimeError("Invalid play() arguments in scene code")
            if "ValueError(\"Called Scene.play with no animations" in stderr:
                raise RuntimeError("Scene.play() was called with no animations")
            if "'float' object is not subscriptable" in stderr:
                raise RuntimeError("Invalid geometry arguments (floats used incorrectly)")
            # Fallback:
            raise RuntimeError(f"Manim failed:\n{stderr.strip()}")
    except subprocess.TimeoutExpired:
        raise RuntimeError("Manim rendering timed out")
    except Exception as e:
        raise RuntimeError(f"Error during Manim invocation: {e}")

    # ── 5) Discover the .mp4 ─────────────────────────────────────────────────
    mp4_files = list(run_dir.rglob("*.mp4"))
    if not mp4_files:
        raise RuntimeError(f"No .mp4 found under {run_dir!r} after rendering")
    # Return the largest file (usually the final video)
    video = max(mp4_files, key=lambda p: p.stat().st_size)
    return video

def concat_videos(video_paths: list[Path], final_name: str = None) -> Path:
    """
    Concatenate a list of mp4s into one. Fallback to re-encode if 'copy' fails.
    Returns the Path to final.mp4.
    """
    run_id = uuid.uuid4().hex
    target_dir = MEDIA_ROOT / run_id
    target_dir.mkdir(parents=True, exist_ok=True)

    parts_txt = target_dir / "parts.txt"
    with parts_txt.open("w") as f:
        for vp in video_paths:
            f.write(f"file '{vp.resolve()}'\n")

    final_mp4 = target_dir / (final_name or "final.mp4")

    # Try fast concat
    try:
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(parts_txt),
            "-c", "copy",
            str(final_mp4),
        ], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError:
        # Fallback: re-encode for compatibility
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(parts_txt),
            "-c:v", "libx264", "-c:a", "aac",
            str(final_mp4),
        ], check=True, capture_output=True, text=True)

    if not final_mp4.exists():
        raise RuntimeError("FFmpeg failed to produce final.mp4")
    return final_mp4
