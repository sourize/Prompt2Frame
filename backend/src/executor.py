import os
import uuid
import subprocess
import ast
import re
from pathlib import Path

MEDIA_ROOT = Path("media/videos")

def _extract_scene_name(code: str) -> str:
    """
    Parse the code’s AST to find the first class that inherits from Scene,
    and return its name. Raises if none found.
    """
    tree = ast.parse(code)
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                # looking for Scene or something.Scene
                if (
                    isinstance(base, ast.Name) and base.id == "Scene"
                ) or (
                    isinstance(base, ast.Attribute) and base.attr == "Scene"
                ):
                    return node.name
    raise RuntimeError("Could not find a Scene subclass in generated code")

def execute_manim_code(
    code: str,
    scene_name: str | None = None,
    quality: str = "l",     # one of 'l','m','h','p','k'
    timeout: int = 300
) -> Path:
    """
    1) Rewrite any stray `.animate.set_points(...)` into Transform(...)
    2) If scene_name not given, extract it from the code
    3) Syntax-check the code.
    4) Write it to run_dir/scene.py.
    5) Call manim with media_dir=run_dir/media.
    6) Find and return the generated .mp4.
    """
    # ── 1) Rewrite bad set_points animations ──────────────────────────────────
    bad_pattern = re.compile(
        r'(\w+)\.animate\.set_points\(\s*(Square\([^)]*\))\s*\)'
    )
    def _rewrite(match):
        obj = match.group(1)
        ctor = match.group(2)
        return f"Transform({obj}, {ctor})"
    code = re.sub(bad_pattern, _rewrite, code)

    # ── 2) Determine scene_name ───────────────────────────────────────────────
    if scene_name is None:
        scene_name = _extract_scene_name(code)

    # ── 3) Syntax validation ─────────────────────────────────────────────────
    try:
        ast.parse(code)
    except SyntaxError as e:
        raise RuntimeError(f"Generated code has a syntax error: {e}")

    # ── 4) Prepare dirs & write scene.py ─────────────────────────────────────
    run_id = uuid.uuid4().hex
    run_dir = MEDIA_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    scene_py = run_dir / "scene.py"
    scene_py.write_text(code, encoding="utf-8")

    # ── 5) Invoke manim ──────────────────────────────────────────────────────
    media_dir = run_dir / "media"
    media_dir.mkdir(exist_ok=True, parents=True)
    cmd = [
        "manim", "render",
        str(scene_py),
        scene_name,
        f"-q{quality}",
        "--disable_caching",
        "--media_dir", str(media_dir),
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        if proc.returncode != 0:
            stderr = proc.stderr or ""
            # handle known errors
            if "Camera' object has no attribute 'frame" in stderr:
                raise RuntimeError("Unsupported camera operation: camera.frame")
            if "Unexpected argument False passed to Scene.play" in stderr:
                raise RuntimeError("Invalid play() arguments in scene code")
            if "Called Scene.play with no animations" in stderr:
                raise RuntimeError("Scene.play() was called with no animations")
            if "'float' object is not subscriptable" in stderr:
                raise RuntimeError("Invalid geometry arguments (floats used incorrectly)")
            # fallback
            raise RuntimeError(f"Manim failed:\n{stderr.strip()}")
    except subprocess.TimeoutExpired:
        raise RuntimeError("Manim rendering timed out")
    except Exception as e:
        raise RuntimeError(f"Error during Manim invocation: {e}")

    # ── 6) Find and return the .mp4 ──────────────────────────────────────────
    mp4_files = list(run_dir.rglob("*.mp4"))
    if not mp4_files:
        raise RuntimeError(f"No .mp4 found under {run_dir!r} after rendering")
    # largest one is usually final
    return max(mp4_files, key=lambda p: p.stat().st_size)

def concat_videos(video_paths: list[Path], final_name: str = None) -> Path:
    """
    Concatenate mp4s into one file. Fallback to re-encode if copy fails.
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

    # fast concat
    try:
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(parts_txt),
            "-c", "copy",
            str(final_mp4),
        ], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError:
        # fallback re-encode
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(parts_txt),
            "-c:v", "libx264", "-c:a", "aac",
            str(final_mp4),
        ], check=True, capture_output=True, text=True)

    if not final_mp4.exists():
        raise RuntimeError("FFmpeg failed to produce final.mp4")
    return final_mp4
