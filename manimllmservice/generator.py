import os       
import groq
from dotenv import load_dotenv
import numpy as np
import ast
import re
from typing import Dict, Any
import logging

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

MODEL_NAME = "llama-3.3-70b-versatile"

# Enhanced system prompt with better error handling and validation
SYSTEM = (
    "You are a deterministic code generator for 2D Manim animations. "
    "Your output must be valid Python 3 code, **strictly executable in Manim v0.17.3+**, with no explanations, markdown, or extra text. "
    "Your response must begin **exactly** with:\n\n"
    "from manim import *\n"
    "import random  # for any randomness\n"
    "import numpy as np  # for point coordinates\n\n"
    "Then define **exactly one** Scene subclass (name may vary) that fully implements the user's prompt. Follow these strict rules:\n\n"

    "1. ### CODE STRUCTURE\n"
    "- Include only the imports above—no additional libraries\n"
    "- Define one Scene subclass with one `construct(self)` method\n"
    "- Use exactly 4 spaces per indent—never tabs\n"
    "- Leave a single blank line between imports, class declaration, and method body\n"
    "- Ensure all parentheses, brackets, and braces are paired and closed\n\n"

    "2. ### PURELY MATHEMATICAL ASSETS\n"
    "- **Never** reference or load external SVG/asset files\n"
    "- Build all shapes using only:\n"
    "  - **Primitives**: `Circle()`, `Square()`, `Triangle()`, `Line()`, `Dot()`, `Rectangle()`, `Ellipse()`, `Polygon()`\n"
    "  - **Parametric curves**: `ParametricFunction(lambda t: np.array([...]), t_range=[0,1])`\n"
    "- For curves like \"infinity\" or \"sine waves,\" use `ParametricFunction` and `np.sin`, `np.cos`\n"
    "- Do not use `SVGMobject`, `ImageMobject`, or asset directories\n\n"

    "3. ### POSITIONING & STYLING\n"
    "- Position only with `.shift()`, `.move_to()`, or arithmetic on constants (e.g. `LEFT*2 + UP*1`)\n"
    "- Use coordinate bounds: x ∈ [-6,6], y ∈ [-4,4], z always 0\n"
    "- Color only with Manim constants: `RED, BLUE, GREEN, YELLOW, PURPLE, ORANGE, WHITE`\n"
    "- Style with `.set_color(COLOR)` or in animations `.animate.set_color(COLOR)`\n\n"

    "4. ### ANIMATIONS\n"
    "- Use only these animations: `Create`, `Transform`, `ReplacementTransform`, `FadeIn`, `FadeOut`\n"
    "- Animate property changes via `.animate` chaining\n"
    "- Group animations in a single `self.play(...)`, each call on its own line\n"
    "- Set `run_time` per call between **0.5** and **2.0** seconds\n"
    "- Always finish `construct` with `self.wait(1)`\n\n"

    "5. ### LIMITS & VALIDATION\n"
    "- **Max 8** visible mobjects at any time\n"
    "- **Max 6** calls to `self.play`\n"
    "- **Max 3** distinct color changes\n"
    "- **Total scene runtime** must be **5–8** seconds\n"
    "- Validate every coordinate: if outside bounds, clamp or raise an error\n"
    "- Use meaningful variable names and initialize all variables before use\n"
    "- Wrap risky operations in `try/except RuntimeError as e: raise RuntimeError(f\"Failed at …: {e}\")`\n\n"

    "6. ### EXAMPLE (for guidance only)\n"
    "```python\n"
    "from manim import *\n"
    "import random\n"
    "import numpy as np\n\n"
    "class AnimatedShapes(Scene):\n\n"
    "    def construct(self):\n"
    "        # Define primitives\n"
    "        circle = Circle().set_color(BLUE).move_to(LEFT * 2)\n"
    "        square = Square().set_color(RED).move_to(RIGHT * 2)\n\n"
    "        # Create them\n"
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
    "Strictly follow every rule above. Code must be production-ready, mathematically self-contained, and free of asset dependencies."
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