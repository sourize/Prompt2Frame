"""
Generator - Converts technical specifications to Manim code.

Uses template-first approach: tries to match keywords to proven templates,
falls back to AI generation if no match, and has a guaranteed fallback.
"""

import os
import logging
import re
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

_groq_client = None


def get_client():
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY environment variable is not set. "
                "Get your key from https://console.groq.com/keys and add it to .env"
            )
        try:
            from groq import Groq

            _groq_client = Groq(api_key=api_key)
        except Exception as exc:
            raise RuntimeError(f"Failed to initialise Groq client: {exc}") from exc
    return _groq_client


MODEL_NAME = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

from .templates import match_template, TEMPLATE_FALLBACK  # noqa: E402

AI_SYSTEM_PROMPT = (
    "You are a Manim code expert. Generate VALID Manim v0.17+ Python code based on "
    "technical specifications.\n\n"
    "RULE #0 — ANIMATION ORDER (HIGHEST PRIORITY — NEVER VIOLATE)\n"
    "Write every self.play() call in the EXACT chronological order described.\n"
    "- 'draw a circle, then transform it into a square':\n"
    "    Step 1: self.play(Create(circle))\n"
    "    Step 2: self.play(ReplacementTransform(circle, square))\n"
    "  NEVER reverse these.\n"
    "- Each narrative step maps to one self.play() call, in order.\n"
    "- NEVER group all creations first and animations second.\n"
    "- NEVER reorder steps for aesthetic or technical reasons.\n\n"
    "EXAMPLE 1 — 'Draw a red circle and transform it into a blue square':\n"
    "from manim import *\n\n"
    "class GeneratedScene(Scene):\n"
    "    def construct(self):\n"
    "        circle = Circle(radius=1.5, color=RED)\n"
    "        circle.set_fill(RED, opacity=0.5)\n"
    "        self.play(Create(circle))\n"
    "        self.wait(0.5)\n"
    "        square = Square(side_length=2.5, color=BLUE)\n"
    "        square.set_fill(BLUE, opacity=0.5)\n"
    "        self.play(ReplacementTransform(circle, square))\n"
    "        self.wait(1)\n\n"
    "EXAMPLE 2 — 'Show the word Hello, move it up, then fade it out':\n"
    "from manim import *\n\n"
    "class GeneratedScene(Scene):\n"
    "    def construct(self):\n"
    "        label = Text('Hello', font_size=60, color=YELLOW)\n"
    "        self.play(Write(label))\n"
    "        self.wait(0.5)\n"
    "        self.play(label.animate.shift(UP * 2))\n"
    "        self.wait(0.5)\n"
    "        self.play(FadeOut(label))\n"
    "        self.wait(0.5)\n\n"
    "EXAMPLE 3 — 'Draw a green arrow pointing right, then rotate it 90 degrees':\n"
    "from manim import *\n\n"
    "class GeneratedScene(Scene):\n"
    "    def construct(self):\n"
    "        arrow = Arrow(start=LEFT * 2, end=RIGHT * 2, color=GREEN)\n"
    "        self.play(Create(arrow))\n"
    "        self.wait(0.5)\n"
    "        self.play(arrow.animate.rotate(PI / 2))\n"
    "        self.wait(1)\n\n"
    "CRITICAL RULES:\n"
    "1. Output ONLY Python code (no markdown, no explanations)\n"
    "2. Class name: GeneratedScene(Scene) or GeneratedScene(ThreeDScene) for 3D\n"
    "3. Import: from manim import *\n"
    "4. Standard objects: Circle, Square, Line, Text, Dot, Arrow, Axes, etc.\n"
    "5. Animations: Create(), Write(), FadeIn(), FadeOut(), ReplacementTransform()\n"
    "6. Motion: obj.animate.move_to() or MoveAlongPath()\n"
    "7. Rotation: obj.animate.rotate(angle)\n"
    "8. Use UP TO 12 self.play() calls — use as many as the description requires\n"
    "9. Always end with self.wait(1)\n"
    "10. Objects must be VISIBLE: use BLUE, RED, YELLOW, GREEN (not BLACK on black bg)\n"
    "11. Keep positions within: x=[-6,6], y=[-3,3]\n"
    "12. Use specific parameters from the spec (coordinates, colors, sizes, counts)\n\n"
    "FORBIDDEN — these cause errors in Manim v0.17.3:\n"
    "13. ShowCreation → use Create() instead\n"
    "14. FadeInFrom → use FadeIn() instead\n"
    "15. Write() IS valid for Text — do NOT replace it with Create() for text\n"
    "16. MathTex / Tex → use Text() for ALL labels (LaTeX not installed)\n"
    "17. Line() only accepts TWO points:\n"
    "    - CORRECT: Line(start_point, end_point, color=RED)\n"
    "    - For multiple segments: use multiple Line objects or VMobject().set_points_as_corners([p1,p2,p3])\n"
    "18. Undefined constants — these do NOT exist in Manim v0.17.3:\n"
    "    - Z / Z_AXIS → use OUT\n"
    "    - X_AXIS → use RIGHT\n"
    "    - Y_AXIS → use UP\n"
    "    - np.pi → use PI (or import numpy as np first)\n"
    "    - TAU is valid\n"
    "19. 3D scenes: use ThreeDScene, call set_camera_orientation() first, import numpy as np\n"
    "20. NEVER use Rotate() on a VGroup with more than 8 objects (causes timeout)\n"
    "21. NEVER use run_time > 3 per self.play() call\n"
    "22. NEVER use about_axis= inside rotate(); use axis= instead\n"
    "23. Avoid Cylinder, Sphere, Cone on free-tier — use ParametricFunction instead\n\n"
    "Do NOT use undefined objects or custom classes.\n"
    "Output pure Python code only."
)


