"""
Generator - Converts user prompts directly into Manim code using AI.

Architecture inspired by rohitg00/manim-video-generator:
  - No template matching — AI handles everything
  - Multi-stage prompting: intent analysis → code generation
  - Self-healing: render errors are fed back to the LLM for auto-correction
  - 3Blue1Brown-inspired visual style by default
"""

import ast
import os
import re
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Groq client (lazy singleton)
# ---------------------------------------------------------------------------

_groq_client = None


def get_client():
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. "
                "Get your key from https://console.groq.com/keys and add it to .env"
            )
        try:
            from groq import Groq

            _groq_client = Groq(api_key=api_key)
        except Exception as exc:
            raise RuntimeError(f"Failed to initialise Groq client: {exc}") from exc
    return _groq_client


MODEL_NAME = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# ---------------------------------------------------------------------------
# Master system prompt
# Inspired by the reference project's prompt-engine approach:
#   - Explicit visual style (3Blue1Brown-like dark background)
#   - Comprehensive Manim API reference baked in
#   - Ordering rule at the very top
#   - Self-contained: no templates needed
# ---------------------------------------------------------------------------

MASTER_SYSTEM_PROMPT = (
    "You are an expert Manim animation programmer. "
    "Your sole job is to write VALID, RUNNABLE Manim v0.17+ Python code "
    "that exactly matches what the user describes.\n\n"
    # ── RULE 0: ORDER ──────────────────────────────────────────────────────
    "══════════════════════════════════════════\n"
    "RULE 0 — ANIMATION ORDER (NEVER VIOLATE)\n"
    "══════════════════════════════════════════\n"
    "Write every self.play() in the EXACT order the user described.\n"
    "  'Draw a red circle, then transform it into a blue square'\n"
    "   → Step 1: self.play(Create(circle))          ← circle FIRST\n"
    "   → Step 2: self.play(ReplacementTransform(...)) ← transform SECOND\n"
    "NEVER group all creations first. NEVER reorder for aesthetics.\n\n"
    # ── CRITICAL: CAMERA FRAMING (MOST IMPORTANT) ─────────────────────────
    "══════════════════════════════════════════════════════\n"
    "RULE 1 — CAMERA FRAMING (CRITICAL: Objects must be VISIBLE!)\n"
    "══════════════════════════════════════════════════════\n"
    "ALWAYS ensure objects are centered in frame. Use MovingCameraScene:\n\n"
    "class GeneratedScene(MovingCameraScene):\n"
    "    def construct(self):\n"
    "        # Your objects here\n"
    "        # ...\n"
    "        # AFTER creating objects, ALWAYS center the camera on them:\n"
    "        self.play(self.camera.frame.animate.move_to(ORIGIN))\n"
    "        # To zoom out to fit all objects:\n"
    "        # self.play(self.camera.frame.animate.set_width(max_width + 1))\n\n"
    "FRAMING RULES (ALWAYS FOLLOW):\n"
    "- Use MovingCameraScene as the base class for ALL animations\n"
    "- After creating objects, ALWAYS add: self.play(self.camera.frame.animate.move_to(ORIGIN))\n"
    "- If objects are spread out, use self.camera.frame.animate.set_width(width) to fit all\n"
    "- To focus on a specific object: self.play(self.camera.frame.animate.move_to(obj.get_center()))\n"
    "- Use self.play(self.camera.frame.animate.scale(1.5)) to zoom in on details\n"
    "- NEVER let objects go off-screen — if object x > 5, zoom out or shift camera\n\n"
    # ── VISUAL STYLE ───────────────────────────────────────────────────────
    "══════════════════════════════════════════\n"
    "VISUAL STYLE (3Blue1Brown-inspired)\n"
    "══════════════════════════════════════════\n"
    "- Background is always BLACK (default in Manim)\n"
    "- Use vivid colors: BLUE, RED, GREEN, YELLOW, ORANGE, PURPLE, TEAL, PINK\n"
    "- Shapes: use set_fill(color, opacity=0.3-0.7) for filled shapes\n"
    "- Text: always use Text(), never MathTex/Tex (LaTeX not installed)\n"
    "- Stroke width: 2-4 for shapes, 1 for connection lines\n"
    "- Keep objects within x=[-6,6], y=[-3,3] by default\n"
    "- For wide layouts: use MovingCameraScene + camera.frame.set_width(12) to fit all\n\n"
    # ── MANIM API REFERENCE ────────────────────────────────────────────────
    "══════════════════════════════════════════\n"
    "MANIM v0.17+ API QUICK REFERENCE\n"
    "══════════════════════════════════════════\n"
    "BASE CLASS (ALWAYS USE):\n"
    "  class GeneratedScene(MovingCameraScene):  # Use MovingCameraScene for camera control\n\n"
    "CAMERA CONTROL (MovingCameraScene):\n"
    "  self.camera.frame.move_to(point)                    # Center camera on point\n"
    "  self.camera.frame.animate.move_to(point)           # Animate camera movement\n"
    "  self.camera.frame.set_width(width)                 # Set frame width (zoom)\n"
    "  self.camera.frame.animate.set_width(width)         # Animate zoom\n"
    "  self.camera.frame.scale(factor)                    # Scale relative to current\n"
    "  self.camera.frame.animate.scale(factor)           # Animate scaling\n\n"
    "BASIC SHAPES:\n"
    "  Circle(radius=1.0, color=BLUE)\n"
    "  Square(side_length=2.0, color=RED)\n"
    "  Rectangle(width=3, height=2, color=GREEN)\n"
    "  Triangle(color=YELLOW)\n"
    "  Polygon(*vertices, color=ORANGE)\n"
    "  Line(start, end, color=WHITE)\n"
    "  Arrow(start, end, color=WHITE)\n"
    "  Dot(point, color=WHITE)\n"
    "  Arc(radius=1, angle=PI, color=BLUE)\n"
    "  ArcBetweenPoints(start, end, angle=PI/2)\n"
    "  Ellipse(width=3, height=2, color=TEAL)\n"
    "  RoundedRectangle(corner_radius=0.2, color=PURPLE)\n\n"
    "COMPLEX SHAPES (for advanced animations):\n"
    "  # Parametric curves (spirals, hearts, custom paths)\n"
    "  ParametricFunction(lambda t: np.array([t, np.sin(t), 0]), t_range=[-PI, PI])\n"
    "  # Custom polygon with vertex list\n"
    "  Polygon(UL, UR, RIGHT*2, DOWN, color=ORANGE)\n"
    "  # Star shape using parametric\n"
    "  ParametricFunction(lambda t: np.array([np.cos(t)*np.sin(t*3), np.sin(t)*np.sin(t*3), 0]), t_range=[0, TAU])\n\n"
    "TEXT:\n"
    "  Text('hello', font_size=48, color=WHITE)\n"
    "  # NEVER use MathTex, Tex, or TexTemplate — LaTeX not installed\n\n"
    "POSITIONING:\n"
    "  obj.move_to(point)          # e.g. move_to(LEFT * 2 + UP)\n"
    "  obj.shift(direction)        # e.g. shift(RIGHT * 3)\n"
    "  obj.next_to(other, DOWN)    # relative positioning\n"
    "  obj.to_corner(UL)           # corners: UL, UR, DL, DR\n"
    "  obj.to_edge(LEFT)           # edges: LEFT, RIGHT, UP, DOWN\n"
    "  Directions: UP, DOWN, LEFT, RIGHT, ORIGIN, UL, UR, DL, DR\n"
    "  Combine: LEFT*2 + UP*0.5\n\n"
    "GETTING OBJECT BOUNDS (for framing):\n"
    "  obj.get_center()            # Get center point of object\n"
    "  obj.get_width()             # Get width of object\n"
    "  obj.get_height()            # Get height of object\n"
    "  # To find bounding box of group:\n"
    "  group.get_all_points()      # All corner points\n\n"
    "ANIMATIONS (self.play(...)):\n"
    "  Create(obj)                 # draw shape outline\n"
    "  Write(text_obj)             # write text stroke by stroke\n"
    "  FadeIn(obj)                 # fade in\n"
    "  FadeOut(obj)                # fade out\n"
    "  GrowFromCenter(obj)         # grow from center point\n"
    "  ReplacementTransform(a, b)  # morph a into b (a is removed)\n"
    "  Transform(a, b)             # morph a into b (a stays)\n"
    "  obj.animate.shift(v)        # move smoothly\n"
    "  obj.animate.scale(factor)   # scale smoothly\n"
    "  obj.animate.rotate(angle)   # rotate smoothly\n"
    "  obj.animate.set_color(c)    # change color smoothly\n"
    "  obj.animate.move_to(point)  # move to point smoothly\n"
    "  MoveAlongPath(obj, path)    # move along a curve\n"
    "  Rotate(obj, angle, about_point=ORIGIN)  # rotate around point\n"
    "  Homotopy()                  # smooth morph between coordinate functions\n"
    "  # Emphasis animations:\n"
    "  Indicate(obj, color=BLUE)  # highlight an object\n"
    "  Flash(obj)                  # flash effect around object\n"
    "  WiggleOutThenIn(obj)        # wiggle animation\n\n"
    "GROUPING:\n"
    "  group = VGroup(a, b, c)           # group objects\n"
    "  group.arrange(RIGHT, buff=0.5)    # lay out in a row\n"
    "  group.arrange(DOWN, buff=0.3)     # lay out in a column\n"
    "  group.move_to(ORIGIN)             # center entire group\n"
    "  group.set_width(max_width)        # scale to fit width\n\n"
    "AXES AND GRAPHS:\n"
    "  axes = Axes(x_range=[-3,3,1], y_range=[-2,2,1])\n"
    "  graph = axes.plot(lambda x: x**2, color=BLUE)\n"
    "  dot = Dot(axes.c2p(1, 1), color=RED)  # convert coords to position\n\n"
    "TIMING:\n"
    "  self.play(anim, run_time=2)   # 2-second animation (max 3)\n"
    "  self.wait(1)                  # pause for 1 second\n"
    "  # Play multiple at once: self.play(Create(a), FadeIn(b))\n\n"
    "3D SCENES:\n"
    "  class GeneratedScene(ThreeDScene):  # use ThreeDScene for 3D\n"
    "      def construct(self):\n"
    "          self.set_camera_orientation(phi=75*DEGREES, theta=30*DEGREES)\n"
    "  # For 3D: import numpy as np\n"
    "  # Use ParametricFunction for helices/spirals, NOT Cylinder/Sphere (too slow)\n\n"
    # ── FORBIDDEN ──────────────────────────────────────────────────────────
    "══════════════════════════════════════════\n"
    "FORBIDDEN — causes immediate errors\n"
    "══════════════════════════════════════════\n"
    "- MathTex, Tex, TexTemplate  → use Text() instead\n"
    "- ShowCreation                → use Create()\n"
    "- FadeInFrom                  → use FadeIn()\n"
    "- X_AXIS, Y_AXIS, Z, Z_AXIS   → use RIGHT, UP, OUT\n"
    "- about_axis=  in rotate()    → use axis= instead\n"
    "- Line(p1, p2, p3)            → Line only takes 2 points\n"
    "- run_time > 3                → keep all run_time <= 3\n"
    "- Rotate() on VGroup of 8+ objects  → causes timeout\n"
    "- np.pi without import numpy as np  → use PI instead\n"
    "- scene.set_camera_orientation()    → ThreeDScene only\n\n"
    # ── WORKED EXAMPLES (IMPROVED WITH CAMERA FRAMING) ─────────────────────
    "══════════════════════════════════════════════\n"
    "WORKED EXAMPLES (Study These Carefully!)\n"
    "══════════════════════════════════════════════\n"
    "Example 1 — 'Draw a red circle and transform it into a blue square':\n"
    "from manim import *\n"
    "class GeneratedScene(MovingCameraScene):\n"
    "    def construct(self):\n"
    "        circle = Circle(radius=1.5, color=RED)\n"
    "        circle.set_fill(RED, opacity=0.4)\n"
    "        circle.move_to(ORIGIN)\n"
    "        self.play(Create(circle))\n"
    "        self.wait(0.5)\n"
    "        # Center camera on the circle\n"
    "        self.play(self.camera.frame.animate.move_to(ORIGIN))\n"
    "        square = Square(side_length=2.5, color=BLUE)\n"
    "        square.set_fill(BLUE, opacity=0.4)\n"
    "        square.move_to(ORIGIN)\n"
    "        self.play(ReplacementTransform(circle, square))\n"
    "        self.wait(1)\n\n"
    "Example 2 — 'Show Hello, move it up, fade out':\n"
    "from manim import *\n"
    "class GeneratedScene(MovingCameraScene):\n"
    "    def construct(self):\n"
    "        label = Text('Hello', font_size=72, color=YELLOW)\n"
    "        label.move_to(ORIGIN)\n"
    "        self.play(Write(label))\n"
    "        self.play(self.camera.frame.animate.move_to(label.get_center()))\n"
    "        self.wait(0.5)\n"
    "        self.play(label.animate.shift(UP * 2))\n"
    "        self.wait(0.5)\n"
    "        self.play(FadeOut(label))\n"
    "        self.wait(0.5)\n\n"
    "Example 3 — 'Animate a bouncing ball':\n"
    "from manim import *\n"
    "class GeneratedScene(MovingCameraScene):\n"
    "    def construct(self):\n"
    "        ball = Circle(radius=0.4, color=YELLOW)\n"
    "        ball.set_fill(YELLOW, opacity=1)\n"
    "        ball.move_to(LEFT * 3)\n"
    "        arc1 = ArcBetweenPoints(LEFT*3, ORIGIN, angle=-PI/3)\n"
    "        arc2 = ArcBetweenPoints(ORIGIN, RIGHT*3, angle=-PI/4)\n"
    "        self.add(ball)\n"
    "        # Center camera on the path\n"
    "        self.play(self.camera.frame.animate.move_to(ORIGIN))\n"
    "        self.play(MoveAlongPath(ball, arc1), run_time=1.5)\n"
    "        self.play(MoveAlongPath(ball, arc2), run_time=1.5)\n"
    "        self.wait(1)\n\n"
    "Example 4 — 'Draw a neural network' (FIXED: centered and visible):\n"
    "from manim import *\n"
    "class GeneratedScene(MovingCameraScene):\n"
    "    def construct(self):\n"
    "        r = 0.25\n"
    "        # Position layers centered\n"
    "        l1 = VGroup(*[Circle(radius=r,color=BLUE).move_to([-2.5,y,0]) for y in [-1,0,1]])\n"
    "        l2 = VGroup(*[Circle(radius=r,color=GREEN).move_to([0,y,0]) for y in [-1,0,1]])\n"
    "        l3 = VGroup(*[Circle(radius=r,color=RED).move_to([2.5,y,0]) for y in [-1,0,1]])\n"
    "        c12 = VGroup(*[Line(a.get_center(),b.get_center(),stroke_width=1,color=GRAY) for a in l1 for b in l2])\n"
    "        c23 = VGroup(*[Line(a.get_center(),b.get_center(),stroke_width=1,color=GRAY) for a in l2 for b in l3])\n"
    "        # Zoom out to fit entire network\n"
    "        self.play(self.camera.frame.animate.set_width(8))\n"
    "        self.play(Create(l1))\n"
    "        self.play(Create(c12))\n"
    "        self.play(Create(l2))\n"
    "        self.play(Create(c23))\n"
    "        self.play(Create(l3))\n"
    "        # Center camera on network\n"
    "        self.play(self.camera.frame.animate.move_to(ORIGIN))\n"
    "        self.wait(1)\n\n"
    "Example 5 — 'Plot y = sin(x) on axes':\n"
    "from manim import *\n"
    "import numpy as np\n"
    "class GeneratedScene(MovingCameraScene):\n"
    "    def construct(self):\n"
    "        axes = Axes(x_range=[-4,4,1], y_range=[-1.5,1.5,0.5],\n"
    "                    axis_config={'include_tip': True})\n"
    "        graph = axes.plot(lambda x: np.sin(x), color=BLUE)\n"
    "        label = Text('y = sin(x)', font_size=28, color=BLUE).to_corner(UL)\n"
    "        self.play(Create(axes))\n"
    "        self.play(Create(graph), Write(label))\n"
    "        # Center camera on the graph\n"
    "        self.play(self.camera.frame.animate.move_to(ORIGIN))\n"
    "        self.wait(2)\n\n"
    "Example 6 — 'Draw a rotating triangle' (complex shape):\n"
    "from manim import *\n"
    "class GeneratedScene(MovingCameraScene):\n"
    "    def construct(self):\n"
    "        triangle = Triangle(color=YELLOW, stroke_width=3)\n"
    "        triangle.set_fill(YELLOW, opacity=0.5)\n"
    "        triangle.move_to(ORIGIN)\n"
    "        self.play(Create(triangle))\n"
    "        self.play(self.camera.frame.animate.move_to(ORIGIN))\n"
    "        self.play(triangle.animate.rotate(PI), run_time=3)\n"
    "        self.wait(1)\n\n"
    "Example 7 — 'Animate a spiral' (parametric curve):\n"
    "from manim import *\n"
    "import numpy as np\n"
    "class GeneratedScene(MovingCameraScene):\n"
    "    def construct(self):\n"
    "        spiral = ParametricFunction(\n"
    "            lambda t: np.array([t*np.cos(t), t*np.sin(t), 0])/4,\n"
    "            t_range=[0, 4*PI],\n"
    "            color=BLUE\n"
    "        )\n"
    "        self.play(Create(spiral), run_time=3)\n"
    "        self.play(self.camera.frame.animate.move_to(ORIGIN))\n"
    "        self.wait(1)\n\n"
    "Example 8 — 'Draw a star' (complex polygon):\n"
    "from manim import *\n"
    "import numpy as np\n"
    "class GeneratedScene(MovingCameraScene):\n"
    "    def construct(self):\n"
    "        def star_points(n=5, r_outer=1.5, r_inner=0.6):\n"
    "            angles = np.linspace(0, 2*PI, n*2, endpoint=False)\n"
    "            points = []\n"
    "            for i, angle in enumerate(angles):\n"
    "                r = r_outer if i % 2 == 0 else r_inner\n"
    "                points.append(r * np.array([np.cos(angle), np.sin(angle), 0]))\n"
    "            return points\n"
    "        star = Polygon(*star_points(), color=YELLOW, stroke_width=2)\n"
    "        star.set_fill(YELLOW, opacity=0.5)\n"
    "        star.move_to(ORIGIN)\n"
    "        self.play(Create(star))\n"
    "        self.play(self.camera.frame.animate.move_to(ORIGIN))\n"
    "        self.play(star.animate.scale(1.2), run_time=2)\n"
    "        self.wait(1)\n\n"
    "Example 9 — 'Show a heart shape' (parametric):\n"
    "from manim import *\n"
    "import numpy as np\n"
    "class GeneratedScene(MovingCameraScene):\n"
    "    def construct(self):\n"
    "        heart = ParametricFunction(\n"
    "            lambda t: np.array([16*np.sin(t)**3, 13*np.cos(t)-5*np.cos(2*t)-2*np.cos(3*t)-np.cos(4*t), 0])/16,\n"
    "            t_range=[0, 2*PI],\n"
    "            color=RED\n"
    "        )\n"
    "        heart.set_fill(RED, opacity=0.5)\n"
    "        self.play(Create(heart), run_time=2)\n"
    "        self.play(self.camera.frame.animate.move_to(ORIGIN))\n"
    "        self.play(heart.animate.set_color(PINK), run_time=2)\n"
    "        self.wait(1)\n\n"
    "Example 10 — 'Draw a pendulum':\n"
    "from manim import *\n"
    "class GeneratedScene(MovingCameraScene):\n"
    "    def construct(self):\n"
    "        pivot = Dot(UP * 2.5, color=WHITE)\n"
    "        rod = Line(UP * 2.5, DOWN * 0.5, color=WHITE)\n"
    "        bob = Circle(radius=0.3).move_to(DOWN * 0.5).set_color(BLUE).set_fill(BLUE, opacity=1)\n"
    "        pendulum = VGroup(rod, bob)\n"
    "        self.add(pivot)\n"
    "        self.play(Create(pendulum), run_time=1)\n"
    "        # Center camera on pendulum\n"
    "        self.play(self.camera.frame.animate.move_to(ORIGIN))\n"
    "        self.play(Rotate(pendulum, angle=PI/6, about_point=pivot.get_center()), run_time=1)\n"
    "        self.play(Rotate(pendulum, angle=-PI/3, about_point=pivot.get_center()), run_time=1.5)\n"
    "        self.play(Rotate(pendulum, angle=PI/6, about_point=pivot.get_center()), run_time=1)\n"
    "        self.wait(1)\n\n"
    "══════════════════════════════════════════\n"
    "OUTPUT RULES\n"
    "══════════════════════════════════════════\n"
    "1. Output ONLY raw Python code — no markdown, no triple backticks, no explanation\n"
    "2. First line must be: from manim import *\n"
    "3. Class must be named exactly: GeneratedScene\n"
    "4. ALWAYS use MovingCameraScene as base class (even for simple animations)\n"
    "5. ALWAYS center camera after creating objects: self.play(self.camera.frame.animate.move_to(ORIGIN))\n"
    "6. Use self.play(self.camera.frame.animate.set_width(width)) to zoom out for wide layouts\n"
    "7. Always end with self.wait(1)\n"
    "8. Use up to 15 self.play() calls (more flexibility with camera)\n"
    "9. Every color mentioned by the user MUST appear in the code\n"
    "10. Every object mentioned by the user MUST appear in the code\n"
    "11. Steps must appear in the SAME ORDER as described by the user\n"
    "12. NEVER use ThreeDScene unless 3D rotation is explicitly requested\n"
)

