"""
Simplified Generator - Converts technical specifications to Manim code.

Uses template-first approach: tries to match keywords to proven templates,
falls back to AI generation if no match, and has a guaranteed fallback.
"""

import os
import logging
import re
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Fix #2: Lazy-initialise the Groq client so a missing key doesn't crash the
# entire application at import time. The app can boot and report "degraded"
# instead of dying with an unhandled exception before FastAPI even starts.
# ---------------------------------------------------------------------------

_groq_client = None  # module-level singleton; populated on first use


def get_client():
    """
    Return the (lazily-initialised) Groq client singleton.

    Fix #1: This function is explicitly exported so that app.py's health-check
    can call `from .generator import get_client` without an ImportError.

    Fix #2: Initialisation is deferred here rather than at module load, so a
    missing GROQ_API_KEY causes a clear RuntimeError at request time instead of
    an unhandled crash during server startup.
    """
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY environment variable is not set. "
                "Get your key from https://console.groq.com/keys and add it to .env"
            )
        try:
            from groq import Groq  # import inside function to allow testing without groq installed
            _groq_client = Groq(api_key=api_key)
        except Exception as exc:
            raise RuntimeError(f"Failed to initialise Groq client: {exc}") from exc
    return _groq_client


# Model selection — configurable via environment variable
MODEL_NAME = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Import template utilities after defining get_client (avoids circular issues)
from .templates import match_template, TEMPLATE_FALLBACK  # noqa: E402

