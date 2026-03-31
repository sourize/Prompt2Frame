"""
Animation Templates - Proven Manim code patterns for common animations.

This module contains working Manim code templates for the most common
animation types. These are guaranteed to work and are visually correct.

Supports SMART TEMPLATES with parameter extraction from technical specs,
and Animation-Type-field-based routing from the prompt expander output.
"""

import re
from typing import Callable, Dict, List, Optional


# ---------------------------------------------------------------------------
# Template code strings
# ---------------------------------------------------------------------------

# Template for circle to square transformation
TEMPLATE_TRANSFORMATION = '''from manim import *

class GeneratedScene(Scene):
    def construct(self):
        # Create source shape
        circle = Circle(radius=1.0).set_color(BLUE)

        # Create target shape
        square = Square(side_length=2.0).set_color(RED)

        # Animation sequence
        self.play(Create(circle))
        self.wait(0.5)
        self.play(ReplacementTransform(circle, square))
        self.wait(1)
'''

# Template for bouncing ball
TEMPLATE_BOUNCE = '''from manim import *
import numpy as np

class GeneratedScene(Scene):
    def construct(self):
        # Create ball
        ball = Circle(radius=0.5).set_color(YELLOW).set_fill(YELLOW, opacity=1)
        ball.move_to(LEFT * 4)

        # Create bounce path (parabolic arc)
        path = ArcBetweenPoints(
            LEFT * 4,
            RIGHT * 4,
            angle=-PI/3
        )

        # Animate
        self.add(ball)
        self.play(
            MoveAlongPath(ball, path),
            run_time=3,
            rate_func=linear
        )
        self.wait(1)
'''

# Template for pendulum
TEMPLATE_PENDULUM = '''from manim import *

class GeneratedScene(Scene):
    def construct(self):
        # Create pendulum components
        pivot = Dot(UP * 2, color=WHITE)
        rod = Line(UP * 2, ORIGIN, color=WHITE)
        bob = Circle(radius=0.3).move_to(ORIGIN).set_color(BLUE).set_fill(BLUE, opacity=1)

        # Group rod and bob for rotation
        pendulum = VGroup(rod, bob)

        # Add to scene
        self.add(pivot)
        self.play(Create(pendulum), run_time=1)

        # Swing animations
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
'''

# Template for neural network
TEMPLATE_NETWORK = '''from manim import *

class GeneratedScene(Scene):
    def construct(self):
        neuron_radius = 0.25

        # Create layers
        layer1 = VGroup(*[
            Circle(radius=neuron_radius).set_color(BLUE).move_to([-3, y, 0])
            for y in [-1.5, 0, 1.5]
        ])

        layer2 = VGroup(*[
            Circle(radius=neuron_radius).set_color(GREEN).move_to([0, y, 0])
            for y in [-1.5, 0, 1.5]
        ])

        layer3 = VGroup(*[
            Circle(radius=neuron_radius).set_color(RED).move_to([3, y, 0])
            for y in [-1.5, 0, 1.5]
        ])

        # Create connections
        connections_1_2 = VGroup(*[
            Line(n1.get_center(), n2.get_center(), stroke_width=1).set_color(GRAY)
            for n1 in layer1 for n2 in layer2
        ])

        connections_2_3 = VGroup(*[
            Line(n1.get_center(), n2.get_center(), stroke_width=1).set_color(GRAY)
            for n1 in layer2 for n2 in layer3
        ])

        # Sequential animation
        self.play(Create(layer1), run_time=1)
        self.play(Create(connections_1_2), run_time=1)
        self.play(Create(layer2), run_time=1)
        self.play(Create(connections_2_3), run_time=1)
        self.play(Create(layer3), run_time=1)
        self.wait(1)
'''

# Template for growing circle
TEMPLATE_GROW = '''from manim import *

class GeneratedScene(Scene):
    def construct(self):
        circle = Circle(radius=0.5).set_color(BLUE).set_fill(BLUE, opacity=0.5)

        self.play(Create(circle))
        self.play(
            circle.animate.scale(3),
            run_time=2
        )
        self.wait(1)
'''

# Template for fading
TEMPLATE_FADE = '''from manim import *

class GeneratedScene(Scene):
    def construct(self):
        text = Text("Hello Manim!", font_size=48).set_color(YELLOW)

        self.play(Create(text))
        self.wait(0.5)
        self.play(FadeOut(text), run_time=2)
        self.wait(1)
'''

# Template for color shift
TEMPLATE_COLOR = '''from manim import *

class GeneratedScene(Scene):
    def construct(self):
        square = Square(side_length=2).set_color(BLUE)

        self.play(Create(square))
        self.play(
            square.animate.set_color(RED),
            run_time=2
        )
        self.play(
            square.animate.set_color(GREEN),
            run_time=2
        )
        self.wait(1)
'''

