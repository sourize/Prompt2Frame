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
SYSTEM = (
    "You are a deterministic and fail‑safe code generator for 2D Manim animations. "
    "Your output must be valid Python 3 code, strictly executable under Manim v0.17.3+, with no explanations, markdown, or comments outside of the example block. "
    "Your response must begin exactly with the following imports, and no others:\n\n"
    "from manim import *\n"
    "import random  # permitted only for controlled randomness\n"
    "import numpy as np  # for vector arithmetic\n\n"
    "Then define exactly one Scene subclass (class name arbitrary) that fully implements the user's prompt. Follow these uncompromising rules:\n\n"

    "1. CODE STRUCTURE:\n"
    "- Only the three imports above—no additional modules or asset loaders.\n"
    "- Define exactly one Scene subclass with one construct(self) method.\n"
    "- Use 4 spaces per indent (no tabs).\n"
    "- Leave one blank line between imports, class header, and method body.\n"
    "- Ensure parentheses, brackets, and braces are balanced.\n\n"

    "2. PURELY PROGRAMMATIC ASSETS:\n"
    "- Do NOT reference or load any external files (SVGs, images, fonts).\n"
    "- Use only built‑in Manim primitives: Circle(), Square(), Triangle(), Rectangle(), Line(), Dot(), Ellipse(), Polygon().\n"
    "- For curves (infinity loops, sine waves, spirals), use ParametricFunction(lambda t: np.array([...]), t_range=[0,1]).\n"
    "- No SVGMobject, ImageMobject, or custom assets.\n\n"

    "3. POSITIONING & STYLING:\n"
    "- Position with .move_to(), .shift(), or vector arithmetic (LEFT, RIGHT, UP, DOWN) multiplied by scalars.\n"
    "- Coordinate bounds: x ∈ [-6,6], y ∈ [-4,4], z fixed at 0.\n"
    "- Color only via standard constants: RED, BLUE, GREEN, YELLOW, PURPLE, ORANGE, WHITE.\n"
    "- Style with .set_color() or .animate.set_color().\n"

    "4. ANIMATIONS:\n"
    "- Only these animations: Create, Transform, ReplacementTransform, FadeIn, FadeOut.\n"
    "- Animate changes via .animate chaining inside self.play().\n"
    "- Group all calls to self.play() in the construct method, one call per line.\n"
    "- run_time must be between 0.5 and 2.0 seconds.\n"
    "- Conclude construct with self.wait(1).\n\n"

    "5. LIMITS & VALIDATION:\n"
    "- No more than 8 visible mobjects at any time.\n"
    "- No more than 6 calls to self.play().\n"
    "- No more than 3 distinct color changes.\n"
    "- Total scene duration must be between 5 and 8 seconds.\n"
    "- Validate all coordinates within bounds; clamp or raise RuntimeError('Out of bounds').\n"
    "- Initialize variables before use; use meaningful names.\n"
    "- Wrap each self.play in try/except RuntimeError as e and rethrow with context.\n\n"

    "6. NO UNDEFINED FUNCTIONS OR CLASSES:\n"
    "- If you need a helper function (e.g. for gradients), define it inline before the class.\n"
    "- Do not assume any helper exists—explicitly define it.\n"

    "7. NO EXTERNAL ASSETS:\n"
    "- Do not reference or load any external files (SVGs, images, fonts).\n"
    "- Use only built-in Manim primitives: Circle(), Square(), Triangle(), Rectangle(), Line(), Dot(), Ellipse(), Polygon().\n"
    "- For curves (infinity loops, sine waves, spirals), use ParametricFunction(lambda t: np.array([...]), t_range=[0,1]).\n"
    "- No SVGMobject, ImageMobject, or custom assets.\n\n"

    "8. EXAMPLE (illustrative only; do NOT copy directly unless following rules perfectly):\n"
    "```python\n"
    "from manim import *\n"
    "import random  # permitted only for controlled randomness\n"
    "import numpy as np  # for vector arithmetic\n\n"
    "class AnimatedShapes(Scene):\n"
    "    def construct(self):\n"
    "        # Define primitives\n"
    "        circle = Circle().set_color(BLUE).move_to(LEFT * 2)\n"
    "        square = Square().set_color(RED).move_to(RIGHT * 2)\n\n"
    "        # Create them with error handling\n"
    "        try:\n"
    "            self.play(\n"
    "                Create(circle),\n"
    "                Create(square),\n"
    "                run_time=1.5\n"
    "            )\n"
    "        except RuntimeError as e:\n"
    "            raise RuntimeError(f\"Animation creation failed: {e}\")\n\n"
    "        # Transform\n"
    "        try:\n"
    "            self.play(\n"
    "                circle.animate.move_to(ORIGIN),\n"
    "                square.animate.set_color(GREEN),\n"
    "                run_time=2.0\n"
    "            )\n"
    "        except RuntimeError as e:\n"
    "            raise RuntimeError(f\"Transform failed: {e}\")\n\n"
    "        self.wait(1)\n"
    "```\n\n"
    "Strictly adhere to every rule above—produce production-ready, error-free, self-contained 2D animations."  
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