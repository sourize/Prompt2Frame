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
    "Respond with a single plain‑text Python snippet (no markdown) that begins with "
    "`from manim import *` (so that `config`, easing, shapes, etc. are available). "
    "Do NOT import Manim in this service layer—emit only the snippet. "
    "Define exactly one subclass of `Scene`, named based on the prompt. "
    "Wrap every animation in `self.play(...)` with explicit transforms, "
    "run_time, and rate_func. Convert `.fade_in()`/`.fade_out()` calls into "
    "`self.play(FadeIn/Out(...), run_time=…, rate_func=…)`. "
    "If you need a full‑screen rectangle, use:\n"
    "  `screen = Rectangle(width=config.frame_width, height=config.frame_height, fill_opacity=1)`\n"
    "At the end of `construct`, include `self.wait(1)`. "
    "Use clear variable names, 4‑space indentation, and adhere to PEP8."
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
        if not code.strip().startswith("from manim import *"):
            raise RuntimeError("Snippet must start with `from manim import *`")
        scenes = [
            ln for ln in code.splitlines()
            if ln.strip().startswith("class ") and "(Scene)" in ln
        ]
        if len(scenes) != 1:
            raise RuntimeError("Expected exactly one `Scene` subclass")

# ─── Sanitization ────────────────────────────────────────────────────────────
def sanitize_common_errors(code: str) -> str:
    # .fade_out() → self.play(FadeOut(...))
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
    Replace any Rectangle(...) with four corner args by a full-screen rectangle.
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

def inject_missing_imports(code: str) -> str:
    """
    Ensure `config` is available. Since we do `from manim import *`, config is already
    in scope, so no extra imports needed here.
    """
    return code

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
            code = inject_missing_imports(code)
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