# Enhanced AI generation prompt with template awareness
AI_SYSTEM_PROMPT = """You are a Manim code expert. Generate VALID Manim v0.17+ Python code based on technical specifications.

You will receive a detailed technical specification describing an animation. Your job is to write working Python code using the Manim library that matches this specification as closely as possible.

TEMPLATE PATTERNS YOU SHOULD KNOW:
Our system has proven templates for common patterns. When the spec matches these, you can adapt the pattern:

1. **Point Plotting**: For coordinates like (0,2), (2,0), (4,2)
   - Extract the coordinate pairs
   - Calculate appropriate axis ranges to fit all points
   - Use `axes.c2p(x, y)` to convert coordinates to scene positions
   - Create Dot objects at each coordinate
   - Add labels showing the coordinates

2. **Transformations**: For "X to Y" patterns
   - Create both source and target shapes
   - Use Create() for source
   - Use ReplacementTransform(source, target) for morphing

3. **Networks/Graphs**: For multi-node structures
   - Use VGroup with list comprehensions: `VGroup(*[Circle(...) for ...])`
   - Position nodes at specific coordinates
   - Connect with Lines using nested loops: `for n1 in layer1 for n2 in layer2`

4. **Motion**: For bouncing, moving, sliding
   - Create path with ArcBetweenPoints or Line
   - Use MoveAlongPath(object, path)

CRITICAL RULES:
1. Output ONLY Python code (no markdown, no explanations)
2. Use class name: GeneratedScene(Scene) or GeneratedScene(ThreeDScene) for 3D
3. Import: from manim import *
4. Use standard Manim objects: Circle, Square, Line, Text, Dot, Arrow, Axes, etc.
5. Common animations: Create(), FadeIn(), FadeOut(), ReplacementTransform()
6. For motion: obj.animate.move_to(), MoveAlongPath()
7. For rotation: Rotate(obj, angle=..., about_point=...)
8. Use UP TO 6 self.play() calls
9. Always end with self.wait(1)
10. Ensure objects are VISIBLE (use colors like BLUE, RED, YELLOW, GREEN, not BLACK)
11. Position objects within range: x=[-6,6], y=[-3,3]
12. Extract specific parameters from the technical spec (coordinates, colors, sizes, counts)
13. **FORBIDDEN DEPRECATED METHODS**: DO NOT USE ShowCreation, Write, FadeInFrom - these are DEPRECATED in Manim v0.17+
    - Use Create() instead of ShowCreation()
    - Use Create() instead of Write() for most cases
    - Use FadeIn() instead of FadeInFrom()
14. **FORBIDDEN: MathTex, Tex, TexTemplate** - LaTeX is NOT installed in deployment environment
    - Use Text() for ALL labels, coordinates, and text content
    - Example: Text("(0, 2)", font_size=20) NOT MathTex("(0, 2)")
    - Simple text only, no mathematical typesetting
15. **CRITICAL: Line() syntax** - Line only accepts TWO points
    - Correct: Line(start_point, end_point, color=RED)
    - WRONG: Line(point1, point2, point3) - this will ERROR
    - For multiple connected points: create multiple Line objects OR use VMobject().set_points_as_corners([p1, p2, p3])
16. **FORBIDDEN CONSTANTS — these do NOT exist in Manim v0.17.3 and will cause NameError:**
    - `Z` → DOES NOT EXIST. Use `OUT` (= np.array([0, 0, 1])) for the Z-axis direction.
    - `Z_AXIS` → DOES NOT EXIST. Use `OUT` instead.
    - `X_AXIS` → DOES NOT EXIST. Use `RIGHT` (= np.array([1, 0, 0])) instead.
    - `Y_AXIS` → DOES NOT EXIST. Use `UP` (= np.array([0, 1, 0])) instead.
    - `np.pi` → only available if you `import numpy as np`. Use `PI` (Manim constant) instead.
    - `TAU` → IS available (= 2*PI). OK to use.
    - Summary of correct axis vectors: RIGHT=X, UP=Y, OUT=Z
17. **3D ANIMATIONS must use ThreeDScene, not Scene**
    - If you use ANY of: Cylinder, Sphere, Cube, Prism, Cone, ThreeDAxes, set_camera_orientation
      → the class MUST be `GeneratedScene(ThreeDScene)`, never `GeneratedScene(Scene)`
    - For 3D scenes: always call `self.set_camera_orientation(phi=75*DEGREES, theta=30*DEGREES)` first
    - For 3D scenes: always `import numpy as np` at the top (needed for np.array operations)
18. **AVOID complex 3D objects** on free-tier (CPU limited):
    - AVOID: Cylinder, Sphere, Cone — these render slowly
    - PREFER: Line, Dot, Circle, Arc, ParametricFunction — render in <10 seconds
    - For a DNA helix: use `ParametricFunction` with `np.sin`/`np.cos` in a 2D Scene, NOT Cylinders
19. **PERFORMANCE — CRITICAL for deployment on limited CPU:**
    - **NEVER use `Rotate()` on a VGroup with more than 8 objects** — it renders frame-by-frame
      and will time out (each frame takes 5-7 seconds × 60+ frames = timeout)
    - **NEVER use `run_time > 3`** — keep every self.play() call to run_time ≤ 3 seconds
    - **NEVER create more than 12 objects in a VGroup** — use ParametricFunction for smooth curves
    - **For any rotating/spinning animation**: use `obj.animate.rotate(angle)` in a short play()
      rather than `Rotate(obj, angle)` which is frame-by-frame heavy
    - **For helical/spiral shapes**: use ONE `ParametricFunction`, not many discrete objects

CORRECT DNA HELIX PATTERN (fast, renders in <30s):
```python
from manim import *
import numpy as np

class GeneratedScene(Scene):
    def construct(self):
        helix1 = ParametricFunction(
            lambda t: np.array([np.cos(t), np.sin(t), t/4]),
            t_range=[-3*PI, 3*PI], color=BLUE
        ).scale(1.5)
        helix2 = ParametricFunction(
            lambda t: np.array([np.cos(t + PI), np.sin(t + PI), t/4]),
            t_range=[-3*PI, 3*PI], color=RED
        ).scale(1.5)
        self.play(Create(helix1), Create(helix2), run_time=2)
        self.play(helix1.animate.rotate(PI/4), helix2.animate.rotate(PI/4), run_time=2)
        self.wait(1)
```

CUSTOMIZATION INSTRUCTIONS:
- If the spec mentions specific coordinates, USE THEM EXACTLY
- If the spec mentions specific colors, USE THEM
- If the spec mentions specific sizes/radii, USE THEM
- If the spec mentions counts (e.g., "3 circles"), CREATE THAT MANY
- Adapt the closest template pattern to match the specific requirements

DO NOT use undefined objects or custom classes.
DO NOT mix positional and keyword arguments.
Output pure Python code only."""


def extract_code_from_response(text: str) -> str:
    """Extract Python code from LLM response, handling markdown code blocks."""
    if not text:
        return ""

    # Try to extract from markdown code block
    pattern = r"```(?:python)?\n([\s\S]*?)```"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Return as-is if no code block found
    return text.strip()