# ---------------------------------------------------------------------------
# Code extraction
# ---------------------------------------------------------------------------


def _extract_code(text: str) -> str:
    """Strip markdown fences if present, return raw code."""
    if not text:
        return ""
    # Strip ```python ... ``` or ``` ... ```
    m = re.search(r"```(?:python)?\n?([\s\S]*?)```", text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return text.strip()


# ---------------------------------------------------------------------------
# Syntax validation (no subprocess needed)
# ---------------------------------------------------------------------------


def _syntax_check(code: str) -> Optional[str]:
    """
    Return None if code is syntactically valid Python, else return the error
    message. Uses the built-in ast module — no subprocess overhead.
    """
    try:
        ast.parse(code)
        return None
    except SyntaxError as e:
        return f"SyntaxError at line {e.lineno}: {e.msg}"


# ---------------------------------------------------------------------------
# Forbidden API guard
# ---------------------------------------------------------------------------

_FORBIDDEN = [
    (r"\bShowCreation\b", "ShowCreation is removed — use Create()"),
    (r"\bFadeInFrom\b", "FadeInFrom is removed — use FadeIn()"),
    (r"\bMathTex\b", "MathTex requires LaTeX which is not installed — use Text()"),
    (r"\bTex\b(?!t)", "Tex requires LaTeX which is not installed — use Text()"),
    (r"\bX_AXIS\b", "X_AXIS does not exist — use RIGHT"),
    (r"\bY_AXIS\b", "Y_AXIS does not exist — use UP"),
    (r"\bZ_AXIS\b", "Z_AXIS does not exist — use OUT"),
    (r"\bZ\b(?!\w)", "Bare 'Z' constant does not exist — use OUT"),
    (r"\babout_axis\b", "about_axis is not valid — use axis="),
]


def _check_forbidden(code: str) -> Optional[str]:
    """Return a description of the first forbidden pattern found, or None."""
    for pattern, msg in _FORBIDDEN:
        if re.search(pattern, code):
            return msg
    return None


def _check_performance(code: str) -> Optional[str]:
    """Return a warning if code contains known performance anti-patterns."""
    has_rotate = bool(re.search(r"\bRotate\s*\(", code))
    range_count = len(re.findall(r"\brange\s*\(", code))
    if has_rotate and range_count >= 2:
        return (
            "Rotate() on a large VGroup (built with range()) causes timeout. "
            "Use obj.animate.rotate() or ParametricFunction instead."
        )
    large_rts = re.findall(r"run_time\s*=\s*(\d+(?:\.\d+)?)", code)
    if any(float(rt) > 3 for rt in large_rts):
        return f"run_time values {large_rts} exceed the 3s limit per play() call."
    return None


def _validate(code: str) -> Optional[str]:
    """
    Full validation pipeline. Returns None if code passes all checks,
    or a human-readable error string describing the first failure.
    """
    if not code or len(code) < 60:
        return "Generated code is too short."

    for required in [
        "from manim import",
        "class GeneratedScene",
        "def construct",
        "self.play",
        "self.wait",
    ]:
        if required not in code:
            return f"Missing required element: '{required}'"

    syntax_err = _syntax_check(code)
    if syntax_err:
        return syntax_err

    forbidden_err = _check_forbidden(code)
    if forbidden_err:
        return forbidden_err

    perf_err = _check_performance(code)
    if perf_err:
        return perf_err

    return None


# ---------------------------------------------------------------------------
# Core AI call
# ---------------------------------------------------------------------------


def _call_llm(messages: list, max_tokens: int = 2000) -> Optional[str]:
    """Single LLM call. Returns raw text content or None on failure."""
    try:
        client = get_client()
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.1,  # Low temperature = consistent, ordered output
            max_tokens=max_tokens,
        )
        if response and response.choices:
            return response.choices[0].message.content or ""
        return None
    except Exception as e:
        logger.error(f"LLM call failed: {str(e)[:200]}")
        return None


