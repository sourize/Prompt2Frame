# executor.py
import uuid, subprocess, ast, re
from pathlib import Path

MEDIA_ROOT = Path("media/videos")
_SCENE_RE = re.compile(r"class\s+(\w+)\s*\(\s*Scene\s*\)")

def execute_manim_code(code: str,
                       quality: str = "l",
                       timeout: int = 300) -> list[Path]:
    # 1) syntax-check
    try:
        ast.parse(code)
    except SyntaxError as e:
        raise RuntimeError(f"Syntax error: {e}")

    # 2) write to disk
    run_id = uuid.uuid4().hex
    run_dir = MEDIA_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "scene.py").write_text(code, encoding="utf-8")
    media_dir = run_dir / "media"
    media_dir.mkdir(parents=True, exist_ok=True)

    # 3) call manim once
    cmd = [
        "manim", "render",
        str(run_dir / "scene.py"),
        "-q" + quality,
        "--disable_caching",
        "--media_dir", str(media_dir),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        stderr = proc.stderr or ""
        # catch known patterns...
        raise RuntimeError(f"Manim failed:\n{stderr.strip()}")

    # 4) glob all mp4 outputs
    vids = list(run_dir.rglob("*.mp4"))
    if not vids:
        raise RuntimeError("No mp4 outputs found")
    # return largest-per-scene? we'll just return them all
    return sorted(vids, key=lambda p: p.stat().st_size, reverse=True)