def extract_code_from_response(text: str) -> str:
    """Extract Python code from LLM response, handling markdown code blocks."""
    if not text:
        return ""
    pattern = r"```(?:python)?\n([\s\S]*?)```"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text.strip()


_FORBIDDEN_MANIM_NAMES = {
    r"\bZ\b",
    r"\bZ_AXIS\b",
    r"\bX_AXIS\b",
    r"\bY_AXIS\b",
    r"\babout_axis\b",
    r"\bShowCreation\b",
    r"\bFadeInFrom\b",
    r"\bMathTex\b",
    r"\bTex\b(?!t)",
}


def _find_forbidden_constants(code: str) -> list:
    """Return list of forbidden Manim names found in code, empty list if clean."""
    found = []
    for pattern in _FORBIDDEN_MANIM_NAMES:
        if re.search(pattern, code):
            found.append(pattern.replace(r"\b", "").replace("(?!t)", ""))
    return found


def generate_with_ai(technical_spec: str, max_retries: int = 2) -> Optional[str]:
    """Generate Manim code using AI based on technical specification."""
    logger.info("Attempting AI code generation")
    last_rejection_reason: Optional[str] = None

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"AI generation attempt {attempt}/{max_retries}")

            ordering_reminder = (
                "ORDERING REMINDER: Write self.play() calls in the EXACT order "
                "described below. The first action mentioned must be the first "
                "self.play() call. Do NOT group all creations first.\n\n"
            )

            user_msg = (
                f"{ordering_reminder}"
                f"Technical Specification:\n\n{technical_spec}\n\n"
                f"Generate Manim code:"
            )

            if attempt > 1 and last_rejection_reason:
                user_msg = (
                    f"{ordering_reminder}"
                    f"Technical Specification:\n\n{technical_spec}\n\n"
                    f"IMPORTANT — your previous attempt was REJECTED:\n"
                    f"{last_rejection_reason}\n\n"
                    f"Fix the above issue and regenerate correct Manim code:"
                )

            client = get_client()
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": AI_SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.1,
                max_tokens=2000,
            )

            if not response or not response.choices:
                logger.warning(f"AI attempt {attempt}: Empty response from API")
                last_rejection_reason = "The API returned an empty response."
                continue

            code = extract_code_from_response(response.choices[0].message.content)

            if not code or len(code) < 50:
                logger.warning(
                    f"AI attempt {attempt}: Code too short ({len(code)} chars)"
                )
                last_rejection_reason = "The generated code was too short or empty."
                continue

            if "class GeneratedScene" not in code or "def construct" not in code:
                last_rejection_reason = (
                    "Missing required class GeneratedScene or def construct."
                )
                logger.warning(f"AI attempt {attempt}: {last_rejection_reason}")
                continue

            forbidden = _find_forbidden_constants(code)
            if forbidden:
                last_rejection_reason = (
                    f"Your code used undefined Manim v0.17.3 constants: {forbidden}. "
                    "Use RIGHT instead of X_AXIS, UP instead of Y_AXIS, OUT instead of Z/Z_AXIS. "
                    "Do NOT use about_axis, MathTex, Tex, ShowCreation, or FadeInFrom."
                )
                logger.warning(
                    f"AI attempt {attempt}: forbidden constants {forbidden} — retrying"
                )
                continue

            has_rotate = bool(re.search(r"\bRotate\s*\(", code))
            range_count = len(re.findall(r"\brange\s*\(", code))
            if has_rotate and range_count >= 2:
                last_rejection_reason = (
                    "Your code uses Rotate() on a VGroup built with range() — this will time out. "
                    "Use ParametricFunction for smooth curves instead. "
                    "Animate with obj.animate.rotate(PI/4) in a single play()."
                )
                logger.warning(
                    f"AI attempt {attempt}: Rotate()+range() pattern — retrying"
                )
                continue

            large_rts = re.findall(r"run_time\s*=\s*(\d+(?:\.\d+)?)", code)
            if any(float(rt) > 4 for rt in large_rts):
                last_rejection_reason = (
                    f"Your code uses run_time={large_rts} which exceeds the 4s limit. "
                    "Keep every self.play() call to run_time <= 3."
                )
                logger.warning(f"AI attempt {attempt}: run_time too large — retrying")
                continue

            logger.info(f"AI code generation successful ({len(code)} characters)")
            return code

        except Exception as e:
            safe_error = str(e)[:200]
            logger.error(f"AI attempt {attempt} failed: {safe_error}")
            last_rejection_reason = f"API error: {safe_error}"
            if attempt == max_retries:
                return None
            continue

    return None


