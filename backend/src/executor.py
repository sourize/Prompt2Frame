import os
import uuid
import subprocess
from pathlib import Path

MEDIA_ROOT = Path("media/videos")

def execute_manim_code(
    code: str,
    scene_name: str,
    quality: str = "l",     # now default to 'l' not 'low'
    timeout: int = 300
) -> Path:
    """
    Renders one Manim scene; returns the Path to its .mp4.
    Raises RuntimeError on failure.
    """
    run_id = uuid.uuid4().hex
    run_dir = MEDIA_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # Write the scene file
    scene_py = run_dir / "scene.py"
    scene_py.write_text(code, encoding="utf-8")

    # Prepare output path
    output_file = run_dir / f"{scene_name}.mp4"

    # Build a CLI invocation that Manim will accept:
    #  - 'manim render file.py SceneName -ql'         (low quality)
    #  - '--disable_caching'
    #  - '-o output.mp4'
    #  - '--media_dir media/videos'
    cmd = [
        "manim", "render",
        str(scene_py),
        scene_name,
        f"-q{quality}",                  # e.g. '-ql', '-qm', '-qh', etc.
        "--disable_caching",
        "-o", str(output_file),          # shorthand for --output_file
        "--media_dir", str(MEDIA_ROOT),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            raise RuntimeError(f"Manim failed:\n{result.stderr.strip()}")
        if not output_file.exists():
            raise FileNotFoundError(f"Expected output {output_file} not found.")
        return output_file
    except subprocess.TimeoutExpired:
        raise RuntimeError("Manim rendering timed out")
    except Exception as e:
        raise RuntimeError(f"Error during Manim execution: {e}")

def concat_videos(video_paths: list[Path], final_name: str) -> Path:
    run_id = uuid.uuid4().hex
    target_dir = MEDIA_ROOT / run_id
    target_dir.mkdir(parents=True, exist_ok=True)

    parts_txt = target_dir / "parts.txt"
    with parts_txt.open("w") as f:
        for vp in video_paths:
            f.write(f"file '{vp.resolve()}'\n")

    final_mp4 = target_dir / "final.mp4"

    # Try a fast concat first
    try:
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(parts_txt),
            "-c", "copy",
            str(final_mp4),
        ], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError:
        # Fallback: re-encode to ensure compatibility
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(parts_txt),
            "-c:v", "libx264", "-c:a", "aac",
            str(final_mp4),
        ], check=True, capture_output=True, text=True)

    if not final_mp4.exists():
        raise RuntimeError("FFmpeg failed to produce final.mp4")
    return final_mp4
