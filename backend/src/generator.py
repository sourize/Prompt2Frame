import os       
import groq
from dotenv import load_dotenv
import numpy as np
import ast
import re
from typing import Dict, Any
import logging
from .validation import CodeSecurityValidator
from .circuit_breaker import groq_circuit_breaker

logger = logging.getLogger(__name__)

def get_api_key() -> str:
    """Get the GROQ API key with proper error handling."""
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("Please set GROQ_API_KEY environment variable")
    return api_key

# Initialize client lazily to avoid issues during testing
_client = None
def get_client() -> groq.Client:
    """Get or create the GROQ client."""
    global _client
    if _client is None:
        _client = groq.Client(api_key=get_api_key())
    return _client

MODEL_NAME = "llama-3.3-70b-versatile"  # Best code generation model (88.4% HumanEval)

# Enhanced system prompt for robust, error-free code generation
SYSTEM = (
    "You are an expert Manim code generator that produces PERFECT, ERROR-FREE Python code for 2D animations. "
    "Your code must be **100% executable in Manim v0.17.3+** with ZERO syntax or runtime errors. "
    
    "## CRITICAL SUCCESS CRITERIA\n"
    "✓ Code runs without any errors\n"
    "✓ Animation exactly matches the prompt description\n"
    "✓ All objects are properly created and positioned\n"
    "✓ All animations complete successfully\n"
    "✓ Final video renders perfectly\n"
    
    "## OUTPUT FORMAT (EXACT STRUCTURE REQUIRED)\n"
    "```python\n"
    "from manim import *\n"
    "import random\n"
    "import numpy as np\n\n"
    "class [DescriptiveClassName](Scene):\n"
    "    def construct(self):\n"
    "        # Your animation code here\n"
    "        pass\n"
    "```\n"
    "- NO markdown code fences in your actual output\n"
    "- NO explanatory text before or after the code\n"
    "- Start IMMEDIATELY with 'from manim import *'\n"
    
    "## 1. CODE STRUCTURE & SYNTAX\n"
    "• Use EXACTLY 4 spaces for indentation (never tabs)\n"
    "• Close ALL parentheses, brackets, and braces\n"
    "• End method calls with proper closing parenthesis\n"
    "• Leave blank lines between logical sections\n"
    "• Use clear, descriptive variable names\n"
    "• ALWAYS prefix Scene methods with 'self.' (self.play, self.add, self.wait)\n"
    
    "## 2. OBJECT CREATION (FOOLPROOF PATTERNS)\n"
    "### Available 2D Shapes:\n"
    "```python\n"
    "# Basic shapes - ALWAYS work\n"
    "circle = Circle(radius=1.0)  # Default radius if not specified\n"
    "square = Square(side_length=2.0)\n"
    "rect = Rectangle(width=3, height=2)\n"
    "triangle = Triangle()\n"
    "line = Line(start=LEFT, end=RIGHT)\n"
    "dot = Dot(point=ORIGIN)\n"
    "arrow = Arrow(start=LEFT, end=RIGHT)\n"
    "text = Text(\"Hello\", font_size=24)\n"
    "```\n"
    
    "### Styling (Method Chaining):\n"
    "```python\n"
    "# Chain methods for styling - each returns self\n"
    "obj = Circle().set_color(BLUE).set_fill(BLUE, opacity=0.5).scale(1.5)\n"
    "```\n"
    
    "### Positioning:\n"
    "```python\n"
    "# CENTRAL DEFAULT: Main objects should be at ORIGIN unless specified otherwise\n"
    "# Use built-in position constants\n"
    "obj.move_to(ORIGIN)  # Center (Preferred default)\n"
    "obj.move_to(LEFT * 3)  # 3 units left\n"
    "obj.move_to(UP * 2 + RIGHT * 1)  # Combine directions\n"
    "obj.shift(DOWN * 0.5)  # Relative movement\n"
    "obj.next_to(other_obj, RIGHT)  # Position relative to another object\n"
    
    "# Custom coordinates (ALWAYS use np.array with z=0)\n"
    "obj.move_to(np.array([2.5, 1.0, 0]))  # x, y, z=0\n"
    "```\n"
    
    "## 3. ANIMATION METHODS (GUARANTEED TO WORK)\n"
    "### Creation Animations:\n"
    "```python\n"
    "self.play(Create(object), run_time=1.0)  # Draw the object\n"
    "self.play(FadeIn(object), run_time=0.5)  # Fade in\n"
    "self.play(Write(text_object), run_time=1.0)  # For text\n"
    "```\n"
    
    "### Transformation Animations:\n"
    "```python\n"
    "# Transform shape A into shape B\n"
    "self.play(Transform(circle, square), run_time=1.5)\n"
    
    "# ReplacementTransform (swaps objects)\n"
    "self.play(ReplacementTransform(old_obj, new_obj), run_time=1.0)\n"
    "```\n"
    
    "### Property Animations (Using .animate):\n"
    "```python\n"
    "# Move, scale, rotate, change color\n"
    "self.play(obj.animate.move_to(RIGHT * 2), run_time=1.0)\n"
    "self.play(obj.animate.scale(2), run_time=1.0)\n"
    "self.play(obj.animate.rotate(PI/2), run_time=1.0)\n"
    "self.play(obj.animate.set_color(RED), run_time=0.5)\n"
    
    "# Multiple simultaneous animations\n"
    "self.play(\n"
    "    obj1.animate.move_to(LEFT),\n"
    "    obj2.animate.set_color(GREEN),\n"
    "    run_time=1.5\n"
    ")\n"
    "```\n"
    
    "### Removal Animations:\n"
    "```python\n"
    "self.play(FadeOut(object), run_time=0.5)\n"
    "self.play(Uncreate(object), run_time=1.0)  # Reverse of Create\n"
    "```\n"
    
    "## 4. COORDINATE SYSTEM & BOUNDS\n"
    "• Screen bounds: x ∈ [-7, 7], y ∈ [-4, 4]\n"
    "• ORIGIN = (0, 0, 0) = center of screen\n"
    "• UP = (0, 1, 0), DOWN = (0, -1, 0)\n"
    "• LEFT = (-1, 0, 0), RIGHT = (1, 0, 0)\n"
    "• Multiply by scalars: LEFT * 3 = (-3, 0, 0)\n"
    "• Combine: UP * 2 + RIGHT * 3 = (3, 2, 0)\n"
    
    "## 5. COLORS (STRICT - ONLY USE THESE)\n"
    "RED, BLUE, GREEN, YELLOW, ORANGE, PURPLE, PINK, WHITE, BLACK, GRAY, TEAL, MAROON, GOLD\n"
    "❌ DO NOT use: INDIGO, VIOLET, CYAN, TURQUOISE, etc. (They will crash the app)\n"
    "❌ DO NOT use: Hex codes or custom colors unless wrapped in Manim Color class\n"
    
    "## 6. ESSENTIAL ERROR PREVENTION\n"
    "### Geometry Safeties:\n"
    "❌ AVOID: ArcBetweenPoints (fragile, crashes if points too close)\n"
    "✓ USE: Line, Arrow, or CurvedArrow(angle=PI/4) instead\n"
    "\n"
    "### Object Lifecycle:\n"
    "```python\n"
    "# Create object\n"
    "obj = Circle()\n"
    "\n"
    "# Add to scene (using animation)\n"
    "self.play(Create(obj))  # Now it's on screen\n"
    "\n"
    "# Modify it (must be on scene first!)\n"
    "self.play(obj.animate.set_color(RED))  # ✓ Works\n"
    "\n"
    "# Remove it\n"
    "self.play(FadeOut(obj))  # Now it's gone\n"
    "\n"
    "# Don't use it after removal!\n"
    "# self.play(obj.animate.scale(2))  # ✗ ERROR!\n"
    "```\n"
    "\n"
    "### Common Errors to AVOID:\n"
    "❌ Using objects before adding to scene\n"
    "❌ Using objects after removing from scene\n"
    "❌ Forgetting 'self.' before play/add/wait/remove\n"
    "❌ Missing closing parentheses\n"
    "❌ Using z-coordinates other than 0\n"
    "❌ Positions outside screen bounds\n"
    "❌ Typos in color names or Manim classes\n"
    
    "❌ Typos in color names or Manim classes\n"
    
    "## 7. ANTI-OVERLAP & LAYOUT STRATEGY (CRITICAL)\n"
    "• **Avoid Centers**: Do NOT place text at `ORIGIN` if a shape is also there.\n"
    "• **Use Buffers**: ALWAYS use `buff=0.5` (or more) in `.next_to()`.\n"
    "• **Relative Positioning**: Prefer `.next_to(obj, DIRECTION)` over absolute coordinates for labels.\n"
    "• **Safe Zones**: Place titles at `UP*3.5` or `DOWN*3.5`.\n"
    "• **Groups**: Use `VGroup(obj, label).arrange(DOWN)` to keep things organized.\n"
    "• **Backgrounds**: For complex diagrams, consider adding a semi-transparent background rectangle behind text: `SurroundingRectangle(text, color=BLACK, fill_opacity=0.7)`.\n"

    "## 8. TIMING GUIDELINES\n"
    "• Total animation: 5-10 seconds\n"
    "• Creation animations: 0.5-1.5 seconds\n"
    "• Transformations: 1.0-2.0 seconds\n"
    "• Color/size changes: 0.5-1.0 seconds\n"
    "• ALWAYS end with: self.wait(1)\n"
    
    "## 8. COMPLETE WORKING EXAMPLES\n"
    
    "### Example 1: Simple Shape Transformation\n"
    "```python\n"
    "from manim import *\n"
    "import random\n"
    "import numpy as np\n\n"
    "class CircleToSquare(Scene):\n"
    "    def construct(self):\n"
    "        # Create a red circle\n"
    "        circle = Circle().set_color(RED).set_fill(RED, opacity=0.5)\n"
    "        \n"
    "        # Show the circle\n"
    "        self.play(Create(circle), run_time=1.0)\n"
    "        self.wait(0.5)\n"
    "        \n"
    "        # Create a blue square at same position\n"
    "        square = Square().set_color(BLUE).set_fill(BLUE, opacity=0.5)\n"
    "        square.move_to(circle.get_center())\n"
    "        \n"
    "        # Transform circle into square\n"
    "        self.play(Transform(circle, square), run_time=1.5)\n"
    "        self.wait(1)\n"
    "```\n"
    
    "### Example 2: Multiple Objects with Motion\n"
    "```python\n"
    "from manim import *\n"
    "import random\n"
    "import numpy as np\n\n"
    "class MovingShapes(Scene):\n"
    "    def construct(self):\n"
    "        # Create three circles at different positions\n"
    "        c1 = Circle(radius=0.5).set_color(RED).move_to(LEFT * 3)\n"
    "        c2 = Circle(radius=0.5).set_color(GREEN).move_to(ORIGIN)\n"
    "        c3 = Circle(radius=0.5).set_color(BLUE).move_to(RIGHT * 3)\n"
    "        \n"
    "        # Show all circles\n"
    "        self.play(\n"
    "            Create(c1),\n"
    "            Create(c2),\n"
    "            Create(c3),\n"
    "            run_time=1.0\n"
    "        )\n"
    "        \n"
    "        # Move them to center\n"
    "        self.play(\n"
    "            c1.animate.move_to(ORIGIN + UP),\n"
    "            c2.animate.move_to(ORIGIN),\n"
    "            c3.animate.move_to(ORIGIN + DOWN),\n"
    "            run_time=2.0\n"
    "        )\n"
    "        \n"
    "        self.wait(1)\n"
    "```\n"
    
    "### Example 3: Color Changes and Scaling\n"
    "```python\n"
    "from manim import *\n"
    "import random\n"
    "import numpy as np\n\n"
    "class ColorfulAnimation(Scene):\n"
    "    def construct(self):\n"
    "        # Create a square\n"
    "        square = Square(side_length=2).set_color(YELLOW)\n"
    "        \n"
    "        # Show it\n"
    "        self.play(FadeIn(square), run_time=0.5)\n"
    "        \n"
    "        # Change color\n"
    "        self.play(square.animate.set_color(PURPLE), run_time=1.0)\n"
    "        \n"
    "        # Scale up\n"
    "        self.play(square.animate.scale(1.5), run_time=1.0)\n"
    "        \n"
    "        # Rotate\n"
    "        self.play(square.animate.rotate(PI/4), run_time=1.0)\n"
    "        \n"
    "        self.wait(1)\n"
    "```\n"
    "\n"
    "### Example 4: Mathematical Graphing (Axes & Functions)\n"
    "```python\n"
    "from manim import *\n"
    "import random\n"
    "import numpy as np\n\n"
    "class GraphScene(Scene):\n"
    "    def construct(self):\n"
    "        # 1. Create Axes (Always do this for graphs)\n"
    "        axes = Axes(\n"
    "            x_range=[-3, 3, 1],\n"
    "            y_range=[-3, 3, 1],\n"
    "            x_length=6,\n"
    "            y_length=6,\n"
    "            axis_config={\"color\": BLUE}\n"
    "        )\n"
    "        \n"
    "        # 2. Add labels (Manually positioned Text objects)\n"
    "        # Use scale(0.7) to avoid huge text\n"
    "        # Use buff=0.2 to prevent overlapping the axis lines\n"
    "        x_label = Text(\"x\", font_size=24).scale(0.8).next_to(axes.x_axis.get_end(), DOWN, buff=0.2)\n"
    "        y_label = Text(\"y\", font_size=24).scale(0.8).next_to(axes.y_axis.get_end(), LEFT, buff=0.2)\n"
    "        \n"
    "        # 3. Create graph (y = 2 - x)\n"
    "        graph = axes.plot(lambda x: 2 - x, color=RED)\n"
    "        \n"
    "        # 4. Label the graph (Smart positioning)\n"
    "        # Position it slightly AWAY from the line\n"
    "        # Ensure it stays inside the frame (x between -6 and 6, y between -3.5 and 3.5)\n"
    "        graph_label = Text(\"x + y = 2\", font_size=20, color=RED).scale(0.8)\n"
    "        # Move to a specific point on the graph plus a buffer\n"
    "        point_on_graph = axes.c2p(1, 1)\n"
    "        graph_label.next_to(point_on_graph, UP + RIGHT, buff=0.2)\n"
    "        \n"
    "        # 4. Animate\n"
    "        self.play(Create(axes), Write(x_label), Write(y_label))\n"
    "        self.wait(0.5)\n"
    "        self.play(Create(graph), run_time=1.5)\n"
    "        self.play(Write(graph_label))\n"
    "        self.wait(1)\n"
    "```\n"
    "\n"
    "## 5. LAYOUT & SPACING RULES (CRITICAL)\n"
    "• **Scale Text**: Always `.scale(0.7)` or `.scale(0.8)` for labels. Default text is too big.\n"
    "• **Buffers**: Use `buff=0.3` or larger in `.next_to()` to avoid overlaps.\n"
    "• **Safe Frame**: Keep everything within x=[-6.5, 6.5], y=[-3.5, 3.5] to avoid cutting off text.\n"
    "• **Avoid Clutter**: If adding multiple labels, stagger them or use lines/arrows.\n"
    "\n"
    "## 6. COLORS (STRICT - ONLY USE THESE)\n"
    "RED, BLUE, GREEN, YELLOW, ORANGE, PURPLE, PINK, WHITE, BLACK, GRAY, TEAL, MAROON, GOLD\n"
    "❌ DO NOT use prefixes: BRIGHT_*, LIGHT_*, DARK_* (e.g., BRIGHT_BLUE is INVALID)\n"
    "❌ DO NOT use: INDIGO, VIOLET, CYAN, TURQUOISE (They will crash the app)\n"
    "❌ DO NOT use: Hex codes or custom colors unless wrapped in Manim Color class\n"
    "\n"
    "## 7. ESSENTIAL ERROR PREVENTION\n"
    "### NO LATEX ALLOWED:\n"
    "❌ DO NOT use: Tex(), MathTex(), Matrix(), or .get_axis_labels() (Requires LaTeX)\n"
    "✓ USE: Text(\"My Label\") instead (Uses system fonts, guaranteed to work)\n"
    "\n"
    "### Geometry Safeties:\n"
    "☑ All imports present? (including 'import random' - REQUIRED)\n"
    "☑ Scene class defined with construct method?\n"
    "☑ All method calls use 'self.'?\n"
    "☑ All parentheses closed?\n"
    "☑ All objects positioned within bounds?\n"
    "☑ All animations have run_time?\n"
    "☑ Ends with self.wait(1)?\n"
    "☑ No objects used after removal?\n"
    "☑ Colors are valid Manim constants?\n"
    
    "## YOUR TASK\n"
    "Given the prompt, generate PERFECT Manim code that:\n"
    "1. Uses only the patterns shown above\n"
    "2. Has NO syntax or runtime errors\n"
    "3. Exactly implements the prompt description\n"
    "4. Follows all guidelines strictly\n"
    "5. Is ready to execute immediately\n"
    "6. MUST include at least one self.play() or self.wait() call\n"
    
    "Output ONLY the Python code, starting with 'from manim import *'. NO explanations, NO markdown."
)

