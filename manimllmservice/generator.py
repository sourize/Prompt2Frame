import os
import re
import time
import logging
import ast
from typing import Optional

import groq
from dotenv import load_dotenv
import numpy as np

# --- Logging Setup ---------------------------------------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# --- Utility Functions -----------------------------------------------------
def _sanitize_code(code: str) -> str:
    """
    Remove unsupported Manim keyword args like opacity and fill_opacity.
    """
    return re.sub(r",\s*(?:opacity|fill_opacity)\s*=\s*[^,\)\n]+", "", code)

def ease_in_out_sine(t: float) -> float:
    """
    Sine-based easing function.
    """
    from math import cos, pi
    return 0.5 * (1 - cos(pi * t))

# --- GROQ Client -----------------------------------------------------------
def get_api_key() -> str:
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("Environment variable GROQ_API_KEY is not set.")
    return api_key

_client: Optional[groq.Client] = None

def get_client() -> groq.Client:
    global _client
    if _client is None:
        _client = groq.Client(api_key=get_api_key())
    return _client

# --- System Prompt ---------------------------------------------------------
MODEL_NAME = "meta-llama/llama-4-scout-17b-16e-instruct"
SYSTEM = (
    "You are a deterministic, production‑grade code generator for 2D Manim v0.17.3+ animations.  "
    "All output must be pure Python3, no markdown or comments outside the code block.  "
    "Your response **must** begin exactly with:\n\n"
    "from manim import *\n"
    "import random  # for any randomness\n"
    "import numpy as np  # for vector arithmetic\n\n"
    "Immediately below these imports, **define any helper functions** you will use (e.g. easing functions) so that no NameError ever occurs.  "
    "For example:\n"
    "def ease_in_out_sine(t: float) -> float:\n"
    "    from math import cos, pi\n"
    "    return 0.5 * (1 - cos(pi * t))\n\n"
    "Then declare exactly one `class MyScene(Scene):` with a single `def construct(self):` method. Follow these strict rules:\n\n"

    "1.  **IMPORTS & STRUCTURE**\n"
    "- Only the three lines above—no other imports or asset loaders.\n"
    "- 4‑space indents, no tabs; one blank line between imports, helpers, class header, and method body.\n"
    "- Balanced parentheses, brackets, and braces.\n\n"

    "2.  **HELPERS**\n"
    "- Any function you call (e.g. easing, clamp) must be defined immediately after the imports.\n\n"

    "3.  **PRIMITIVES & CURVES**\n"
    "- Use only built‑in primitives: `Circle()`, `Square()`, `Triangle()`, `Rectangle()`, `Line()`, `Dot()`, `Ellipse()`, `Polygon()`, `ParametricFunction`.\n"
    "- No `SVGMobject`, `ImageMobject`, or external files.\n\n"

    "4.  **POSITIONING & COLORS**\n"
    "- Position with `.move_to()`, `.shift()`, or vector arithmetic (`LEFT*2 + UP*1`).\n"
    "- Coordinate bounds: x ∈ [-6,6], y ∈ [-4,4], z = 0.  Clamp out‑of‑bounds or raise `RuntimeError(\"Out of bounds\")`.\n"
    "- Only allowed colors: RED, BLUE, GREEN, YELLOW, PURPLE, ORANGE, WHITE.  No other names.\n\n"

    "5.  **ANIMATIONS**\n"
    "- Only use `Create`, `Transform`, `ReplacementTransform`, `FadeIn`, `FadeOut`.\n"
    "- Chain property changes via `.animate` inside `self.play()`.\n"
    "- One `self.play(...)` per line, max 6 calls, each with `run_time` between 0.5 and 2.0 seconds.\n"
    "- Wrap each `self.play` in `try/except RuntimeError as e:` and rethrow with context.\n"
    "- Always conclude with `self.wait(1)`.\n\n"

    "6.  **LIMITS & VALIDATION**\n"
    "- No more than 8 visible mobjects at once.\n"
    "- No more than 3 distinct color changes.\n"
    "- Total scene runtime between 5 and 8 seconds.\n"
    "- Meaningful variable names; initialize before use.\n\n"

    "7.  **NO UNDEFINED NAMES**\n"
    "- If you reference `ease_in_out_sine`, `clamp`, `my_curve`, etc., you **must** define them in the helper section above.\n"
    "- Do not rely on any global or external definitions.\n\n"

    "**Example skeleton (do NOT copy verbatim):**\n"
    "```python\n"
    "from manim import *\n"
    "import random  # for any randomness\n"
    "import numpy as np  # for vector arithmetic\n\n"
    "def ease_in_out_sine(t: float) -> float:\n"
    "    from math import cos, pi\n"
    "    return 0.5 * (1 - cos(pi * t))\n\n"
    "class TransformingShape(Scene):\n"
    "    def construct(self):\n"
    "        circle = Circle().set_color(BLUE).move_to(LEFT*2)\n"
    "        square = Square().set_color(RED).move_to(RIGHT*2)\n\n"
    "        try:\n"
    "            self.play(\n"
    "                Create(circle),\n"
    "                run_time=1.0\n"
    "            )\n"
    "        except RuntimeError as e:\n"
    "            raise RuntimeError(f\"Create failed: {e}\")\n\n"
    "        try:\n"
    "            self.play(\n"
    "                Transform(circle, square, rate_func=ease_in_out_sine),\n"
    "                square.animate.set_color(GREEN),\n"
    "                run_time=2.0\n"
    "            )\n"
    "        except RuntimeError as e:\n"
    "            raise RuntimeError(f\"Transform failed: {e}\")\n\n"
    "        self.wait(1)\n"
    "```\n\n"
    "Strictly adhere to every rule to ensure no undefined names, no asset dependencies, and fully renderable, error‑free code."
)