# ---------------------------------------------------------------------------
# Stage 1: Generate code from user prompt
# ---------------------------------------------------------------------------


def _generate_initial(user_prompt: str) -> Optional[str]:
    """
    Stage 1: Generate Manim code directly from the user prompt.
    No template matching — the system prompt contains all necessary context.
    """
    ordering_note = (
        "REMINDER: Write self.play() calls in the EXACT order described. "
        "The first thing mentioned must be the first self.play() call.\n\n"
        f"Animation request: {user_prompt}"
    )
    messages = [
        {"role": "system", "content": MASTER_SYSTEM_PROMPT},
        {"role": "user", "content": ordering_note},
    ]
    raw = _call_llm(messages)
    if not raw:
        return None
    return _extract_code(raw)


# ---------------------------------------------------------------------------
# Stage 2: Self-healing — fix code given an error
# Inspired by rohitg00/manim-video-generator's error-feedback loop
# ---------------------------------------------------------------------------


def _fix_code(user_prompt: str, broken_code: str, error: str) -> Optional[str]:
    """
    Stage 2: Feed the broken code + error back to the LLM and ask it to fix it.
    This is the self-healing loop that makes the system robust.
    """
    logger.info(f"Self-healing: error = {error[:120]}")
    fix_prompt = (
        f"The following Manim code was generated for the request:\n"
        f"'{user_prompt}'\n\n"
        f"But it failed with this error:\n"
        f"{error}\n\n"
        f"Here is the broken code:\n"
        f"{broken_code}\n\n"
        f"Fix ALL errors and return ONLY the corrected Python code. "
        f"Do not change the animation logic — only fix what's broken. "
        f"Keep the same self.play() order as in the original request."
    )
    messages = [
        {"role": "system", "content": MASTER_SYSTEM_PROMPT},
        {"role": "user", "content": fix_prompt},
    ]
    raw = _call_llm(messages)
    if not raw:
        return None
    return _extract_code(raw)


