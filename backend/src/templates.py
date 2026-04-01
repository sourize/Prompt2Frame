"""
Animation Templates - Proven Manim code patterns for common animations.

Supports SMART TEMPLATES with parameter extraction from technical specs,
and Animation-Type-field-based routing from the prompt expander output.
"""

import re
from typing import Callable, Dict, List, Optional


# ---------------------------------------------------------------------------
# Static template strings
# ---------------------------------------------------------------------------

TEMPLATE_BOUNCE = """from manim import *
import numpy as np

class GeneratedScene(Scene):
    def construct(self):
        ball = Circle(radius=0.5).set_color(YELLOW).set_fill(YELLOW, opacity=1)
        ball.move_to(LEFT * 4)

        path = ArcBetweenPoints(
            LEFT * 4,
            RIGHT * 4,
            angle=-PI/3
        )

        self.add(ball)
        self.play(
            MoveAlongPath(ball, path),
            run_time=3,
            rate_func=linear
        )
        self.wait(1)
"""

TEMPLATE_PENDULUM = """from manim import *

class GeneratedScene(MovingCameraScene):
    def construct(self):
        pivot = Dot(UP * 2.5, color=WHITE)
        rod = Line(UP * 2.5, DOWN * 0.5, color=WHITE)
        bob = Circle(radius=0.3).move_to(DOWN * 0.5).set_color(BLUE).set_fill(BLUE, opacity=1)

        pendulum = VGroup(rod, bob)
        pendulum.move_to(ORIGIN)

        self.add(pivot)
        self.play(Create(pendulum), run_time=1)
        self.play(self.camera.frame.animate.move_to(ORIGIN))

        self.play(
            Rotate(pendulum, angle=PI/6, about_point=pivot.get_center()),
            run_time=1
        )
        self.play(
            Rotate(pendulum, angle=-PI/3, about_point=pivot.get_center()),
            run_time=1.5
        )
        self.play(
            Rotate(pendulum, angle=PI/6, about_point=pivot.get_center()),
            run_time=1
        )
        self.wait(1)
"""

TEMPLATE_NETWORK = """from manim import *

class GeneratedScene(MovingCameraScene):
    def construct(self):
        neuron_radius = 0.25

        # Position layers within visible range, centered
        layer1 = VGroup(*[
            Circle(radius=neuron_radius).set_color(BLUE).move_to([-2, y, 0])
            for y in [-0.8, 0, 0.8]
        ])
        layer2 = VGroup(*[
            Circle(radius=neuron_radius).set_color(GREEN).move_to([0, y, 0])
            for y in [-0.8, 0, 0.8]
        ])
        layer3 = VGroup(*[
            Circle(radius=neuron_radius).set_color(RED).move_to([2, y, 0])
            for y in [-0.8, 0, 0.8]
        ])

        connections_1_2 = VGroup(*[
            Line(n1.get_center(), n2.get_center(), stroke_width=1).set_color(GRAY)
            for n1 in layer1 for n2 in layer2
        ])
        connections_2_3 = VGroup(*[
            Line(n1.get_center(), n2.get_center(), stroke_width=1).set_color(GRAY)
            for n1 in layer2 for n2 in layer3
        ])

        # Zoom out to fit entire network
        self.play(self.camera.frame.animate.set_width(7))
        self.play(Create(layer1), run_time=1)
        self.play(Create(connections_1_2), run_time=1)
        self.play(Create(layer2), run_time=1)
        self.play(Create(connections_2_3), run_time=1)
        self.play(Create(layer3), run_time=1)
        # Center camera on network
        self.play(self.camera.frame.animate.move_to(ORIGIN))
        self.wait(1)
"""

TEMPLATE_GROW = """from manim import *

class GeneratedScene(MovingCameraScene):
    def construct(self):
        circle = Circle(radius=0.5).set_color(BLUE).set_fill(BLUE, opacity=0.5)
        circle.move_to(ORIGIN)

        self.play(Create(circle))
        self.play(self.camera.frame.animate.move_to(ORIGIN))
        self.play(circle.animate.scale(3), run_time=2)
        self.wait(1)
"""