# --- Code Validation ------------------------------------------------------
class CodeValidator:
    @staticmethod
    def validate_syntax(code: str) -> None:
        try:
            ast.parse(code)
        except SyntaxError as exc:
            raise RuntimeError(f"Syntax error: {exc}")

    @staticmethod
    def validate_structure(code: str) -> None:
        if not code.startswith("from manim import *"):
            raise RuntimeError("Code must start with 'from manim import *'.")
        if "import numpy as np" not in code:
            raise RuntimeError("Missing 'import numpy as np'.")
        forbidden = ["import os", "import sys", "subprocess", "shutil"]
        for item in forbidden:
            if item in code:
                raise RuntimeError(f"Forbidden import: {item}")

    @staticmethod
    def validate_scene_class(code: str) -> None:
        tree = ast.parse(code)
        scenes = [node for node in ast.walk(tree)
                  if isinstance(node, ast.ClassDef)
                  and any(isinstance(b, ast.Name) and b.id == 'Scene' for b in node.bases)]
        if len(scenes) != 1:
            raise RuntimeError(f"Expected one Scene subclass, found {len(scenes)}.")

    @staticmethod
    def validate_delimiters(code: str) -> None:
        for o, c in [('(', ')'), ('[', ']'), ('{', '}')]:
            if code.count(o) != code.count(c):
                raise RuntimeError(f"Unmatched delimiter {o} vs {c}.")

    @staticmethod
    def validate_colors(code: str) -> None:
        # Replace any undefined custom colors
        undefined = re.findall(r"\.set_color\(([^)]+)\)", code)
        for color in undefined:
            if color.strip() not in ["RED","BLUE","GREEN","YELLOW","PURPLE","ORANGE","WHITE"]:
                raise RuntimeError(f"Undefined color: {color}")

# --- Core Generation ------------------------------------------------------
def _clean_and_format_code(raw: str) -> str:
    code = re.sub(r"```(?:python)?", "", raw).strip('`\n ')
    return "\n".join(line.rstrip() for line in code.splitlines())

def generate_manim_code(prompt: str, max_retries: int = 3) -> str:
    validator = CodeValidator()
    client = get_client()

    for attempt in range(1, max_retries + 1):
        logger.info(f"Attempt {attempt}/{max_retries}")
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role":"system","content":SYSTEM},{"role":"user","content":prompt}],
                temperature=0.2 + 0.1*(attempt-1),
                top_p=0.9,
                max_tokens=2000
            )
            raw = response.choices[0].message.content
            code = _sanitize_code(_clean_and_format_code(raw))

            validator.validate_structure(code)
            validator.validate_syntax(code)
            validator.validate_scene_class(code)
            validator.validate_delimiters(code)
            validator.validate_colors(code)

            logger.info("Code generation succeeded.")
            return code
        except Exception as exc:
            logger.warning(f"Generation failed: {exc}")
            if attempt == max_retries:
                raise RuntimeError(f"Generation failed after {attempt} attempts: {exc}")
            time.sleep(1)

# --- Fallback --------------------------------------------------------------
def generate_manim_code_with_fallback(prompt: str) -> str:
    try:
        return generate_manim_code(prompt)
    except RuntimeError as exc:
        logger.error(f"Falling back due to: {exc}")
        return (
            "from manim import *\n"
            "import numpy as np\n\n"
            "class FallbackScene(Scene):\n"
            "    def construct(self):\n"
            "        circle = Circle().set_color(BLUE).move_to(ORIGIN)\n"
            "        try:\n"
            "            self.play(Create(circle), run_time=1.0)\n"
            "        except RuntimeError as err:\n"
            "            raise RuntimeError(f'Fallback failed: {err}')\n"
            "        self.wait(1)\n"
        )