def validate_code_basic(code: str) -> bool:
    """Basic validation of generated code."""
    if not code or len(code) < 50:
        return False

    required = [
        "from manim import",
        "class GeneratedScene",
        "def construct",
        "self.play",
        "self.wait",
    ]

    if not all(req in code for req in required):
        return False

    if _find_forbidden_constants(code):
        return False

    has_rotate_animation = bool(re.search(r"\bRotate\s*\(", code))
    range_counts = len(re.findall(r"\brange\s*\(", code))
    if has_rotate_animation and range_counts >= 2:
        logger.warning("Code rejected: Rotate() + range() will exceed render timeout.")
        return False

    large_runtimes = re.findall(r"run_time\s*=\s*(\d+(?:\.\d+)?)", code)
    if any(float(rt) > 4 for rt in large_runtimes):
        logger.warning(
            f"Code rejected: run_time values {large_runtimes} exceed 4s limit."
        )
        return False

    return True


def _generate_dynamic_fallback(technical_spec: str) -> str:
    """Generate a dynamic fallback animation when AI and templates fail."""
    import textwrap

    subject = "Requested Animation"
    match = re.search(r"Animation Type:\s*([^\n]+)", technical_spec, re.IGNORECASE)
    if match and match.group(1).strip():
        subject = match.group(1).strip().title()
    else:
        lines = [line.strip() for line in technical_spec.split("\n") if line.strip()]
        if lines:
            subject = lines[0][:40] + ("..." if len(lines[0]) > 40 else "")

    safe_subject = subject.replace('"', '\\"').replace("'", "\\'")
    wrapped_lines = textwrap.wrap(safe_subject, width=30)
    formatted_subject = "\\n".join(wrapped_lines)

    return (
        "from manim import *\n\n"
        "class GeneratedScene(Scene):\n"
        "    def construct(self):\n"
        '        title = Text("Fallback Generation:", font_size=36, color=BLUE)\n'
        f'        subtitle = Text("{formatted_subject}", font_size=40)\n'
        '        warning = Text("(Complexity exceeded AI limits)", font_size=24, color=GRAY)\n\n'
        "        group = VGroup(title, subtitle, warning).arrange(DOWN, buff=0.5)\n\n"
        "        self.play(FadeIn(group, shift=UP), run_time=1.5)\n"
        "        self.wait(1.5)\n"
        "        self.play(FadeOut(group, shift=DOWN), run_time=1.5)\n"
        "        self.wait(1)\n"
    )


def generate_code(technical_spec: str) -> Tuple[str, str]:
    """
    Generate Manim code from technical specification.

    Three-tier approach:
    1. Template matching (fastest, most reliable)
    2. AI generation (flexible, for novel requests)
    3. Dynamic fallback (guaranteed to work)

    Returns:
        Tuple of (manim_code, generation_method)
    """
    logger.info("Starting code generation")

    spec_lower = technical_spec.lower()
    enhanced_keywords = [
        "line through",
        "connect",
        "draw a line",
        "add a line",
        "show trajectory",
        "fit a curve",
        "regression",
        "and also",
        "as well as",
        "additionally",
        "plus",
    ]
    has_enhanced_requirements = any(kw in spec_lower for kw in enhanced_keywords)

    if not has_enhanced_requirements:
        logger.info("Attempting template matching")
        template_code = match_template(technical_spec)
        if template_code is not None and template_code != TEMPLATE_FALLBACK:
            logger.info("Template match found, using proven code")
            return template_code, "template"
    else:
        logger.info("Enhanced requirements detected, skipping templates")

    logger.info("Trying AI generation")
    ai_code = generate_with_ai(technical_spec)

    if ai_code and validate_code_basic(ai_code):
        logger.info("AI generation successful")
        return ai_code, "ai"

    logger.warning(
        "ALL generation tiers failed (template->AI). "
        "Returning dynamic fallback. Check GROQ_API_KEY validity."
    )
    fallback_code = _generate_dynamic_fallback(technical_spec)
    return fallback_code, "fallback"


def generate_code_with_retries(
    technical_spec: str, max_attempts: int = 2
) -> Tuple[str, str]:
    """
    Generate code with retry logic.

    Returns:
        Tuple of (manim_code, generation_method)
    """
    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(f"Code generation attempt {attempt}/{max_attempts}")
            code, method = generate_code(technical_spec)

            if validate_code_basic(code):
                return code, method
            else:
                logger.warning(f"Attempt {attempt}: Basic validation failed")
                continue

        except Exception as e:
            safe_error = str(e)[:200]
            logger.error(f"Attempt {attempt} error: {safe_error}")
            if attempt == max_attempts:
                logger.error("All attempts failed, returning fallback")
                return TEMPLATE_FALLBACK, "fallback"
            continue

    return TEMPLATE_FALLBACK, "fallback"