TEMPLATE_FADE = """from manim import *

class GeneratedScene(MovingCameraScene):
    def construct(self):
        text = Text("Hello Manim!", font_size=48).set_color(YELLOW)
        text.move_to(ORIGIN)

        self.play(Write(text))
        self.play(self.camera.frame.animate.move_to(ORIGIN))
        self.wait(0.5)
        self.play(FadeOut(text), run_time=2)
        self.wait(1)
"""

TEMPLATE_COLOR = """from manim import *

class GeneratedScene(MovingCameraScene):
    def construct(self):
        square = Square(side_length=2).set_color(BLUE)
        square.move_to(ORIGIN)

        self.play(Create(square))
        self.play(self.camera.frame.animate.move_to(ORIGIN))
        self.play(square.animate.set_color(RED), run_time=2)
        self.play(square.animate.set_color(GREEN), run_time=2)
        self.wait(1)
"""

TEMPLATE_TEXT = """from manim import *

class GeneratedScene(MovingCameraScene):
    def construct(self):
        title = Text("Animation Title", font_size=48)
        subtitle = Text("A subtitle here", font_size=32).next_to(title, DOWN)
        title.move_to(ORIGIN)

        self.play(Write(title))
        self.play(self.camera.frame.animate.move_to(ORIGIN))
        self.wait(0.5)
        self.play(Write(subtitle))
        self.wait(1)

        group = VGroup(title, subtitle)
        self.play(group.animate.shift(UP * 2))
        self.wait(1)
"""

TEMPLATE_3D_ROTATE = """from manim import *

class GeneratedScene(ThreeDScene):
    def construct(self):
        self.set_camera_orientation(phi=75 * DEGREES, theta=30 * DEGREES)

        cube = Cube(side_length=2, fill_opacity=0.7, stroke_width=2)
        cube.set_color(BLUE)

        self.play(Create(cube))
        self.begin_ambient_camera_rotation(rate=0.3)
        self.wait(5)
        self.stop_ambient_camera_rotation()
        self.wait(1)
"""

TEMPLATE_SPIRAL = """from manim import *
import numpy as np

class GeneratedScene(MovingCameraScene):
    def construct(self):
        spiral = ParametricFunction(
            lambda t: np.array([t*np.cos(t), t*np.sin(t), 0])/5,
            t_range=[0, 4*PI],
            color=BLUE
        )
        self.play(Create(spiral), run_time=3)
        self.play(self.camera.frame.animate.move_to(ORIGIN))
        self.wait(1)
"""

TEMPLATE_STAR = """from manim import *
import numpy as np

class GeneratedScene(MovingCameraScene):
    def construct(self):
        def star_points(n=5, r_outer=1.5, r_inner=0.6):
            angles = np.linspace(0, 2*np.pi, n*2, endpoint=False)
            points = []
            for i, angle in enumerate(angles):
                r = r_outer if i % 2 == 0 else r_inner
                points.append(r * np.array([np.cos(angle), np.sin(angle), 0]))
            return points
        star = Polygon(*star_points(), color=YELLOW, stroke_width=2)
        star.set_fill(YELLOW, opacity=0.5)
        star.move_to(ORIGIN)
        self.play(Create(star))
        self.play(self.camera.frame.animate.move_to(ORIGIN))
        self.play(star.animate.scale(1.2), run_time=2)
        self.wait(1)
"""

TEMPLATE_HEART = """from manim import *
import numpy as np

class GeneratedScene(MovingCameraScene):
    def construct(self):
        heart = ParametricFunction(
            lambda t: np.array([16*np.sin(t)**3, 13*np.cos(t)-5*np.cos(2*t)-2*np.cos(3*t)-np.cos(4*t), 0])/16,
            t_range=[0, 2*np.pi],
            color=RED
        )
        heart.set_fill(RED, opacity=0.5)
        self.play(Create(heart), run_time=2)
        self.play(self.camera.frame.animate.move_to(ORIGIN))
        self.play(heart.animate.set_color(PINK), run_time=2)
        self.wait(1)
"""

TEMPLATE_HEXAGON = """from manim import *
import numpy as np

class GeneratedScene(MovingCameraScene):
    def construct(self):
        def hexagon(center, size=0.5):
            angles = np.linspace(0, 2*np.pi, 7)[:-1]
            points = [center + size * np.array([np.cos(a), np.sin(a), 0]) for a in angles]
            return Polygon(*points, color=BLUE)
        
        hexagons = VGroup(*[
            hexagon(np.array([i*0.9, j*0.78, 0]))
            for i in range(-2, 3)
            for j in range(-2, 3)
        ])
        self.play(self.camera.frame.animate.set_width(6))
        self.play(Create(hexagons), run_time=2)
        self.play(self.camera.frame.animate.move_to(ORIGIN))
        self.wait(1)
"""

