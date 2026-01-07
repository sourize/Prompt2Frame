"""
Template Parameter Extraction - Extract parameters from technical specifications.

This module parses plain text technical specs to extract useful parameters
like coordinates, colors, numbers, etc. that can be used to customize templates.
"""

import re
from typing import Dict, List, Tuple, Optional


def extract_coordinates(text: str) -> List[Tuple[float, float]]:
    """
    Extract coordinate pairs from text.
    
    Matches patterns like: (0,2), (2,0), (4,2) or [0,2] or x=3, y=4
    
    Args:
        text: Text containing coordinates
        
    Returns:
        List of (x, y) tuples
    """
    coordinates = []
    
    # Pattern 1: (x,y) or [x,y]
    pattern1 = r'[\(\[](-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)[\)\]]'
    for match in re.finditer(pattern1, text):
        x, y = float(match.group(1)), float(match.group(2))
        coordinates.append((x, y))
    
    # Pattern 2: x=3, y=4 or x: 3, y: 4
    pattern2 = r'x\s*[:=]\s*(-?\d+\.?\d*)\s*,?\s*y\s*[:=]\s*(-?\d+\.?\d*)'
    for match in re.finditer(pattern2, text, re.IGNORECASE):
        x, y = float(match.group(1)), float(match.group(2))
        coordinates.append((x, y))
    
    return coordinates


def extract_numbers(text: str) -> List[float]:
    """
    Extract all numbers from text.
    
    Args:
        text: Text containing numbers
        
    Returns:
        List of numbers found
    """
    pattern = r'-?\d+\.?\d*'
    return [float(m.group()) for m in re.finditer(pattern, text)]


def extract_colors(text: str) -> List[str]:
    """
    Extract color names from text.
    
    Args:
        text: Text containing color names
        
    Returns:
        List of Manim color constants
    """
    # Common colors mentioned in text -> Manim constants
    color_map = {
        'red': 'RED',
        'blue': 'BLUE', 
        'green': 'GREEN',
        'yellow': 'YELLOW',
        'orange': 'ORANGE',
        'purple': 'PURPLE',
        'pink': 'PINK',
        'white': 'WHITE',
        'black': 'BLACK',
        'gray': 'GRAY',
        'grey': 'GRAY',
        'cyan': 'TEAL',
        'magenta': 'PINK'
    }
    
    colors = []
    text_lower = text.lower()
    for color_name, manim_color in color_map.items():
        if color_name in text_lower:
            colors.append(manim_color)
    
    return colors if colors else ['BLUE', 'RED']  # Default colors


def extract_sizes(text: str) -> Dict[str, float]:
    """
    Extract size-related parameters from text.
    
    Args:
        text: Text containing size information
        
    Returns:
        Dictionary with size parameters
    """
    sizes = {}
    
    # Look for radius mentions
    radius_pattern = r'radius\s*[:=]?\s*(-?\d+\.?\d*)'
    radius_match = re.search(radius_pattern, text, re.IGNORECASE)
    if radius_match:
        sizes['radius'] = float(radius_match.group(1))
    
    # Look for side length mentions
    side_pattern = r'side\s*(?:length)?\s*[:=]?\s*(-?\d+\.?\d*)'
    side_match = re.search(side_pattern, text, re.IGNORECASE)
    if side_match:
        sizes['side_length'] = float(side_match.group(1))
    
    # Default sizes if not specified
    if 'radius' not in sizes:
        sizes['radius'] = 1.0
    if 'side_length' not in sizes:
        sizes['side_length'] = 2.0
    
    return sizes


def extract_duration(text: str) -> float:
    """
    Extract duration in seconds from text.
    
    Args:
        text: Text containing duration info
        
    Returns:
        Duration in seconds (default 4.0)
    """
    # Look for "X seconds" or "duration: X"
    pattern = r'(?:duration|time).*?(\d+\.?\d*)\s*(?:second|sec|s)'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return float(match.group(1))
    
    # Look for "Total Duration: X seconds"
    pattern2 = r'Total Duration:\s*(\d+\.?\d*)'
    match2 = re.search(pattern2, text)
    if match2:
        return float(match2.group(1))
    
    return 4.0  # Default


