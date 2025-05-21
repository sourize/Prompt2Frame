# executor.py
import uuid, subprocess, ast, re
from pathlib import Path

MEDIA_ROOT = Path("media/videos")
_SCENE_NAME_RE = re.compile(r"class\s+(\w+)\s*\(\s*Scene\s*\)")

def execute_manim_code(code: str, quality="l", timeout=300) -> list[Path]:
    """
    Write `code` to a new run folder, invoke Manim *once* (it will render
    every Scene subclass), then return the list of generated MP4s in the
    order the classes appeared in the file.
    """
    # syntax check
    try:
        ast.parse(code)
    except SyntaxError as e:
        raise RuntimeError(f"Syntax error in generated code: {e}")

    run_id = uuid.uuid4().hex
    run_dir = MEDIA_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    scene_py = run_dir / "scene.py"
    scene_py.write_text(code, encoding="utf-8")

    media_dir = run_dir / "media"
    media_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "manim", "render", str(scene_py),
        "-q"+quality, "--disable_caching",
        "--media_dir", str(media_dir),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        stderr = proc.stderr or ""
        # ... same error‐pattern handling as before ...
        raise RuntimeError(f"Manim failed:\n{stderr.strip()}")

    # parse scene order
    names = _SCENE_NAME_RE.findall(code)
    # collect MP4s and map by scene name
    all_mp4 = {p.stem: p for p in run_dir.rglob("*.mp4")}
    ordered = []
    for nm in names:
        if nm in all_mp4:
            ordered.append(all_mp4[nm])
    if not ordered:
        raise RuntimeError("No scenes rendered")
    return ordered

def concat_videos(parts: list[Path], final_name=None) -> Path:
    run_id = uuid.uuid4().hex
    out_dir = MEDIA_ROOT / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = out_dir / "parts.txt"
    with manifest.open("w") as f:
        for p in parts:
            f.write(f"file '{p.resolve()}'\n")

    final_mp4 = out_dir / (final_name or "final.mp4")
    try:
        subprocess.run([
            "ffmpeg","-y","-f","concat","-safe","0",
            "-i", str(manifest), "-c","copy", str(final_mp4)
        ], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError:
        # fallback re-encode
        subprocess.run([
            "ffmpeg","-y","-f","concat","-safe","0",
            "-i", str(manifest),
            "-c:v","libx264","-c:a","aac", str(final_mp4)
        ], check=True, capture_output=True, text=True)

    if not final_mp4.exists():
        raise RuntimeError("FFmpeg failed to create final.mp4")
    return final_mp4