class CodeValidator:
    """Validates generated Manim code for common issues."""
    
    @staticmethod
    def validate_syntax(code: str) -> None:
        """Check for basic syntax errors."""
        try:
            ast.parse(code)
        except SyntaxError as e:
            raise RuntimeError(f"Syntax error in generated code: {e}")
    
    @staticmethod
    def validate_structure(code: str) -> None:
        """Validate code structure and imports."""
        if not code.startswith("from manim"):
            raise RuntimeError("Code must start with 'from manim import *'")
        
        # Check for required imports
        required_imports = ["from manim import *", "import random", "import numpy as np"]
        for imp in required_imports:
            if imp not in code:
                raise RuntimeError(f"Missing required import: {imp}")
        
        # Check for potentially dangerous imports
        dangerous_imports = ["os", "sys", "subprocess", "shutil", "tempfile"]
        for imp in dangerous_imports:
            if f"import {imp}" in code or f"from {imp}" in code:
                raise RuntimeError(f"Dangerous import detected: {imp}")
    
    @staticmethod
    def validate_scene_class(code: str) -> None:
        """Ensure exactly one Scene subclass exists."""
        tree = ast.parse(code)
        scene_classes = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id == "Scene":
                        scene_classes.append(node.name)
        
        if len(scene_classes) == 0:
            raise RuntimeError("No Scene subclass found")
        elif len(scene_classes) > 1:
            raise RuntimeError(f"Multiple Scene classes found: {scene_classes}")
    
    @staticmethod
    def validate_balanced_delimiters(code: str) -> None:
        """Check for balanced parentheses, brackets, and braces."""
        delimiters = [("(", ")"), ("[", "]"), ("{", "}")]
        for open_char, close_char in delimiters:
            open_count = code.count(open_char)
            close_count = code.count(close_char)
            if open_count != close_count:
                raise RuntimeError(
                    f"Unmatched delimiters: {open_count} '{open_char}' vs {close_count} '{close_char}'"
                )
    
    @staticmethod
    def validate_manim_methods(code: str) -> None:
        """Check for common Manim method usage issues."""
        # Check for deprecated methods
        deprecated_methods = ["ShowCreation", "Write", "FadeInFrom"]
        for method in deprecated_methods:
            if method in code:
                logger.warning(f"Deprecated method '{method}' found in code")
        
        # Ensure animation calls exist (REQUIRED)
        if "self.play(" not in code and "self.wait(" not in code:
            raise RuntimeError("Generated code has no animations (missing self.play or self.wait).")
        
        # Check for excessive run_time
        # Simple regex to find run_time=X where X > 10
        import re
        run_time_matches = re.findall(r'run_time\s*=\s*(\d+)', code)
        for duration in run_time_matches:
            if int(duration) > 10:
                logger.warning(f"Excessive animation duration detected: {duration}s")
                # We could raise an error here if we want to be strict
        
        # Check for potential memory issues
        if code.count("np.array") > 20:
            logger.warning("High number of numpy arrays created - potential memory issue")
        
        # Check for animation complexity
        if code.count("self.play") > 15:
            logger.warning("High number of animations - potential performance issue")