# Template for text sequence
TEMPLATE_TEXT = '''from manim import *

class GeneratedScene(Scene):
    def construct(self):
        title = Text("Animation Title", font_size=48)
        subtitle = Text("A subtitle here", font_size=32).next_to(title, DOWN)

        self.play(Create(title))
        self.wait(0.5)
        self.play(Create(subtitle))
        self.wait(1)

        group = VGroup(title, subtitle)
        self.play(group.animate.shift(UP * 2))
        self.wait(1)
'''

# Template for function plot (smart — customised from technical spec)
def TEMPLATE_PLOT_SMART(technical_spec: str) -> str:
    """Smart plot template that extracts parameters and customises."""
    from .template_helpers import extract_parameters, generate_plot_points_code

    params = extract_parameters(technical_spec)

    # If coordinates are specified, use custom point plot
    if params['coordinates']:
        return generate_plot_points_code(params['coordinates'], params['colors'])

    # Otherwise use default parabola plot
    return '''from manim import *

class GeneratedScene(Scene):
    def construct(self):
        axes = Axes(
            x_range=[-3, 3, 1],
            y_range=[-2, 2, 1],
            axis_config={"include_tip": True}
        )

        # Add labels
        x_label = Text("x", font_size=24).next_to(axes.x_axis.get_end(), RIGHT)
        y_label = Text("y", font_size=24).next_to(axes.y_axis.get_end(), UP)

        # Create function graph
        graph = axes.plot(lambda x: x**2 / 3, color=BLUE)
        graph_label = Text("f(x) = x^2", font_size=28, color=BLUE).to_corner(UL)

        # Animate
        self.play(Create(axes), Create(x_label), Create(y_label))
        self.play(Create(graph), Create(graph_label))
        self.wait(2)
'''

# Template for rotating 3D cube
TEMPLATE_3D_ROTATE = '''from manim import *

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
'''

# Fallback template for unknown requests
TEMPLATE_FALLBACK = '''from manim import *

class GeneratedScene(Scene):
    def construct(self):
        # Fallback: Simple circle with text
        circle = Circle(radius=1.0).set_color(BLUE)
        text = Text("Animation", font_size=36).next_to(circle, UP)

        self.play(Create(circle), Create(text))
        self.play(
            circle.animate.scale(1.5),
            run_time=2
        )
        self.wait(1)
'''


# ---------------------------------------------------------------------------
# Template registry
# ---------------------------------------------------------------------------

TEMPLATE_REGISTRY: Dict[str, Dict] = {
    'transformation': {
        # Fix #5/#6: Use precise, multi-word phrases and word-boundary patterns
        # to avoid false positives. "transform" is still single-word but it is
        # specific enough that false matches are rare and acceptable.
        'keywords': ['transform', 'morph', 'become', 'circle to square', 'square to circle'],
        'animation_types': ['transformation'],
        'code': TEMPLATE_TRANSFORMATION,
        'description': 'Shape transformation (e.g., circle to square)'
    },
    'bounce': {
        # Fix #5: Removed bare "ball" — it matched "basketball", "baseball" etc.
        # Kept compound phrases that clearly indicate the bouncing ball animation.
        'keywords': ['bouncing ball', 'ball bounce', 'ball bouncing', 'bounce animation'],
        'animation_types': ['motion along path', 'bouncing'],
        'code': TEMPLATE_BOUNCE,
        'description': 'Bouncing ball along arc path'
    },
    'pendulum': {
        'keywords': ['pendulum', 'swing', 'oscillate'],
        'animation_types': ['rotation about pivot', 'pendulum'],
        'code': TEMPLATE_PENDULUM,
        'description': 'Swinging pendulum with rotation'
    },
    'network': {
        'keywords': ['neural network', 'network layers', 'deep learning'],
        'animation_types': ['network structure', 'neural network'],
        'code': TEMPLATE_NETWORK,
        'description': 'Multi-layer network with connections'
    },
    'grow': {
        'keywords': ['grow', 'growing', 'expand', 'scale up'],
        'animation_types': ['growth', 'scaling'],
        'code': TEMPLATE_GROW,
        'description': 'Growing/scaling animation'
    },
    'fade': {
        'keywords': ['fade out', 'fade in', 'fading', 'disappear'],
        'animation_types': ['fade', 'fading'],
        'code': TEMPLATE_FADE,
        'description': 'Fading in/out animation'
    },
    'color': {
        'keywords': ['color shift', 'change color', 'color transition', 'colour shift'],
        'animation_types': ['color transition', 'colour transition'],
        'code': TEMPLATE_COLOR,
        'description': 'Color transition animation'
    },
    'text': {
        'keywords': ['write text', 'show text', 'display title', 'text animation'],
        'animation_types': ['text', 'writing', 'title'],
        'code': TEMPLATE_TEXT,
        'description': 'Text writing and positioning'
    },
    'plot': {
        'keywords': ['plot points', 'coordinate plot', 'axes plot', 'function graph', 'function plot'],
        'animation_types': ['plot', 'graph', 'coordinate', 'mathematical function'],
        'code': None,          # Uses smart function below
        'smart_function': TEMPLATE_PLOT_SMART,
        'description': 'Mathematical function plot or point plotting'
    },
    '3d_rotate': {
        'keywords': ['3d cube', 'rotating cube', '3d rotation', 'three dimensional'],
        'animation_types': ['3d', 'three-dimensional', 'rotating 3d'],
        'code': TEMPLATE_3D_ROTATE,
        'description': '3D object rotation'
    },
}


