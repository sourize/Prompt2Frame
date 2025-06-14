import os
import re
import time
import logging
import ast
from typing import Any, Optional

import groq
from dotenv import load_dotenv
import numpy as np

# Configure module‐level logger
logger = logging.getLogger("manim_code_generator")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

# --- Helper Functions ------------------------------------------------------

def _sanitize_code(code: str) -> str:
    """
    Remove unsupported keyword arguments (e.g., opacity, fill_opacity) from constructor calls.
    """
    pattern = r",\s*(?:opacity|fill_opacity)\s*=\s*[^,\)\n]+"
    return re.sub(pattern, "", code)

# Easing curve helper example (define here to avoid NameError in output)
def ease_in_out_sine(t: float) -> float:
    """
    Ease function mapping t in [0, 1] to a smooth sine‐based curve.
    """
    from math import cos, pi
    return 0.5 * (1 - cos(pi * t))

# --- GROQ Client Initialization -------------------------------------------

def get_api_key() -> str:
    """
    Retrieve the GROQ_API_KEY from environment or fail.
    """
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("Environment variable GROQ_API_KEY is not set.")
    return api_key

_client: Optional[groq.Client] = None

def get_client() -> groq.Client:
    """
    Lazily initialize and return a GROQ client instance.
    """
    global _client
    if _client is None:
        _client = groq.Client(api_key=get_api_key())
    return _client

# --- System Prompt ----------------------------------------------------------

MODEL_NAME = "meta-llama/llama-4-scout-17b-16e-instruct"
SYSTEM = (
    "You are a deterministic, production-grade code generator for 2D Manim v0.17.3+ animations.\n"
    "All output must be pure Python3, no markdown or comments outside code blocks.\n"
    "\n"
    "1. ALWAYS BEGIN with exactly these imports:\n"
    "   from manim import *\n"
    "   import numpy as np  # for vectors and parametric functions\n"
    "\n"
    "2. DEFINE any helper functions you need—including easing curves—immediately below imports.\n"
    "   For example:\n"
    "       def ease_in_out_sine(t: float) -> float:\n"
    "           from math import cos, pi\n"
    "           return 0.5 * (1 - cos(pi * t))\n"
    "\n"
    "3. ONLY use built-in Manim primitives:\n"
    "   Circle, Square, Triangle, Rectangle, Line, Dot, Ellipse, Polygon, ParametricFunction.\n"
    "\n"
    "4. GROUPING:\n"
    "   - If you need to animate multiple mobjects at once, wrap them in a VGroup: e.g.\n"
    "       group = VGroup(obj1, obj2, obj3)\n"
    "     Then animate that group, not a bare Python list.\n"
    "\n"
    "5. STRUCTURE:\n"
    "   - Exactly one Scene subclass with a single construct(self) method.\n"
    "   - 4-space indents, no tabs; one blank line between imports, helpers, class header, and method body.\n"
    "   - Balanced brackets.\n"
    "   - No external assets or imports beyond the two above.\n"
    "\n"
    "6. POSITIONING & COLORS:\n"
    "   - Coordinates x ∈ [-6,6], y ∈ [-4,4], z always 0.\n"
    "   - Position via .move_to(), .shift(), or algebraic vector ops.\n"
    "   - Colors only via constants: RED, BLUE, GREEN, YELLOW, PURPLE, ORANGE, WHITE.\n"
    "\n"
    "7. ANIMATIONS:\n"
    "   - Only Create, Transform, ReplacementTransform, FadeIn, FadeOut.\n"
    "   - Chain .animate for property changes inside self.play().\n"
    "   - One self.play() call per line, max 6 plays, run_time ∈ [0.5,2.0].\n"
    "   - Wrap each self.play call in try/except RuntimeError as e, rethrow with context message.\n"
    "   - End construct with self.wait(1).\n"
    "\n"
    "8. LIMITS:\n"
    "   - ≤8 visible mobjects at once.\n"
    "   - ≤3 distinct color changes.\n"
    "   - Total scene duration ∈ [5,8] seconds.\n"
    "   - Validate and clamp any out-of-bounds coordinates or raise RuntimeError(\"Out of bounds\").\n"
    "\n"
    "EXAMPLE OUTPUT (pure code block only):\n"
    "```python\n"
    "from manim import *\n"
    "import numpy as np  # for vectors and parametric functions\n"
    "\n"
    "def ease_in_out_sine(t: float) -> float:\n"
    "    from math import cos, pi\n"
    "    return 0.5 * (1 - cos(pi * t))\n"
    "\n"
    "class MyScene(Scene):\n"
    "    def construct(self):\n"
    "        circle = Circle().set_color(BLUE).move_to(LEFT * 2)\n"
    "        square = Square().set_color(RED).move_to(RIGHT * 2)\n"
    "\n"
    "        group = VGroup(circle, square)\n"
    "        try:\n"
    "            self.play(Create(group), run_time=1.5)\n"
    "        except RuntimeError as e:\n"
    "            raise RuntimeError(f\"Creation failed: {e}\")\n"
    "\n"
    "        try:\n"
    "            self.play(group.animate.move_to(ORIGIN), run_time=2.0)\n"
    "        except RuntimeError as e:\n"
    "            raise RuntimeError(f\"Transform failed: {e}\")\n"
    "\n"
    "        self.wait(1)\n"
    "```\n"
    "Strictly adhere to these rules, define helpers inline to avoid NameError, "
    "wrap multimobject animations in VGroup, and produce self-contained, "
    "renderable Manim code every time."
)

