import os       
import groq
from dotenv import load_dotenv
import numpy as np
import ast
import re
from typing import Dict, Any
import logging
import time

logger = logging.getLogger(__name__)

# Helper to strip unsupported kwargs (opacity, fill_opacity, etc.)
def _sanitize_code(code: str) -> str:
    # remove any 'opacity=...', 'fill_opacity=...' inside constructor calls
    return re.sub(r',\s*(?:opacity|fill_opacity)\s*=\s*[^,\)\n]+', '', code)

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

MODEL_NAME = "meta-llama/llama-4-scout-17b-16e-instruct"

# Enhanced system prompt with better error handling and validation
SYSTEM_PROMPT = """
You are a deterministic, production‑grade code generator for 2D Manim v0.17.3+ animations.  
All output must be pure Python3, no markdown or comments outside code blocks.  

1. ALWAYS BEGIN with exactly these imports:
   
   from manim import *
   import numpy as np  # for vectors and parametric functions

2. DEFINE any helper functions you need—including easing curves—immediately below imports.  
   For example:
   
   def ease_in_out_sine(t: float) -> float:
       # maps t in [0,1] to eased value
       from math import sin, pi
       return 0.5 * (1 - np.cos(pi * t))

3. ONLY use built‑in Manim primitives:
   Circle, Square, Triangle, Rectangle, Line, Dot, Ellipse, Polygon, ParametricFunction.

4. STRUCTURE:
   - Exactly one Scene subclass with a single construct(self) method.
   - 4‑space indents, no tabs; one blank line between imports, helpers, class header, and method body.
   - Balanced brackets.
   - No external assets or imports beyond the two above.

5. POSITIONING & COLORS:
   - Coordinates x ∈ [-6,6], y ∈ [-4,4], z always 0.
   - Position via .move_to(), .shift(), or algebraic vector ops.
   - Colors only via constants: RED, BLUE, GREEN, YELLOW, PURPLE, ORANGE, WHITE.

6. ANIMATIONS:
   - Only Create, Transform, ReplacementTransform, FadeIn, FadeOut.
   - Chain .animate for property changes inside self.play().
   - One self.play() call per line, max 6 plays, run_time ∈ [0.5,2.0].
   - Wrap each self.play call in try/except RuntimeError as e, rethrow with context message.
   - End construct with self.wait(1).

7. LIMITS:
   - ≤8 visible mobjects at once.
   - ≤3 distinct color changes.
   - Total scene duration ∈ [5,8] seconds.
   - Validate and clamp any out-of-bounds coordinates or raise RuntimeError("Out of bounds").

EXAMPLE OUTPUT (do not include comments outside code block):
```python
from manim import *
import numpy as np  # for vectors and parametric functions

def ease_in_out_sine(t: float) -> float:
    from math import cos, pi
    return 0.5 * (1 - cos(pi * t))

class MyScene(Scene):
    def construct(self):
        circle = Circle().set_color(BLUE).move_to(LEFT * 2)
        square = Square().set_color(RED).move_to(RIGHT * 2)

        try:
            self.play(
                Create(circle),
                Create(square),
                run_time=1.5,
            )
        except RuntimeError as e:
            raise RuntimeError(f"Creation failed: {e}")

        try:
            self.play(
                circle.animate.move_to(ORIGIN),
                square.animate.set_color(GREEN),
                run_time=2.0,
            )
        except RuntimeError as e:
            raise RuntimeError(f"Transform failed: {e}")

        self.wait(1)
Strictly adhere to the above rules, include helper definitions to avoid NameError, and produce self‑contained, renderable Manim code every time.
"""

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
        
        # Ensure self.play() calls exist
        if "self.play(" not in code:
            logger.warning("No self.play() calls found - animation may be empty")
        
        # Check for potential memory issues
        if code.count("np.array") > 20:
            logger.warning("High number of numpy arrays created - potential memory issue")
        
        # Check for animation complexity
        if code.count("self.play") > 10:
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
            
            response = get_client().chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=0.2 + (attempt * 0.1),  # Slightly increase randomness on retries
                max_tokens=2000,
                top_p=0.9,
            )
            
            raw_code = response.choices[0].message.content.strip()
            code = _clean_and_format_code(raw_code)
            code = _sanitize_code(code)
            
            # Comprehensive validation
            validator.validate_structure(code)
            validator.validate_syntax(code)
            validator.validate_scene_class(code)
            validator.validate_balanced_delimiters(code)
            validator.validate_manim_methods(code)
            
            logger.info("Code generation successful")
            return code
            
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt == max_retries - 1:
                logger.error(f"All {max_retries} attempts failed")
                raise RuntimeError(f"Code generation failed after {max_retries} attempts: {str(e)}")
            
            # Brief pause before retry
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
        circle = Circle().set_color(BLUE).move_to(ORIGIN)
        try:
            self.play(Create(circle), run_time=1.0)
        except RuntimeError as err:
            raise RuntimeError(f"Fallback animation failed: {err}")
        self.wait(1)
"""
        return fallback_code