TEMPLATE_FALLBACK = """from manim import *

class GeneratedScene(MovingCameraScene):
    def construct(self):
        circle = Circle(radius=1.0).set_color(BLUE)
        circle.move_to(ORIGIN)
        self.play(Create(circle))
        self.play(self.camera.frame.animate.move_to(ORIGIN))
        self.play(circle.animate.scale(1.5), run_time=2)
        self.wait(1)
"""


# ---------------------------------------------------------------------------
# Smart template functions
# ---------------------------------------------------------------------------


def TEMPLATE_TRANSFORMATION_SMART(technical_spec: str) -> str:
    """
    Smart transformation template that extracts source/target shapes and
    colors from the technical spec rather than using hardcoded values.

    This replaces the old hardcoded TEMPLATE_TRANSFORMATION which always
    produced a BLUE circle -> RED square regardless of what the user asked.
    """
    from .template_helpers import extract_colors

    spec_lower = technical_spec.lower()
    colors = extract_colors(technical_spec)

    # --- Determine source shape ---
    if "circle" in spec_lower:
        source_color = colors[0] if colors else "BLUE"
        source_code = (
            f"        source = Circle(radius=1.5, color={source_color})\n"
            f"        source.set_fill({source_color}, opacity=0.5)"
        )
    elif "triangle" in spec_lower:
        source_color = colors[0] if colors else "BLUE"
        source_code = (
            f"        source = Triangle(color={source_color})\n"
            f"        source.set_fill({source_color}, opacity=0.5)"
        )
    else:
        source_color = colors[0] if colors else "BLUE"
        source_code = (
            f"        source = Circle(radius=1.5, color={source_color})\n"
            f"        source.set_fill({source_color}, opacity=0.5)"
        )

    # --- Determine target shape ---
    if "square" in spec_lower:
        target_color = colors[1] if len(colors) > 1 else "RED"
        target_code = (
            f"        target = Square(side_length=2.5, color={target_color})\n"
            f"        target.set_fill({target_color}, opacity=0.5)"
        )
    elif "triangle" in spec_lower and "circle" in spec_lower:
        target_color = colors[1] if len(colors) > 1 else "RED"
        target_code = (
            f"        target = Triangle(color={target_color})\n"
            f"        target.set_fill({target_color}, opacity=0.5)"
        )
    elif "circle" in spec_lower and "square" not in spec_lower:
        target_color = colors[1] if len(colors) > 1 else "GREEN"
        target_code = (
            f"        target = Square(side_length=2.5, color={target_color})\n"
            f"        target.set_fill({target_color}, opacity=0.5)"
        )
    else:
        target_color = colors[1] if len(colors) > 1 else "RED"
        target_code = (
            f"        target = Square(side_length=2.5, color={target_color})\n"
            f"        target.set_fill({target_color}, opacity=0.5)"
        )

    return (
        "from manim import *\n\n"
        "class GeneratedScene(MovingCameraScene):\n"
        "    def construct(self):\n"
        f"{source_code}\n"
        f"        source.move_to(ORIGIN)\n\n"
        f"{target_code}\n"
        f"        target.move_to(ORIGIN)\n\n"
        "        # Step 1: draw source shape\n"
        "        self.play(Create(source))\n"
        "        self.play(self.camera.frame.animate.move_to(ORIGIN))\n"
        "        self.wait(0.5)\n\n"
        "        # Step 2: transform into target shape\n"
        "        self.play(ReplacementTransform(source, target))\n"
        "        self.wait(1)\n"
    )


