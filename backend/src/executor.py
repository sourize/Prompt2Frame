import os
import uuid
import subprocess
from pathlib import Path

def execute_manim_code(
    code: str,
    scene_name: str,
    media_root: Path,
    run_id: str = None,
    timeout: int = 300,
) -> Path:
    """
    Render a Manim scene script to video and return path to the output file.
    """
    run_id = run_id or uuid.uuid4().hex
    work_dir = media_root / run_id
    work_dir.mkdir(parents=True, exist_ok=True)

    scene_py = work_dir / "scene.py"
    scene_py.write_text(code, encoding="utf-8")

    output_file = work_dir / f"{scene_name}.mp4"
    cmd = [
        "manim", "render", str(scene_py), scene_name,
        "-ql", "--disable_caching",
        "--media_dir", str(media_root),
        "--output_file", str(output_file),
        "--preview", "false"
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Manim failed (rc={result.returncode}): {result.stderr}")
    if not output_file.exists():
        raise FileNotFoundError(f"Expected video not found at {output_file}")
    return output_file
