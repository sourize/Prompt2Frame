import re
import uuid
import subprocess
import ast
from pathlib import Path

MEDIA_ROOT = Path("media/videos")

# Sanitize patterns:
_REWRITE = [
    # Replace any Write(...) → Create(...)
    (re.compile(r"\bWrite\("), "Create("),
    # Replace any .animate.set_points(...) → Transform(...)
    (re.compile(r"(\w+)\.animate\.set_points\(\s*(\w+\([^)]*\))\s*\)"),
     lambda m: f"Transform({m.group(1)}, {m.group(2)})"),
    # Strip any camera.frame operations
    (re.compile(r"camera\.frame\.[\w_]+\([^)]*\)"), ""),
]

def _sanitize(code: str) -> str:
    for pat, repl in _REWRITE:
        if callable(repl):
            code = pat.sub(repl, code)
        else:
            code = pat.sub(repl, code)
    return code

def render_and_concat_all(code: str, quality="l", timeout=300) -> Path:
    """
    1) Sanitize unsupported calls
    2) Write single main.py
    3) Invoke Manim on every Scene subclass inside it
    4) Collect all mp4s and ffmpeg‐concat them
    5) Return one final.mp4 path
    """
    code = _sanitize(code)
    run_id = uuid.uuid4().hex
    run_dir = MEDIA_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # Write main.py
    main_py = run_dir / "main.py"
    main_py.write_text(code, encoding="utf-8")

    # Discover scene names via AST
    tree = ast.parse(code)
    scenes = [
        cls.name
        for cls in tree.body
        if isinstance(cls, ast.ClassDef)
        for base in cls.bases
        if (isinstance(base, ast.Name) and base.id=="Scene")
           or (isinstance(base, ast.Attribute) and base.attr=="Scene")
    ]
    if not scenes:
        raise RuntimeError("No Scene subclasses found to render")

    media_dir = run_dir / "media"
    media_dir.mkdir(exist_ok=True, parents=True)

    # Render each scene
    videos = []
    for sc in scenes:
        cmd = [
            "manim", "render",
            str(main_py),
            sc,
            f"-q{quality}",
            "--disable_caching",
            "--media_dir", str(media_dir),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if proc.returncode != 0:
            raise RuntimeError(f"Manim failed on {sc}:\n{proc.stderr.strip()}")
        # pick the largest .mp4 under media_dir
        mp4s = list(media_dir.rglob(f"{sc}*.mp4"))
        if not mp4s:
            raise RuntimeError(f"No mp4 for scene {sc}")
        videos.append(max(mp4s, key=lambda p: p.stat().st_size))

    # If only one scene, return it
    if len(videos)==1:
        return videos[0]

    # Otherwise concat
    parts = run_dir/"parts.txt"
    with parts.open("w") as f:
        for v in videos:
            f.write(f"file '{v.resolve()}'\n")

    final = run_dir/"final.mp4"
    try:
        subprocess.run([
            "ffmpeg","-y","-f","concat","-safe","0",
            "-i",str(parts),"-c","copy",str(final)
        ], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError:
        subprocess.run([
            "ffmpeg","-y","-f","concat","-safe","0",
            "-i",str(parts),"-c:v","libx264","-c:a","aac",str(final)
        ], check=True, capture_output=True, text=True)

    if not final.exists():
        raise RuntimeError("ffmpeg failed to produce final.mp4")
    return final
