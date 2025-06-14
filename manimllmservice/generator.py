# ===== generator.py =====
import os
import re
import time
import logging
import ast
from typing import Optional

import groq
from dotenv import load_dotenv

# ─── Logging ──────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)

# ─── Configuration ────────────────────────────────────────────────────────────
load_dotenv()
MODEL_NAME = "meta-llama/llama-4-scout-17b-16e-instruct"

SYSTEM = (
    "You are a world‑class, deterministic 2D Manim v0.17.3+ code generator. "
    "Always emit exactly one plain‑text Python snippet (no markdown) starting with:\n"
    "    from manim import *\n\n"
    "Then define one subclass of Scene, named logically for the user prompt.\n\n"
    "**Rectangle usage**: Never call Rectangle() with LEFT/RIGHT/UP/DOWN tuples. "
    "If you need a background rectangle, use:\n"
    "    screen = Rectangle(\n"
    "        width=config.frame_width,\n"
    "        height=config.frame_height,\n"
    "        fill_opacity=1\n"
    "    )\n\n"
    "**Easing functions**: Do NOT reference or import ease_in_out_sine or others directly. "
    "Always use the built‑in rate_funcs linear, smooth, there_and_back, etc., which are "
    "available via `from manim import *`.\n\n"
    "**Transforms**: To morph between shapes of different vertices (e.g., circle→square), "
    "use TransformMatchingShapes rather than Transform.\n\n"
    "**Fade methods**: Convert any `.fade_in()`/`.fade_out()` calls into:\n"
    "    self.play(FadeIn(obj), run_time=1, rate_func=linear)\n"
    "    self.play(FadeOut(obj), run_time=1, rate_func=linear)\n\n"
    "All animations must be wrapped in `self.play(...)` with explicit transform classes, "
    "`run_time` (in seconds), and `rate_func` (one of linear, smooth, etc.).\n"
    "At the end of `construct`, include exactly `self.wait(1)`.\n\n"
    "Use clear variable names, 4‑space indentation, and adhere to PEP8 throughout."
)

_client: Optional[groq.Client] = None

def get_api_key() -> str:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY environment variable is not set")
    return key

def get_client() -> groq.Client:
    global _client
    if _client is None:
        _client = groq.Client(api_key=get_api_key())
    return _client

# ─── Validation ───────────────────────────────────────────────────────────────
class CodeValidator:
    @staticmethod
    def validate_syntax(code: str):
        try:
            ast.parse(code)
        except SyntaxError as e:
            raise RuntimeError(f"Syntax error in generated code: {e}")

    @staticmethod
    def validate_structure(code: str):
        # Must start with wildcard import
        if not code.strip().startswith("from manim import *"):
            raise RuntimeError("Generated snippet must start with `from manim import *`")
        # Exactly one Scene subclass
        scenes = [
            ln for ln in code.splitlines()
            if ln.strip().startswith("class ") and "(Scene)" in ln
        ]
        if len(scenes) != 1:
            raise RuntimeError("Expected exactly one subclass of Scene in snippet")

# ─── Sanitization ────────────────────────────────────────────────────────────
def sanitize_common_errors(code: str) -> str:
    # .fade_out() → self.play(FadeOut(...), run_time=1, rate_func=linear)
    code = re.sub(
        r"(\w+)\.fade_out\(\)",
        r"self.play(FadeOut(\1), run_time=1, rate_func=linear)",
        code,
    )
    code = re.sub(
        r"(\w+)\.fade_in\(\)",
        r"self.play(FadeIn(\1), run_time=1, rate_func=linear)",
        code,
    )
    return code

def sanitize_rectangle(code: str) -> str:
    """
    Replace any Rectangle(...) with corner tuples by full-screen rectangle pattern.
    """
    pattern = r"(\w+)\s*=\s*Rectangle\([^)]*\)"
    replacement = (
        r"\1 = Rectangle(\n"
        r"    width=config.frame_width,\n"
        r"    height=config.frame_height,\n"
        r"    fill_opacity=1\n"
        r")"
    )
    return re.sub(pattern, replacement, code)

def rewrite_transforms(code: str) -> str:
    """
    Convert Transform(circle, square) → TransformMatchingShapes(circle, square)
    whenever the two shapes differ in number of points.
    """
    return re.sub(
        r"self\.play\(Transform\(([^,]+),\s*([^)]+)\)",
        r"self.play(TransformMatchingShapes(\1, \2)",
        code
    )

def _strip_fences(code: str) -> str:
    # Remove any ``` fences
    code = re.sub(r"```(?:python)?", "", code)
    return "\n".join(line.rstrip() for line in code.splitlines())

# ─── Core Generation ─────────────────────────────────────────────────────────
def generate_manim_code(prompt: str, max_retries: int = 3) -> str:
    validator = CodeValidator()
    for attempt in range(1, max_retries + 1):
        logger.info(f"Generation attempt {attempt}/{max_retries}")
        try:
            resp = get_client().chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system",  "content": SYSTEM},
                    {"role": "user",    "content": prompt},
                ],
                temperature=0.2 + 0.1 * (attempt - 1),
                max_tokens=1500,
                top_p=0.9,
            )
            code = resp.choices[0].message.content
            code = _strip_fences(code)
            code = sanitize_common_errors(code)
            code = sanitize_rectangle(code)
            code = rewrite_transforms(code)
            validator.validate_structure(code)
            validator.validate_syntax(code)
            return code

        except Exception as e:
            logger.warning(f"Attempt {attempt} failed: {e}")
            if attempt == max_retries:
                raise RuntimeError(f"All attempts failed: {e}")
            time.sleep(1)

    raise RuntimeError("Unexpected failure in generate_manim_code")

def generate_manim_code_with_fallback(prompt: str) -> str:
    try:
        return generate_manim_code(prompt)
    except Exception as e:
        logger.error(f"Primary generation failed, using fallback: {e}")
        return (
            "from manim import *\n"
            "import numpy as np\n\n"
            "class FallbackScene(Scene):\n"
            "    def construct(self):\n"
            "        circle = Circle().set_color(RED)\n"
            "        self.play(Create(circle), run_time=1)\n"
            "        self.wait(1)\n"
        )