# ---------------------------------------------------------------------------
# Public API: generate_code
# ---------------------------------------------------------------------------


def generate_code(
    user_prompt: str, render_error: Optional[str] = None
) -> Tuple[str, str]:
    """
    Generate Manim code from a user prompt.

    Args:
        user_prompt:  The original user request (plain English).
        render_error: If provided, this is a Manim render error from a previous
                      attempt. The LLM will attempt to fix the code rather than
                      generate from scratch. This is the self-healing entry point.

    Returns:
        Tuple of (manim_code, method) where method is 'ai' or 'fallback'.
    """
    MAX_VALIDATION_RETRIES = 3

    # ── Path A: self-healing from a render error ────────────────────────
    if render_error:
        logger.info("Entering self-healing mode with render error")
        # We need the last generated code — it's passed via render_error context
        # The caller in app.py should pass "code|||error" as render_error
        if "|||" in render_error:
            broken_code, error_msg = render_error.split("|||", 1)
        else:
            broken_code, error_msg = "", render_error

        fixed = _fix_code(user_prompt, broken_code, error_msg)
        if fixed:
            err = _validate(fixed)
            if err is None:
                logger.info("Self-healing produced valid code")
                return fixed, "ai_healed"
            logger.warning(f"Self-healed code still invalid: {err}")
        # Fall through to fresh generation if healing fails
        logger.warning("Self-healing failed, generating fresh")

    # ── Path B: fresh generation with validation retry loop ────────────
    last_code = ""
    last_error = ""

    for attempt in range(1, MAX_VALIDATION_RETRIES + 1):
        logger.info(f"Generation attempt {attempt}/{MAX_VALIDATION_RETRIES}")

        if attempt == 1:
            code = _generate_initial(user_prompt)
        else:
            # On retry, use the fix path with the validation error
            code = _fix_code(user_prompt, last_code, last_error)

        if not code:
            last_error = "LLM returned empty response."
            logger.warning(f"Attempt {attempt}: empty response")
            continue

        last_code = code
        validation_error = _validate(code)

        if validation_error is None:
            logger.info(
                f"Valid code generated on attempt {attempt} ({len(code)} chars)"
            )
            return code, "ai"

        last_error = validation_error
        logger.warning(f"Attempt {attempt} validation failed: {validation_error}")

    # ── Path C: guaranteed fallback ─────────────────────────────────────
    logger.error("All generation attempts failed, returning fallback animation")
    return _make_fallback(user_prompt), "fallback"


