import os
import uuid
import subprocess
import ast
from pathlib import Path

MEDIA_ROOT = Path("media/videos")

def execute_manim_code(
    code: str,
    scene_name: str,
    quality: str = "l",     # one of 'l','m','h','p','k'
    timeout: int = 300
) -> Path:
    """
    1) Syntax-check the code.
    2) Write it to run_dir/scene.py.
    3) Call manim with media_dir=run_dir/media.
    4) Find the generated .mp4 anywhere under run_dir.
    """
    # 1) Syntax validation
    try:
        ast.parse(code)
    except SyntaxError as e:
        raise RuntimeError(f"Generated code has a syntax error: {e}")

    # 2) Prepare directories
    run_id = uuid.uuid4().hex
    run_dir = MEDIA_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    scene_py = run_dir / "scene.py"
    scene_py.write_text(code, encoding="utf-8")

    # 3) Invoke Manim
    #    We pass media_dir=run_dir/media so all outputs live under there.
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
            raise RuntimeError(f"Manim failed:\n{proc.stderr.strip()}")
    except subprocess.TimeoutExpired:
        raise RuntimeError("Manim rendering timed out")
    except Exception as e:
        raise RuntimeError(f"Error during Manim invocation: {e}")

    # 4) Discover the .mp4
    mp4_files = list(run_dir.rglob("*.mp4"))
    if not mp4_files:
        raise RuntimeError(
            f"No .mp4 found under {run_dir!r} after rendering"
        )

    # Pick the largest (in case Manim also wrote thumbnail .mp4)
    video = max(mp4_files, key=lambda p: p.stat().st_size)
    return video