def TEMPLATE_PLOT_SMART(technical_spec: str) -> str:
    """Smart plot template that extracts parameters and customises."""
    from .template_helpers import extract_parameters, generate_plot_points_code

    params = extract_parameters(technical_spec)

    if params["coordinates"]:
        return generate_plot_points_code(params["coordinates"], params["colors"])

    return """from manim import *

class GeneratedScene(MovingCameraScene):
    def construct(self):
        axes = Axes(
            x_range=[-3, 3, 1],
            y_range=[-2, 2, 1],
            axis_config={"include_tip": True}
        )

        x_label = Text("x", font_size=24).next_to(axes.x_axis.get_end(), RIGHT)
        y_label = Text("y", font_size=24).next_to(axes.y_axis.get_end(), UP)

        graph = axes.plot(lambda x: x**2 / 3, color=BLUE)
        graph_label = Text("f(x) = x^2", font_size=28, color=BLUE).to_corner(UL)

        self.play(Create(axes), Write(x_label), Write(y_label))
        self.play(Create(graph), Write(graph_label))
        self.play(self.camera.frame.animate.move_to(ORIGIN))
        self.wait(2)
"""


# ---------------------------------------------------------------------------
# Template registry
# ---------------------------------------------------------------------------

TEMPLATE_REGISTRY: Dict[str, Dict] = {
    "transformation": {
        # NOTE: 'transformation' is intentionally NOT in animation_types routing.
        # It is too generic — the AI handles it better with color/shape extraction.
        # The smart function below is used for keyword matches only.
        "keywords": [
            "circle to square",
            "square to circle",
            "morph",
            "become",
            "circle into square",
            "square into circle",
            "shape morph",
        ],
        "animation_types": [],  # Empty — do NOT route via Animation Type field
        "code": None,
        "smart_function": TEMPLATE_TRANSFORMATION_SMART,
        "description": "Shape transformation (e.g., circle to square)",
    },
    "bounce": {
        "keywords": [
            "bouncing ball",
            "ball bounce",
            "ball bouncing",
            "bounce animation",
        ],
        "animation_types": ["motion along path", "bouncing"],
        "code": TEMPLATE_BOUNCE,
        "description": "Bouncing ball along arc path",
    },
    "pendulum": {
        "keywords": ["pendulum", "swing", "oscillate"],
        "animation_types": ["rotation about pivot", "pendulum"],
        "code": TEMPLATE_PENDULUM,
        "description": "Swinging pendulum with rotation",
    },
    "network": {
        "keywords": ["neural network", "network layers", "deep learning"],
        "animation_types": ["network structure", "neural network"],
        "code": TEMPLATE_NETWORK,
        "description": "Multi-layer network with connections",
    },
    "grow": {
        "keywords": ["grow", "growing", "expand", "scale up"],
        "animation_types": ["growth", "scaling"],
        "code": TEMPLATE_GROW,
        "description": "Growing/scaling animation",
    },
    "fade": {
        "keywords": ["fade out", "fade in", "fading", "disappear"],
        "animation_types": ["fade", "fading"],
        "code": TEMPLATE_FADE,
        "description": "Fading in/out animation",
    },
    "color": {
        "keywords": ["color shift", "change color", "color transition", "colour shift"],
        "animation_types": ["color transition", "colour transition"],
        "code": TEMPLATE_COLOR,
        "description": "Color transition animation",
    },
    "text": {
        "keywords": ["write text", "show text", "display title", "text animation"],
        "animation_types": ["text", "writing", "title"],
        "code": TEMPLATE_TEXT,
        "description": "Text writing and positioning",
    },
    "plot": {
        "keywords": [
            "plot points",
            "coordinate plot",
            "axes plot",
            "function graph",
            "function plot",
        ],
        "animation_types": ["plot", "graph", "coordinate", "mathematical function"],
        "code": None,
        "smart_function": TEMPLATE_PLOT_SMART,
        "description": "Mathematical function plot or point plotting",
    },
    "3d_rotate": {
        "keywords": ["3d cube", "rotating cube", "3d rotation", "three dimensional"],
        "animation_types": ["3d", "three-dimensional", "rotating 3d"],
        "code": TEMPLATE_3D_ROTATE,
        "description": "3D object rotation",
    },
    "spiral": {
        "keywords": ["spiral", "helix", "curl", "swirl", "spiral animation"],
        "animation_types": ["parametric curve", "spiral", "curved path"],
        "code": TEMPLATE_SPIRAL,
        "description": "Spiral/parametric curve animation",
    },
    "star": {
        "keywords": ["star", "stars", "5-point star", "polygon star", "star shape"],
        "animation_types": ["star shape", "polygon animation"],
        "code": TEMPLATE_STAR,
        "description": "Star shape animation",
    },
    "heart": {
        "keywords": ["heart", "love", "heart shape", "heartbeat", "pulsing heart"],
        "animation_types": ["heart shape", "heart animation", "pulse"],
        "code": TEMPLATE_HEART,
        "description": "Heart shape with pulsing animation",
    },
    "hexagon": {
        "keywords": ["hexagon", "hexagonal", "honeycomb", "grid of hexagons"],
        "animation_types": ["hexagonal grid", "pattern", "geometric pattern"],
        "code": TEMPLATE_HEXAGON,
        "description": "Hexagonal grid pattern",
    },
}


