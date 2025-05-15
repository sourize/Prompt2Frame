### app.py

from flask import Flask, request, jsonify, send_from_directory, g
from flask_cors import CORS
from dotenv import load_dotenv
import os, re, time
from pathlib import Path
from werkzeug.exceptions import HTTPException
import psutil
from flask_caching import Cache

from .generator import generate_manim_code
from .executor import execute_manim_code

load_dotenv()
app = Flask(__name__)
CORS(app)

# Ensure media directories exist
media_dir = Path("media/videos")
media_dir.mkdir(parents=True, exist_ok=True)

cache = Cache(app, config={
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': 'cache',
    'CACHE_DEFAULT_TIMEOUT': 300
})

def check_system_resources():
    cpu_percent = psutil.cpu_percent()
    memory = psutil.virtual_memory()
    
    if cpu_percent > 90 or memory.percent > 90:
        return False
    return True

@app.route("/generate", methods=["POST"])
@cache.memoize(timeout=300)
def generate_animation():
    payload = request.get_json(force=True)
    prompt = payload.get("prompt", "").strip()
    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400

    try:
        code = generate_manim_code(prompt)
        match = re.search(r"class\s+(\w+)\(Scene\)", code)
        if not match:
            raise RuntimeError("No Scene subclass found in generated code")
        scene_name = match.group(1)

        video_path = execute_manim_code(code, scene_name)
        media_dir = Path("media/videos").resolve()
        video_path_obj = Path(video_path).resolve()
        relative_path = video_path_obj.relative_to(media_dir)
        video_url = f"/media/videos/{relative_path.as_posix()}"
        print(f"Generated video URL: {video_url}")

        return jsonify({
            "videoUrl": video_url,
            "code": code
        }), 200

    except Exception as err:
        app.logger.error("Generation error", exc_info=err)
        return jsonify({"error": str(err)}), 500

@app.route('/media/videos/<path:filename>')
def serve_video(filename):
    return send_from_directory('media/videos', filename)

@app.route('/health')
def health_check():
    return jsonify({"status": "ok"})

@app.errorhandler(Exception)
def handle_error(error):
    if isinstance(error, HTTPException):
        response = {
            "error": error.description,
            "status_code": error.code
        }
    else:
        response = {
            "error": str(error),
            "status_code": 500
        }
    return jsonify(response), response["status_code"]

# Add request timeout middleware
@app.before_request
def before_request():
    if not check_system_resources():
        return jsonify({"error": "Server is currently overloaded. Please try again later."}), 503
    g.start_time = time.time()

@app.after_request
def after_request(response):
    if hasattr(g, 'start_time'):
        elapsed = time.time() - g.start_time
        if elapsed > 300:  # 5 minutes
            return jsonify({"error": "Request timeout"}), 408
    return response

if __name__ == '__main__':
    debug = os.getenv('FLASK_DEBUG', 'false').lower() in ('1', 'true')
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=debug)
