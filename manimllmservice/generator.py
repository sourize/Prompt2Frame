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

SYSTEM_FILE = os.getenv("SYSTEM_PROMPT_PATH", "Generator_System_Prompt.txt")
try:
    with open(SYSTEM_FILE, "r", encoding="utf-8") as f:
        SYSTEM = f.read().strip()
except FileNotFoundError:
    raise RuntimeError(f"System-prompt file not found: {SYSTEM_FILE}")
except Exception as e:
    raise RuntimeError(f"Error reading system prompt: {e}")


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
            logger.debug(f"Raw model output:\n{code}")  # Add debug logging
            
            # Log the first few lines to see what we're getting
            logger.info("First 10 lines of raw output:")
            for i, line in enumerate(code.splitlines()[:10]):
                logger.info(f"Line {i+1}: {repr(line)}")  # Use repr to see whitespace
            
            code = _strip_fences(code)
            code = sanitize_deprecated_methods(code)
            
            # Log the processed code
            logger.info("First 10 lines after processing:")
            for i, line in enumerate(code.splitlines()[:10]):
                logger.info(f"Line {i+1}: {repr(line)}")  # Use repr to see whitespace
            
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
