import uuid
import subprocess
from pathlib import Path
import ast

MEDIA_ROOT = Path("media/videos")

def _extract_scene_names(code: str) -> list[str]:
    """Parse the Python AST and return all Scene subclass names in definition order."""
    tree = ast.parse(code)
    names = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                if getattr(base, "id", None) == "Scene":
                    names.append(node.name)
    if not names:
        raise RuntimeError("No Scene subclasses found in generated code")
    return names

def render_and_concat_all(raw, quality="l", timeout=300) -> Path:
    """
    Accepts either:
      - A single code string
      - A list of dicts {"name":..., "code":...}
    and returns a Path to the final concatenated mp4.
    """
    # Normalize input
    if isinstance(raw, str):
        code = raw
    else:
        raise RuntimeError("render_and_concat_all expects a single code string")

    # Extract each scene name
    scene_names = _extract_scene_names(code)

    # Write code to a one-off script
    run_id = uuid.uuid4().hex
    run_dir = MEDIA_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    script_path = run_dir / "all_scenes.py"
    script_path.write_text(code, encoding="utf-8")

    # Prepare media subdir
    media_dir = run_dir / "media"
    media_dir.mkdir(parents=True, exist_ok=True)

    # Call manim once for *all* Scene classes
    cmd = [
        "manim", "render",
        str(script_path),
        *scene_names,
        f"-q{quality}",
        "--disable_caching",
        "--media_dir", str(media_dir),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        stderr = proc.stderr or ""
        raise RuntimeError(f"Manim failed:\n{stderr.strip()}")

    # Discover the generated .mp4s
    mp4s = list(media_dir.rglob("*.mp4"))
    if not mp4s:
        raise RuntimeError(f"No .mp4 files produced under {media_dir!r}")

    # If only one, return it immediately
    if len(mp4s) == 1:
        return mp4s[0]

    # Otherwise, create a parts.txt and concat with ffmpeg
    parts_txt = run_dir / "parts.txt"
    with parts_txt.open("w") as f:
        for m in sorted(mp4s):
            f.write(f"file '{m.resolve()}'\n")

    final_mp4 = run_dir / "final.mp4"
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
             "-i", str(parts_txt), "-c", "copy", str(final_mp4)],
            check=True, capture_output=True, text=True
        )
    except subprocess.CalledProcessError:
        # fallback
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
             "-i", str(parts_txt), "-c:v", "libx264", "-c:a", "aac",
             str(final_mp4)],
            check=True, capture_output=True, text=True
        )

    if not final_mp4.exists():
        raise RuntimeError("FFmpeg failed to produce final.mp4")
    return final_mp4
