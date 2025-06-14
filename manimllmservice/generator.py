import os
import re
import time
import logging
import ast
from typing import Optional

import groq
from dotenv import load_dotenv

# Configure module‑level logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)

# --- GROQ client setup ---

def get_api_key() -> str:
    load_dotenv()
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY environment variable is not set")
    return key

_client: Optional[groq.Client] = None

def get_client() -> groq.Client:
    global _client
    if _client is None:
        _client = groq.Client(api_key=get_api_key())
    return _client

MODEL_NAME = "meta-llama/llama-4-scout-17b-16e-instruct"

# --- System prompt ---

SYSTEM = (
    "You are a deterministic, production‑grade code generator for 2D Manim v0.17.3+ animations.\n"
    "All output must be pure Python, no markdown or comments.\n\n"
    "1) ALWAYS start with:\n"
    "   from manim import *\n"
    "   import numpy as np\n\n"
    "2) If you need helpers, define them immediately below imports.\n"
    "3) Then define exactly one Scene subclass with construct(self).\n"
    "4) Use only built‑in primitives and animations, obey the coordinate & run_time limits.\n"
    "5) Wrap plays in try/except and end construct with self.wait(1).\n"
    "6) No external assets or undefined names.\n"
)

# --- Code sanitization & validation ---

def _strip_fences(code: str) -> str:
    code = re.sub(r"```(?:python)?", "", code)
    return "\n".join(line.rstrip() for line in code.splitlines() if line.strip() or code.startswith("from manim"))

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
            raise RuntimeError("Must start with `from manim import *`")
        if "import numpy as np" not in code:
            raise RuntimeError("Missing `import numpy as np`")
        if code.count("class ") != 1 or "Scene" not in code:
            raise RuntimeError("Expected exactly one Scene subclass")

# --- Generation logic ---

def generate_manim_code(prompt: str, max_retries: int = 3) -> str:
    validator = CodeValidator()
    for attempt in range(1, max_retries + 1):
        logger.info(f"Code generation attempt {attempt}/{max_retries}")
        try:
            client = get_client()
            resp = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM},
                    {"role": "user",   "content": prompt},
                ],
                temperature=0.2 + 0.1*(attempt-1),
                max_tokens=1500,
                top_p=0.9,
            )
            raw = resp.choices[0].message.content
            code = _strip_fences(raw)
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
    """
    Try the main generator, otherwise return a minimal fallback Scene.
    """
    try:
        return generate_manim_code(prompt)
    except Exception as e:
        logger.error(f"Primary generation failed: {e}")
        return (
            "from manim import *\n"
            "import numpy as np\n\n"
            "class FallbackScene(Scene):\n"
            "    def construct(self):\n"
            "        circle = Circle().set_color(RED)\n"
            "        try:\n"
            "            self.play(Create(circle), run_time=1)\n"
            "        except RuntimeError as err:\n"
            "            raise RuntimeError(f'Fallback failed: {err}')\n"
            "        self.wait(1)\n"
        )
