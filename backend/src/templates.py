"""
Animation Templates - Proven Manim code patterns for common animations.

This module contains working Manim code templates for the most common
animation types. These are guaranteed to work and are visually correct.
"""

from typing import Callable, Dict, List


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
        
        self.play(Write(text))
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
        
        self.play(Write(title))
        self.wait(0.5)
        self.play(Write(subtitle))
        self.wait(1)
        
        group = VGroup(title, subtitle)
        self.play(group.animate.shift(UP * 2))
        self.wait(1)
'''

# Template for function plot
TEMPLATE_PLOT = '''from manim import *

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
        graph_label = Text("f(x) = x²", font_size=28, color=BLUE).to_corner(UL)
        
        # Animate
        self.play(Create(axes), Write(x_label), Write(y_label))
        self.play(Create(graph), Write(graph_label))
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
        
        self.play(Create(circle), Write(text))
        self.play(
            circle.animate.scale(1.5),
            run_time=2
        )
        self.wait(1)
'''


# Template registry with keywords for matching
TEMPLATE_REGISTRY: Dict[str, Dict] = {
    'transformation': {
        'keywords': ['transform', 'morph', 'change', 'become', 'circle to square', 'square to circle'],
        'code': TEMPLATE_TRANSFORMATION,
        'description': 'Shape transformation (e.g., circle to square)'
    },
    'bounce': {
        'keywords': ['bounce', 'bouncing', 'ball'],
        'code': TEMPLATE_BOUNCE,
        'description': 'Bouncing ball along arc path'
    },
    'pendulum': {
        'keywords': ['pendulum', 'swing', 'oscillate'],
        'code': TEMPLATE_PENDULUM,
        'description': 'Swinging pendulum with rotation'
    },
    'network': {
        'keywords': ['network', 'neural', 'graph', 'nodes', 'layers'],
        'code': TEMPLATE_NETWORK,
        'description': 'Multi-layer network with connections'
    },
    'grow': {
        'keywords': ['grow', 'growing', 'expand', 'scale'],
        'code': TEMPLATE_GROW,
        'description': 'Growing/scaling animation'
    },
    'fade': {
        'keywords': ['fade', 'fading', 'disappear'],
        'code': TEMPLATE_FADE,
        'description': 'Fading in/out animation'
    },
    'color': {
        'keywords': ['color', 'shift', 'change color'],
        'code': TEMPLATE_COLOR,
        'description': 'Color transition animation'
    },
    'text': {
        'keywords': ['text', 'write', 'title'],
        'code': TEMPLATE_TEXT,
        'description': 'Text writing and positioning'
    },
    'plot': {
        'keywords': ['plot', 'graph', 'function', 'axes', 'curve'],
        'code': TEMPLATE_PLOT,
        'description': 'Mathematical function plot'
    },
    '3d_rotate': {
        'keywords': ['3d', 'rotate', 'cube', 'rotating'],
        'code': TEMPLATE_3D_ROTATE,
        'description': '3D object rotation'
    }
}


def match_template(technical_spec: str) -> str:
    """
    Find the best matching template based on keywords in the technical specification.
    
    Args:
        technical_spec: Plain text technical specification from prompt_expander
        
    Returns:
        Manim code from best matching template, or fallback template
    """
    spec_lower = technical_spec.lower()
    
    # Count keyword matches for each template
    best_match = None
    max_matches = 0
    
    for template_name, template_info in TEMPLATE_REGISTRY.items():
        matches = sum(1 for keyword in template_info['keywords'] if keyword in spec_lower)
        if matches > max_matches:
            max_matches = matches
            best_match = template_info['code']
    
    # Return best match or fallback
    if best_match and max_matches > 0:
        return best_match

    return TEMPLATE_FALLBACK


def get_template_by_name(name: str) -> str:
    """Get a specific template by name."""
    if name in TEMPLATE_REGISTRY:
        return TEMPLATE_REGISTRY[name]['code']
    return TEMPLATE_FALLBACK


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
