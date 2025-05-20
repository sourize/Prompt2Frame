import os
import uuid
import subprocess
from pathlib import Path

MEDIA_ROOT = Path("media/videos")

def execute_manim_code(
    code: str,
    scene_name: str,
    quality: str = "low",
    timeout: int = 300
) -> Path:
    """
    Renders one Manim scene; returns the Path to its .mp4.
    Raises RuntimeError on failure.
    """
    run_id = uuid.uuid4().hex
    run_dir = MEDIA_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    scene_py = run_dir / "scene.py"
    scene_py.write_text(code, encoding="utf-8")

    output_file = run_dir / f"{scene_name}.mp4"
    cmd = [
        "manim", "render",
        str(scene_py), scene_name,
        "-q", quality,
        "--disable_caching",
        "--media_dir", str(MEDIA_ROOT),
        "--output_file", str(output_file),
        "--preview", "false",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            raise RuntimeError(f"Manim failed: {result.stderr}")
        if not output_file.exists():
            raise FileNotFoundError(f"Expected output {output_file} not found.")
        return output_file
    except subprocess.TimeoutExpired:
        raise RuntimeError("Manim rendering timed out")
    except Exception as e:
        raise RuntimeError(f"Error during Manim execution: {e}")

def concat_videos(
    video_paths: list[Path],
    final_name: str
) -> Path:
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

    final_mp4 = target_dir / "final.mp4"
    copy_cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(parts_txt),
        "-c", "copy",
        str(final_mp4),
    ]

    try:
        subprocess.run(copy_cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError:
        # fallback: re-encode to ensure compatibility
        reencode_cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(parts_txt),
            "-c:v", "libx264", "-c:a", "aac",
            str(final_mp4),
        ]
        subprocess.run(reencode_cmd, check=True, capture_output=True, text=True)

    if not final_mp4.exists():
        raise RuntimeError("FFmpeg failed to produce final.mp4")
    return final_mp4