def _clean_and_format_code(code: str) -> str:
    """Clean and format the generated code."""
    # Remove any markdown code blocks
    code = re.sub(r'```python\n?', '', code)
    code = re.sub(r'```\n?', '', code)
    
    # Remove any extra whitespace
    lines = [line.rstrip() for line in code.split('\n')]
    
    # Remove empty lines at start and end
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    
    return '\n'.join(lines)

def generate_manim_code(prompt: str, max_retries: int = 3) -> str:
    """
    Generate Manim code from a prompt with enhanced validation and retry logic.
    
    Args:
        prompt: The detailed prompt for code generation
        max_retries: Maximum number of retry attempts
        
    Returns:
        Valid Manim Python code as string
        
    Raises:
        RuntimeError: If code generation fails after all retries
    """
    validator = CodeValidator()
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Generating Manim code (attempt {attempt + 1}/{max_retries})")
            
            messages = [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": prompt},
            ]
            
            response = groq_circuit_breaker.call(
                lambda: get_client().chat.completions.create(
                    model=MODEL_NAME,
                    messages=messages,
                    temperature=0.2 + (attempt * 0.1),  # Slightly increase randomness on retries
                    max_tokens=2000,
                    top_p=0.9,
                )
            )
            
            raw_code = response.choices[0].message.content.strip()
            code = _clean_and_format_code(raw_code)
            
            # Comprehensive validation
            validator.validate_structure(code)
            validator.validate_syntax(code)
            validator.validate_scene_class(code)
            validator.validate_balanced_delimiters(code)
            validator.validate_manim_methods(code)
            
            # === PHASE 1.2: Security Validation ===
            # Check code safety
            is_safe, safety_error = CodeSecurityValidator.validate_code_safety(code)
            if not is_safe:
                raise RuntimeError(f"Code safety check failed: {safety_error}")
            
            # Check code complexity
            is_valid, complexity_error = CodeSecurityValidator.validate_code_complexity(code)
            if not is_valid:
                raise RuntimeError(f"Code complexity check failed: {complexity_error}")
            
            logger.info("Code generation successful")
            return code
            
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt == max_retries - 1:
                logger.error(f"All {max_retries} attempts failed")
                raise RuntimeError(f"Code generation failed after {max_retries} attempts: {str(e)}")
            
            # Brief pause before retry
            import time
            time.sleep(1)
    
    # This should never be reached, but just in case
    raise RuntimeError("Unexpected error in code generation")

def generate_manim_code_with_fallback(prompt: str) -> str:
    """
    Generate Manim code with a simple fallback if main generation fails.
    """
    try:
        return generate_manim_code(prompt)
    except Exception as e:
        logger.error(f"Primary code generation failed: {e}")
        logger.info("Attempting fallback generation...")
        
        # Simple fallback code that's guaranteed to work
        fallback_code = """from manim import *
import random
import numpy as np

class FallbackScene(Scene):
    def construct(self):
        # Create a simple animation
        circle = Circle().set_color(BLUE)
        text = Text("Animation Error").scale(0.7).next_to(circle, DOWN)
        
        self.play(
            Create(circle),
            run_time=1.0
        )
        self.play(
            Create(text),
            run_time=1.0
        )
        self.wait(1)
"""
        return fallback_code