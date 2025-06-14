import os
import re
import time
import logging
import ast
from typing import Optional

import groq
from dotenv import load_dotenv
import numpy as np

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("generator_service")

# --- Helper to sanitize code from assistant ---
def _sanitize_code(code: str) -> str:
    # Remove markdown fences
    code = re.sub(r"```(?:python)?", "", code)
    # Remove unsupported kwargs like opacity, fill_opacity
    code = re.sub(r",\s*(?:opacity|fill_opacity)\s*=\s*[^,\)\n]+", "", code)
    # Strip leading/trailing blank lines
    lines = [ln.rstrip() for ln in code.splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)

# --- Environment & Client ---
def _get_api_key() -> str:
    load_dotenv()
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY not set in environment.")
    return key

_client: Optional[groq.Client] = None

def get_client() -> groq.Client:
    global _client
    if _client is None:
        _client = groq.Client(api_key=_get_api_key())
    return _client

# --- System Prompt ---
MODEL_NAME = "meta-llama/llama-4-scout-17b-16e-instruct"
SYSTEM_PROMPT = (
    "You are a deterministic, production-grade code generator for 2D Manim v0.17.3+ animations. "
    "Output only pure Python code, no markdown or explanations. "
    "Begin with exactly these imports:\n"
    "from manim import *\n"
    "import random  # for any randomness\n"
    "import numpy as np  # for vector arithmetic\n"
    "Then define any helper functions you need with non-empty bodies, e.g.:\n"
    "def ease_in_out_sine(t: float) -> float:\n"
    "    from math import cos, pi\n"
    "    return 0.5 * (1 - cos(pi * t))\n"
    "Define one Scene subclass with construct(self) method. "
    "Use only built-in primitives, valid animations, and wrap each self.play in try/except. "
    "Ensure any name you reference is defined above."
)

# --- Code Validator ---
class Validator:
    @staticmethod
    def parse(code: str):
        try:
            return ast.parse(code)
        except SyntaxError as e:
            raise RuntimeError(f"Syntax error in code: {e}")

    @staticmethod
    def check_structure(tree: ast.AST, code: str):
        if not code.startswith("from manim import *"):
            raise RuntimeError("Code must start with 'from manim import *'.")
        classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        if len(classes) != 1:
            raise RuntimeError(f"Expected exactly one class, found {len(classes)}.")

# --- Generation Logic ---
def generate_code(prompt: str, retries: int = 3) -> str:
    for i in range(1, retries + 1):
        logger.info(f"Generation attempt {i}/{retries}")
        try:
            client = get_client()
            resp = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2 + 0.1 * (i - 1),
                max_tokens=2000,
                top_p=0.9,
            )
            raw = resp.choices[0].message.content
            code = _sanitize_code(raw)
            tree = Validator.parse(code)
            Validator.check_structure(tree, code)
            logger.info("Code generation successful.")
            return code
        except Exception as e:
            logger.warning(f"Attempt {i} failed: {e}")
            if i == retries:
                raise RuntimeError(f"Code generation failed after {retries} attempts: {e}")
            time.sleep(1)

    raise RuntimeError("Unexpected error in code generation.")

# --- Fallback ---
def generate_code_with_fallback(prompt: str) -> str:
    try:
        return generate_code(prompt)
    except RuntimeError as e:
        logger.error(f"Primary generation failed: {e}")
        # Minimal fallback scene
        return (
            "from manim import *\n"
            "import random  # for any randomness\n"
            "import numpy as np  # for vector arithmetic\n\n"
            "class FallbackScene(Scene):\n"
            "    def construct(self):\n"
            "        circle = Circle().set_color(BLUE).move_to(ORIGIN)\n"
            "        try:\n"
            "            self.play(Create(circle), run_time=1.0)\n"
            "        except RuntimeError as err:\n"
            "            raise RuntimeError(f'Fallback failed: {err}')\n"
            "        self.wait(1)"
        )