def extract_point_count(text: str) -> int:
    """
    Determine how many points/objects are mentioned.
    
    Args:
        text: Text to analyze
        
    Returns:
        Number of points/objects
    """
    # Count coordinate pairs
    coords = extract_coordinates(text)
    if coords:
        return len(coords)
    
    # Look for explicit count mentions
    pattern = r'(\d+)\s*(?:points?|circles?|squares?|objects?|neurons?|nodes?)'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    
    return 3  # Default


def extract_parameters(technical_spec: str) -> Dict:
    """
    Extract all useful parameters from a technical specification.
    
    Args:
        technical_spec: Plain text technical specification
        
    Returns:
        Dictionary containing extracted parameters
    """
    return {
        'coordinates': extract_coordinates(technical_spec),
        'colors': extract_colors(technical_spec),
        'sizes': extract_sizes(technical_spec),
        'duration': extract_duration(technical_spec),
        'numbers': extract_numbers(technical_spec),
        'point_count': extract_point_count(technical_spec)
    }


def generate_plot_points_code(coordinates: List[Tuple[float, float]], colors: List[str]) -> str:
    """
    Generate Manim code to plot specific points.
    
    Args:
        coordinates: List of (x, y) coordinate tuples
        colors: List of color names to use
        
    Returns:
        Manim code string
    """
    if not coordinates:
        return TEMPLATE_PLOT_BASIC
    
    # Normalize coordinates to fit in Manim's viewport
    xs = [x for x, y in coordinates]
    ys = [y for x, y in coordinates]
    
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    
    # Calculate appropriate axis ranges with padding
    x_range_min = x_min - 1
    x_range_max = x_max + 1
    y_range_min = y_min - 1
    y_range_max = y_max + 1
    
    color = colors[0] if colors else 'BLUE'
    
    # Generate points string
    points_str = ', '.join([f'({x}, {y})' for x, y in coordinates])
    
    return f'''from manim import *

class GeneratedScene(Scene):
    def construct(self):
        # Create axes with appropriate range
        axes = Axes(
            x_range=[{x_range_min}, {x_range_max}, 1],
            y_range=[{y_range_min}, {y_range_max}, 1],
            axis_config={{"include_tip": True}},
            x_length=10,
            y_length=6
        )
        
        # Add labels
        x_label = Text("x", font_size=24).next_to(axes.x_axis.get_end(), RIGHT)
        y_label = Text("y", font_size=24).next_to(axes.y_axis.get_end(), UP)
        
        # Create dots for each point
        points = [
            Dot(axes.c2p(x, y), color={color}, radius=0.1)
            for x, y in [{points_str}]
        ]
        
        # Create labels for points
        labels = [
            Text(f"({x},{y})", font_size=20).next_to(dot, UP)
            for dot, (x, y) in zip(points, [{points_str}])
        ]
        
        # Animate
        self.play(Create(axes), Write(x_label), Write(y_label))
        self.play(*[Create(dot) for dot in points])
        self.play(*[Write(label) for label in labels])
        self.wait(2)
'''


# Basic plot template for when no coordinates are given
TEMPLATE_PLOT_BASIC = '''from manim import *

class GeneratedScene(Scene):
    def construct(self):
        axes = Axes(
            x_range=[-3, 3, 1],
            y_range=[-2, 2, 1],
            axis_config={"include_tip": True}
        )
        
        x_label = Text("x", font_size=24).next_to(axes.x_axis.get_end(), RIGHT)
        y_label = Text("y", font_size=24).next_to(axes.y_axis.get_end(), UP)
        
        graph = axes.plot(lambda x: x**2 / 3, color=BLUE)
        graph_label = Text("f(x) = x²", font_size=28, color=BLUE).to_corner(UL)
        
        self.play(Create(axes), Write(x_label), Write(y_label))
        self.play(Create(graph), Write(graph_label))
        self.wait(2)
'''