# --- Code Validator --------------------------------------------------------

class CodeValidator:
    """
    Collection of static methods to validate generated Manim code.
    """

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
            raise RuntimeError("Missing import: 'import numpy as np'.")
        forbidden = ["import os", "import sys", "subprocess", "shutil"]
        for item in forbidden:
            if item in code:
                raise RuntimeError(f"Forbidden import detected: {item}")

    @staticmethod
    def validate_scene_class(code: str) -> None:
        tree = ast.parse(code)
        scenes = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef)
            and any(
                isinstance(base, ast.Name) and base.id == "Scene" for base in node.bases
            )
        ]
        if len(scenes) != 1:
            raise RuntimeError(f"Expected exactly one Scene subclass, found {len(scenes)}.")

    @staticmethod
    def validate_delimiters(code: str) -> None:
        pairs = [("(", ")"), ("[", "]"), ("{", "}")]
        for o, c in pairs:
            if code.count(o) != code.count(c):
                raise RuntimeError(f"Unmatched '{o}' vs '{c}'.")

    @staticmethod
    def validate_animation_methods(code: str) -> None:
        if "self.play(" not in code:
            logger.warning("No 'self.play' call detected.")

# --- Core Generation Logic -------------------------------------------------

def _clean_and_format_code(raw: str) -> str:
    code = re.sub(r"```python|```", "", raw)
    lines = [ln.rstrip() for ln in code.splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)

def generate_manim_code(prompt: str, max_retries: int = 3) -> str:
    """
    Generate and validate Manim code from a user prompt, retrying on failure.
    """
    validator = CodeValidator()

    for attempt in range(1, max_retries + 1):
        logger.info(f"Attempt {attempt}/{max_retries}…")
        try:
            client = get_client()
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2 + 0.1 * (attempt - 1),
                max_tokens=2000,
                top_p=0.9,
            )

            code = _sanitize_code(_clean_and_format_code(response.choices[0].message.content))

            # Run validations
            validator.validate_structure(code)
            validator.validate_syntax(code)
            validator.validate_scene_class(code)
            validator.validate_delimiters(code)
            validator.validate_animation_methods(code)

            logger.info("Code generation succeeded.")
            return code

        except Exception as exc:
            logger.warning(f"Generation failed: {exc}")
            if attempt == max_retries:
                logger.error("Exhausted all retries.")
                raise RuntimeError(f"Code generation failed after {attempt} attempts: {exc}")
            time.sleep(1)

    # Should never be reached
    raise RuntimeError("Unexpected code generation error.")

def generate_manim_code_with_fallback(prompt: str) -> str:
    """
    Try primary generation, then provide a minimal fallback scene if it fails.
    """
    try:
        return generate_manim_code(prompt)
    except RuntimeError as exc:
        logger.error(f"Primary failed: {exc}")
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