def generate_with_ai(technical_spec: str, max_retries: int = 2) -> Optional[str]:
    """
    Generate Manim code using AI based on technical specification.

    On each retry, injects a feedback message explaining exactly why the
    previous attempt was rejected, allowing the LLM to self-correct.

    Fix #3: Exception messages are truncated to 200 chars before logging to
    prevent leaking SDK internals into log aggregators.
    """
    logger.info("Attempting AI code generation")
    last_rejection_reason: Optional[str] = None

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"AI generation attempt {attempt}/{max_retries}")

            # On retries, tell the LLM exactly why its previous code failed
            user_msg = f"Technical Specification:\n\n{technical_spec}\n\nGenerate Manim code:"
            if attempt > 1 and last_rejection_reason:
                user_msg = (
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
                    {"role": "user", "content": user_msg}
                ],
                temperature=0.2,
                max_tokens=1500,
            )

            if not response or not response.choices:
                logger.warning(f"AI attempt {attempt}: Empty response from API")
                last_rejection_reason = "The API returned an empty response."
                continue

            code = extract_code_from_response(response.choices[0].message.content)

            if not code or len(code) < 50:
                logger.warning(f"AI attempt {attempt}: Code too short or empty ({len(code)} chars)")
                last_rejection_reason = "The generated code was too short or empty."
                continue

            if "class GeneratedScene" not in code or "def construct" not in code:
                last_rejection_reason = "Missing required class GeneratedScene or def construct method."
                logger.warning(f"AI attempt {attempt}: {last_rejection_reason}")
                continue

            # Check for known-undefined Manim constants (NameError at render time)
            forbidden = _find_forbidden_constants(code)
            if forbidden:
                last_rejection_reason = (
                    f"Your code used undefined Manim v0.17.3 constants: {forbidden}. "
                    "Use RIGHT instead of X_AXIS, UP instead of Y_AXIS, OUT instead of Z/Z_AXIS. "
                    "Do NOT use MathTex, Tex, ShowCreation, or FadeInFrom."
                )
                logger.warning(f"AI attempt {attempt}: forbidden constants {forbidden} — retrying")
                continue

            # Check for Rotate() on complex VGroups (6+ sec/frame → timeout)
            has_rotate = bool(re.search(r'\bRotate\s*\(', code))
            range_count = len(re.findall(r'\brange\s*\(', code))
            if has_rotate and range_count >= 2:
                last_rejection_reason = (
                    "Your code uses Rotate() on a VGroup built with range() — this takes "
                    "6+ seconds per frame and will time out (renders ~400s total). "
                    "INSTEAD: use ParametricFunction for smooth curves (helix, spiral). "
                    "For a DNA helix, use two ParametricFunction objects with sin/cos, "
                    "then animate with obj.animate.rotate(PI/4) in a single play()."
                )
                logger.warning(f"AI attempt {attempt}: Rotate()+range() slow pattern — retrying")
                continue

            # Check for excessive run_time values
            large_rts = re.findall(r'run_time\s*=\s*(\d+(?:\.\d+)?)', code)
            if any(float(rt) > 4 for rt in large_rts):
                last_rejection_reason = (
                    f"Your code uses run_time={large_rts} which exceeds the 4s limit. "
                    "Keep every self.play() call to run_time ≤ 3."
                )
                logger.warning(f"AI attempt {attempt}: run_time {large_rts} too large — retrying")
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




# ---------------------------------------------------------------------------
# Manim constant / API guard
# ---------------------------------------------------------------------------

# Names that LLMs commonly hallucinate but DON'T exist in Manim v0.17.3.
# Using any of these causes an immediate NameError at render time.
_FORBIDDEN_MANIM_NAMES = {
    # Axis constants — use RIGHT / UP / OUT
    r'\bZ\b',         # Z → OUT
    r'\bZ_AXIS\b',    # Z_AXIS → OUT
    r'\bX_AXIS\b',    # X_AXIS → RIGHT
    r'\bY_AXIS\b',    # Y_AXIS → UP
    # Old Manim API
    r'\bShowCreation\b',
    r'\bFadeInFrom\b',
    r'\bMathTex\b',
    r'\bTex\b(?!t)',   # Tex but not Text
}

def _find_forbidden_constants(code: str) -> list:
    """Return list of forbidden Manim names found in code, empty list if clean."""
    found = []
    for pattern in _FORBIDDEN_MANIM_NAMES:
        if re.search(pattern, code):
            found.append(pattern.replace(r'\b', '').replace('(?!t)', ''))
    return found


def validate_code_basic(code: str) -> bool:
    """
    Basic validation of generated code.

    Returns True if code passes basic structural checks AND does not contain
    constants that are undefined in Manim v0.17.3.
    """
    if not code or len(code) < 50:
        return False

    # Check for required elements
    required = [
        "from manim import",
        "class GeneratedScene",
        "def construct",
        "self.play",
        "self.wait"
    ]

    if not all(req in code for req in required):
        return False

    # Reject code with known-undefined Manim constants
    if _find_forbidden_constants(code):
        return False

    # Reject code that will almost certainly time out on HF free-tier:
    # Rotate() combined with a large range() → frame-by-frame on many objects
    # Example: Rotate(VGroup of 40 Cylinders) takes 6s/frame × 60 frames = 360s
    has_rotate_animation = bool(re.search(r'\bRotate\s*\(', code))
    range_counts = len(re.findall(r'\brange\s*\(', code))
    if has_rotate_animation and range_counts >= 2:
        logger.warning(
            "Code rejected: Rotate() combined with multiple range() calls "
            "will exceed render timeout on free-tier CPU."
        )
        return False

    # Reject suspiciously large run_time values (> 4 seconds per play call)
    large_runtimes = re.findall(r'run_time\s*=\s*(\d+(?:\.\d+)?)', code)
    if any(float(rt) > 4 for rt in large_runtimes):
        logger.warning(
            f"Code rejected: run_time values {large_runtimes} exceed 4s limit."
        )
        return False

    return True


