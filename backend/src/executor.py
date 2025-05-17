import os
import uuid
import subprocess
from pathlib import Path

def execute_manim_code(code: str, scene_name: str, output_dir: str = "media/videos") -> str:

    try:
        # Convert to absolute paths
        base = Path(output_dir).resolve()
        base.mkdir(parents=True, exist_ok=True)

        run_id = uuid.uuid4().hex
        run_dir = base / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        # Create media directory if it doesn't exist
        media_dir = base / "media"
        media_dir.mkdir(parents=True, exist_ok=True)

        # Write code file
        scene_py = run_dir / "scene.py"
        scene_py.write_text(code, encoding="utf-8")

        # Set up output paths
        output_file = run_dir / f"{scene_name}.mp4"
        
        # Render via Manim
        cmd = [
            "manim", "render",
            str(scene_py),
            scene_name,
            "-ql",
            "--disable_caching",
            "--media_dir", str(base),
            "--output_file", str(output_file),
            "--preview", "false"
        ]
        print(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode:
            print(f"Manim stderr: {result.stderr}")
            raise RuntimeError(f"Manim failed: {result.stderr}")

        # Check for video in the expected location
        video_file = run_dir / f"{scene_name}.mp4"
        if not video_file.exists():
            video_file = base / "videos" / run_id / f"{scene_name}.mp4"
            if not video_file.exists():
                print(f"Manim stdout: {result.stdout}")
                raise FileNotFoundError(f"Video not found at expected paths: {run_dir / f'{scene_name}.mp4'} or {video_file}")

        return str(video_file)
    except subprocess.TimeoutExpired:
        raise RuntimeError("Manim rendering timed out after 5 minutes")
    except Exception as e:
        raise RuntimeError(f"Manim rendering failed: {str(e)}")