# ---------------------------------------------------------------------------
# Fix #7: Animation-Type-field routing
# ---------------------------------------------------------------------------

def _route_by_animation_type(technical_spec: str) -> Optional[str]:
    """
    Fix #7: The prompt expander always outputs an 'Animation Type:' line.
    Parse it and map directly to a template *before* keyword matching.

    This is zero-cost (no extra LLM call) and much more reliable than
    bag-of-words keyword search.

    Returns the template name (key in TEMPLATE_REGISTRY) or None if
    the declared type cannot be mapped to a known template.
    """
    match = re.search(r'Animation Type:\s*(.+)', technical_spec, re.IGNORECASE)
    if not match:
        return None

    declared_type = match.group(1).strip().lower()

    for template_name, template_info in TEMPLATE_REGISTRY.items():
        for anim_type in template_info.get('animation_types', []):
            if anim_type.lower() in declared_type or declared_type in anim_type.lower():
                return template_name

    return None


# ---------------------------------------------------------------------------
# Fix #6: Word-boundary keyword matcher
# ---------------------------------------------------------------------------

def _count_keyword_matches(template_keywords: List[str], spec_lower: str) -> int:
    """
    Count how many of the given keywords appear in spec_lower using whole-word
    (or whole-phrase) matching.

    Fix #6: Previously used raw `keyword in spec_lower` which matches substrings.
    e.g. "basketball" matched keyword "ball" and sent the user a bouncing-ball
    animation instead of something basketball-related.

    We now wrap each keyword in \\b word-boundary assertions so that single
    words must appear as complete words, while multi-word phrases (e.g.
    "bouncing ball") still match naturally.
    """
    count = 0
    for keyword in template_keywords:
        # Build a word-boundary-aware pattern.
        # re.escape handles special chars in multi-word phrases safely.
        pattern = r'\b' + re.escape(keyword) + r'\b'
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
    1. Animation Type field (structured, from prompt_expander) — Fix #7
    2. Keyword bag-of-words with word boundaries — Fix #5 / #6
    3. Return None if no confident match (≥2 keyword hits required)

    Returns:
        Manim code string, or None when no confident match was found.
        Callers should fall through to AI generation on None.
    """
    spec_lower = technical_spec.lower()

    # --- Priority 1: Animation Type field ---
    matched_name = _route_by_animation_type(technical_spec)
    if matched_name:
        template_info = TEMPLATE_REGISTRY[matched_name]
        smart_fn = template_info.get('smart_function')
        if smart_fn:
            return smart_fn(technical_spec)
        code = template_info.get('code')
        if code:
            return code

    # --- Priority 2: Keyword matching (word-boundary safe) ---
    best_match_code: Optional[str] = None
    best_match_smart_fn: Optional[Callable] = None
    max_matches = 0

    for template_name, template_info in TEMPLATE_REGISTRY.items():
        hits = _count_keyword_matches(template_info['keywords'], spec_lower)
        if hits > max_matches:
            max_matches = hits
            best_match_code = template_info.get('code')
            best_match_smart_fn = template_info.get('smart_function')

    # Require at least 2 keyword matches to avoid spurious single-word matches
    # (e.g. a prompt mentioning "grow" incidentally should not force TEMPLATE_GROW)
    MIN_CONFIDENCE = 2
    if max_matches >= MIN_CONFIDENCE:
        if best_match_smart_fn:
            return best_match_smart_fn(technical_spec)
        if best_match_code:
            return best_match_code

    # No confident match — signal caller to try AI generation
    return None


def get_template_by_name(name: str) -> str:
    """
    Get a specific template by name.

    Fix #8: Previously returned None for 'plot' because its 'code' field is
    None (it uses a smart function). Now calls the smart function with an empty
    spec (yielding the default parabola) or returns TEMPLATE_FALLBACK as a
    last resort.
    """
    if name not in TEMPLATE_REGISTRY:
        return TEMPLATE_FALLBACK

    template_info = TEMPLATE_REGISTRY[name]

    # Handle smart-function templates (like 'plot')
    smart_fn = template_info.get('smart_function')
    if smart_fn:
        return smart_fn("")

    code = template_info.get('code')
    return code if code else TEMPLATE_FALLBACK


def list_available_templates() -> List[Dict[str, str]]:
    """List all available templates with their descriptions."""
    return [
        {
            'name': name,
            'description': info['description'],
            'keywords': ', '.join(info['keywords'][:3])  # Show first 3 keywords
        }
        for name, info in TEMPLATE_REGISTRY.items()
    ]
