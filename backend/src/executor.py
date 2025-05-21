import uuid
import subprocess
import ast
from pathlib import Path

# ──────────────────────────────────────────────────────────────────────────────
# Media root: generated videos will live under here
MEDIA_ROOT = Path("media/videos")
# ──────────────────────────────────────────────────────────────────────────────

def _check_balanced_delimiters(code: str):
    pairs = {"(": ")", "[": "]", "{": "}"}
    for o, c in pairs.items():
        if code.count(o) != code.count(c):
            raise RuntimeError(
                f"Unmatched delimiters: {code.count(o)} ‘{o}’ vs {code.count(c)} ‘{c}’"
            )

def execute_manim_code(
    code: str,
    scene_name: str,
    quality: str = "l",
    timeout: int = 300
) -> Path:
    """
    1) Quick delimiter check
    2) AST-validate (syntax & indent)
    3) Write to unique run_dir/scene.py
    4) Call `manim render`
    5) Return the largest .mp4 under that run_dir
    """
    # 1) Delimiters
    _check_balanced_delimiters(code)

    # 2) Syntax & indentation
    try:
        ast.parse(code)
    except IndentationError as ie:
        raise RuntimeError(f"Generated code has an indentation error: {ie}")
    except SyntaxError as se:
        raise RuntimeError(f"Generated code has a syntax error: {se}")

    # 3) Prepare run directory
    run_id = uuid.uuid4().hex
    run_dir = MEDIA_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    scene_py = run_dir / "scene.py"
    scene_py.write_text(code, encoding="utf-8")

    # 4) Invoke Manim
    media_dir = run_dir / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "manim", "render",
        str(scene_py),
        scene_name,
        f"-q{quality}",
        "--disable_caching",
        "--media_dir", str(media_dir),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if proc.returncode != 0:
            err = proc.stderr or ""
            # map known errors
            if "Camera' object has no attribute 'frame" in err:
                raise RuntimeError("Unsupported camera operation: camera.frame")
            if "Unexpected argument False passed to Scene.play" in err:
                raise RuntimeError("Invalid play() arguments in scene code")
            if "Called Scene.play with no animations" in err:
                raise RuntimeError("Scene.play() was called with no animations")
            if "'float' object is not subscriptable" in err:
                raise RuntimeError("Invalid geometry arguments (floats used incorrectly)")
            # fallback
            raise RuntimeError(f"Manim failed:\n{err.strip()}")
    except subprocess.TimeoutExpired:
        raise RuntimeError("Manim rendering timed out")
    except Exception as e:
        raise RuntimeError(f"Error during Manim invocation: {e}")

    # 5) Locate output .mp4
    mp4s = list(run_dir.rglob("*.mp4"))
    if not mp4s:
        raise RuntimeError(f"No .mp4 found under {run_dir!r} after rendering")
    # return the largest (by size)
    return max(mp4s, key=lambda p: p.stat().st_size)


def concat_videos(video_paths: list[Path], final_name: str = None) -> Path:
    """
    Fast-concat (copy) or fall back to re-encode via ffmpeg.
    Returns the final .mp4 Path.
    """
    run_id = uuid.uuid4().hex
    target_dir = MEDIA_ROOT / run_id
    target_dir.mkdir(parents=True, exist_ok=True)

    parts = target_dir / "parts.txt"
    with parts.open("w") as f:
        for vp in video_paths:
            f.write(f"file '{vp.resolve()}'\n")

    out = target_dir / (final_name or "final.mp4")

    # try stream copy
    try:
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(parts),
            "-c", "copy", str(out),
        ], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError:
        # fallback re-encode
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(parts),
            "-c:v", "libx264", "-c:a", "aac",
            str(out),
        ], check=True, capture_output=True, text=True)

    if not out.exists():
        raise RuntimeError("FFmpeg failed to produce the concatenated video")
    return out


def render_and_concat_all(
    scenes: list[dict],
    quality: str = "l",
    timeout: int = 300
) -> Path:
    """
    Given a list of {"name": str, "code": str} scenes:
      • Renders each via execute_manim_code
      • If one scene, returns its Path
      • If multiple, concatenates them into one final.mp4 and returns that Path
    """
    videos = []
    for idx, sc in enumerate(scenes, start=1):
        name = sc.get("name")
        code = sc.get("code")
        if not name or not code:
            raise RuntimeError(f"Scene #{idx} missing name or code")
        video_path = execute_manim_code(code, name, quality=quality, timeout=timeout)
        videos.append(video_path)

    if not videos:
        raise RuntimeError("No videos were rendered")

    if len(videos) == 1:
        return videos[0]
    # else, join them
    return concat_videos(videos)