def _generate_dynamic_fallback(technical_spec: str) -> str:
    """
    Generate a dynamic fallback animation when AI and templates fail.
    Instead of rendering a generic blue circle, this displays a clean title-card
    with the user's requested concept based on the technical specification.
    """
    import textwrap
    import re
    # Try to extract the core subject or just use the first line of the spec
    subject = "Requested Animation"
    
    # Simple extraction heuristic based on our prompt_expander format
    match = re.search(r"Animation Type:\s*([^\n]+)", technical_spec, re.IGNORECASE)
    if match and match.group(1).strip():
        subject = match.group(1).strip().title()
    else:
        # Just grab the first few lines, strip empty ones
        lines = [line.strip() for line in technical_spec.split('\n') if line.strip()]
        if lines:
            subject = lines[0][:40] + ("..." if len(lines[0]) > 40 else "")

    # Clean the subject for safe text injection (escape quotes)
    safe_subject = subject.replace('"', '\\"').replace("'", "\\'")
    
    # Word wrap so long text doesn't flow off screen
    wrapped_lines = textwrap.wrap(safe_subject, width=30)
    formatted_subject = "\\n".join(wrapped_lines)

    return f'''from manim import *

class GeneratedScene(Scene):
    def construct(self):
        title = Text("Fallback Generation:", font_size=36, color=BLUE)
        subtitle = Text("{formatted_subject}", font_size=40)
        warning = Text("(Complexity exceeded AI limits)", font_size=24, color=GRAY)
        
        group = VGroup(title, subtitle, warning).arrange(DOWN, buff=0.5)
        
        self.play(FadeIn(group, shift=UP), run_time=1.5)
        self.wait(1.5)
        self.play(FadeOut(group, shift=DOWN), run_time=1.5)
'''


def generate_code(technical_spec: str) -> Tuple[str, str]:
    """
    Generate Manim code from technical specification.

    Uses three-tier approach:
    1. Template matching (fastest, most reliable)
    2. AI generation (flexible, for novel requests)
    3. Fallback template (guaranteed to work)

    Returns:
        Tuple of (manim_code, generation_method) where generation_method is one
        of: "template", "ai", "fallback".  The method is surfaced so callers can
        log or expose it without having to re-derive it.
    """
    logger.info("Starting code generation")

    # Check if request has enhanced requirements that templates can't handle
    spec_lower = technical_spec.lower()
    enhanced_keywords = [
        'line through', 'connect', 'draw a line', 'add a line',
        'show trajectory', 'fit a curve', 'regression',
        'and also', 'as well as', 'additionally', 'plus'
    ]

    has_enhanced_requirements = any(keyword in spec_lower for keyword in enhanced_keywords)

    # Tier 1: Try template matching (only if no enhanced requirements)
    if not has_enhanced_requirements:
        logger.info("Attempting template matching")
        template_code = match_template(technical_spec)

        # match_template returns None when no confident match found
        # (it returns TEMPLATE_FALLBACK when confidence > 0 but we want to
        #  distinguish "no match" from "fallback" — see templates.py fix)
        if template_code is not None and template_code != TEMPLATE_FALLBACK:
            logger.info("Template match found, using proven code")
            return template_code, "template"
    else:
        logger.info("Enhanced requirements detected, skipping templates and using AI")

    # Tier 2: Try AI generation for novel/enhanced requests
    logger.info("No confident template match or enhanced request, trying AI generation")
    ai_code = generate_with_ai(technical_spec)

    if ai_code and validate_code_basic(ai_code):
        logger.info("AI generation successful")
        return ai_code, "ai"

    # Fix #4: Explicitly log the fallback path so it is visible in production logs.
    logger.warning(
        "ALL generation tiers failed (template→AI). "
        "Returning dynamic TEMPLATE_FALLBACK. "
        "Check GROQ_API_KEY validity and Groq API status."
    )
    fallback_code = _generate_dynamic_fallback(technical_spec)
    return fallback_code, "fallback"


def generate_code_with_retries(technical_spec: str, max_attempts: int = 2) -> Tuple[str, str]:
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