def _make_fallback(user_prompt: str) -> str:
    """Minimal guaranteed-to-render fallback animation."""
    import textwrap

    safe = user_prompt.replace('"', "'")[:50]
    lines = textwrap.wrap(safe, width=28)
    label = "\\n".join(lines) if lines else "Animation"
    return (
        "from manim import *\n\n"
        "class GeneratedScene(Scene):\n"
        "    def construct(self):\n"
        '        title = Text("Could not generate:", font_size=32, color=YELLOW)\n'
        f'        req = Text("{label}", font_size=28, color=WHITE)\n'
        "        group = VGroup(title, req).arrange(DOWN, buff=0.4)\n"
        "        self.play(FadeIn(group, shift=UP))\n"
        "        self.wait(2)\n"
        "        self.play(FadeOut(group))\n"
        "        self.wait(1)\n"
    )


# ---------------------------------------------------------------------------
# Legacy compatibility shim
# app.py calls generate_code_with_retries(technical_spec) — we keep that
# signature but route everything through the new pipeline.
# ---------------------------------------------------------------------------


def generate_code_with_retries(
    technical_spec: str,
    max_attempts: int = 2,
    render_error: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Backward-compatible entry point called by app.py.

    'technical_spec' is now treated as the user prompt directly —
    the prompt expander output is still accepted but no longer parsed
    for template routing.
    """
    return generate_code(technical_spec, render_error=render_error)


# ---------------------------------------------------------------------------
# validate_code_basic — kept for backward compat with app.py health checks
# ---------------------------------------------------------------------------


def validate_code_basic(code: str) -> bool:
    return _validate(code) is None
