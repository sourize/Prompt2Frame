# ===== generator.py =====
import os
import re
import time
import logging
import ast
from typing import Optional

import groq
from dotenv import load_dotenv
from manim import FadeOut, FadeIn, Scene, Circle

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)

load_dotenv()

MODEL_NAME = "meta-llama/llama-4-scout-17b-16e-instruct"

SYSTEM = (
    "You are a world-class, deterministic 2D Manim v0.17.3+ code generator. "
    "Your output must be fully self-contained Python code with precise imports, consistent indentation, and no syntax errors. "
    "Begin by listing only necessary imports (e.g., `from manim import *`, `import numpy as np`). "
    "Define exactly one subclass of `Scene` named descriptively based on the prompt. "
    "All animations must be wrapped in `self.play(...)` calls with explicit transforms and easing functions. "
    "Ensure any `fade_in`, `fade_out`, or similar methods are converted to `self.play(FadeIn/Out(...))` with `run_time` and `rate_func`. "
    "At the end of `construct`, include `self.wait(1)`. "
    "Use clear variable names, proper spacing, and adhere to PEP8."
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

class CodeValidator:
    @staticmethod
    def validate_syntax(code: str):
        try:
            ast.parse(code)
        except SyntaxError as e:
            raise RuntimeError(f"Syntax error: {e}")

    @staticmethod
    def validate_structure(code: str):
        if not code.startswith("from manim import *"):
            raise RuntimeError("Code must start with 'from manim import *'")
        if "import numpy as np" not in code:
            raise RuntimeError("Missing 'import numpy as np' import")
        if code.count("class ") != 1 or "Scene" not in code:
            raise RuntimeError("Expected exactly one Scene subclass")

# Common sanitization patterns
def sanitize_common_errors(code: str) -> str:
    # Replace .fade_out() calls with self.play(FadeOut(obj), run_time=1)
    code = re.sub(r"(\w+)\.fade_out\(\)", r"self.play(FadeOut(\1), run_time=1)", code)
    code = re.sub(r"(\w+)\.fade_in\(\)", r"self.play(FadeIn(\1), run_time=1)", code)
    # Ensure easing functions are imported
    if "ease_in_out" in code.lower() and "ease_in_out" not in code:
        # Already imported via *
        pass
    return code

def _strip_fences(code: str) -> str:
    code = re.sub(r"```(?:python)?", "", code)
    return "\n".join(line.rstrip() for line in code.splitlines())

def generate_manim_code(prompt: str, max_retries: int = 3) -> str:
    validator = CodeValidator()
    for attempt in range(1, max_retries + 1):
        logger.info(f"Generation attempt {attempt}/{max_retries}")
        try:
            client = get_client()
            resp = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
                temperature=0.2 + 0.1*(attempt-1),
                max_tokens=1500,
                top_p=0.9,
            )
            raw = resp.choices[0].message.content
            code = _strip_fences(raw)
            code = sanitize_common_errors(code)
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
        logger.error(f"Primary generation failed: {e}")
        # minimal fallback
        return (
            "from manim import *\n"
            "import numpy as np\n\n"
            "class FallbackScene(Scene):\n"
            "    def construct(self):\n"
            "        circle = Circle().set_color(RED)\n"
            "        self.play(Create(circle), run_time=1)\n"
            "        self.wait(1)\n"
        )