# ---------------------------------------------------------------------------
# Animation Type field routing
# ---------------------------------------------------------------------------


def _route_by_animation_type(technical_spec: str) -> Optional[str]:
    """
    Parse the 'Animation Type:' line from the expander and map it to a template.

    IMPORTANT: Templates with empty animation_types lists are intentionally
    excluded from this routing — they require AI or smart extraction to handle
    correctly (e.g. 'transformation' needs color/shape extraction from the spec).
    """
    match = re.search(r"Animation Type:\s*(.+)", technical_spec, re.IGNORECASE)
    if not match:
        return None

    declared_type = match.group(1).strip().lower()

    for template_name, template_info in TEMPLATE_REGISTRY.items():
        anim_types = template_info.get("animation_types", [])
        if not anim_types:
            continue  # Skip templates that opted out of Animation Type routing
        for anim_type in anim_types:
            if anim_type.lower() in declared_type or declared_type in anim_type.lower():
                return template_name

    return None


# ---------------------------------------------------------------------------
# Word-boundary keyword matcher
# ---------------------------------------------------------------------------


def _count_keyword_matches(template_keywords: List[str], spec_lower: str) -> int:
    """
    Count keyword matches using whole-word boundary assertions to avoid
    false positives (e.g. "ball" matching "basketball").
    """
    count = 0
    for keyword in template_keywords:
        pattern = r"\b" + re.escape(keyword) + r"\b"
        if re.search(pattern, spec_lower):
            count += 1
    return count


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def match_template(technical_spec: str) -> Optional[str]:
    """
    Find the best matching template based on the technical specification.

    Routing priority:
    1. Animation Type field (only for templates that opted in)
    2. Keyword matching with word boundaries (requires >= 2 hits)
    3. Return None → caller falls through to AI generation

    Returns:
        Manim code string, or None when no confident match was found.
    """
    spec_lower = technical_spec.lower()

    # --- Priority 1: Animation Type field routing ---
    matched_name = _route_by_animation_type(technical_spec)
    if matched_name:
        template_info = TEMPLATE_REGISTRY[matched_name]
        smart_fn = template_info.get("smart_function")
        if smart_fn:
            return smart_fn(technical_spec)
        code = template_info.get("code")
        if code:
            return code

    # --- Priority 2: Keyword matching ---
    best_match_code: Optional[str] = None
    best_match_smart_fn: Optional[Callable] = None
    max_matches = 0

    for template_name, template_info in TEMPLATE_REGISTRY.items():
        hits = _count_keyword_matches(template_info["keywords"], spec_lower)
        if hits > max_matches:
            max_matches = hits
            best_match_code = template_info.get("code")
            best_match_smart_fn = template_info.get("smart_function")

    MIN_CONFIDENCE = 2
    if max_matches >= MIN_CONFIDENCE:
        if best_match_smart_fn:
            return best_match_smart_fn(technical_spec)
        if best_match_code:
            return best_match_code

    # No confident match — let AI handle it
    return None


def get_template_by_name(name: str) -> str:
    """Get a specific template by name."""
    if name not in TEMPLATE_REGISTRY:
        return TEMPLATE_FALLBACK

    template_info = TEMPLATE_REGISTRY[name]
    smart_fn = template_info.get("smart_function")
    if smart_fn:
        return smart_fn("")

    code = template_info.get("code")
    return code if code else TEMPLATE_FALLBACK


def list_available_templates() -> List[Dict[str, str]]:
    """List all available templates with their descriptions."""
    return [
        {
            "name": name,
            "description": info["description"],
            "keywords": ", ".join(info["keywords"][:3]),
        }
        for name, info in TEMPLATE_REGISTRY.items()
    ]
