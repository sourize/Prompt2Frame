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
    "Respond with exactly one plain‑text Python snippet (no markdown) that begins with:\n"
    "    from manim import *\n\n"
    "Then define exactly one subclass of Scene, named clearly for the user prompt. "
    "Your code must exclusively use Manim’s public, documented API (e.g. shift(), to_edge(), "
    "scale(), FadeIn, FadeOut, Create, TransformMatchingShapes, etc.). "
    "Do NOT call any deprecated or internal methods such as .move(), .fade_in() as methods on Mobjects. "
    "Always wrap animations in self.play(...) with explicit transform classes, run_time (in seconds), "
    "and rate_func (one of linear, smooth, there_and_back, or another built‑in rate function). "
    "If positioning is needed, use shift(), to_edge(), or set_x()/set_y(); "
    "if you need a full‑screen shape, use config.frame_width/height. "
    "At the end of construct(), include exactly self.wait(1). "
    "Ensure code parses (AST‑valid), is PEP8‑compliant, and runs without import or attribute errors."
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

# ─── Validator ─────────────────────────────────────────────────────────────────
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
def _strip_fences(code: str) -> str:
    # Remove any ``` fences
    code = re.sub(r"```(?:python)?", "", code)
    return "\n".join(line.rstrip() for line in code.splitlines())

def sanitize_deprecated_methods(code: str) -> str:
    """
    Convert deprecated/internal calls:
      - .fade_in()/.fade_out() → self.play(FadeIn/Out(obj), run_time=1, rate_func=linear)
      - .move(...)           → .shift(...)
    """
    code = re.sub(
        r"(\w+)\.fade_out\(\)",
        r"self.play(FadeOut(\1), run_time=1, rate_func=linear)",
        code
    )
    code = re.sub(
        r"(\w+)\.fade_in\(\)",
        r"self.play(FadeIn(\1), run_time=1, rate_func=linear)",
        code
    )
    code = re.sub(r"\.move\(", ".shift(", code)
    return code

# ─── Core Generation ─────────────────────────────────────────────────────────
def generate_manim_code(prompt: str, max_retries: int = 3) -> str:
    validator = CodeValidator()
    for attempt in range(1, max_retries + 1):
        logger.info(f"Generation attempt {attempt}/{max_retries}")
        try:
            resp = get_client().chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM},
                    {"role": "user",   "content": prompt},
                ],
                temperature=0.2 + 0.1 * (attempt - 1),
                max_tokens=1500,
                top_p=0.9,
            )
            code = resp.choices[0].message.content
            code = _strip_fences(code)
            code = sanitize_deprecated_methods(code)
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
