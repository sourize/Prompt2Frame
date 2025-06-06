# Enhanced executor.py
import os
import groq
from dotenv import load_dotenv
import numpy as np
import ast
import re
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

load_dotenv()
API_KEY = os.getenv("GROQ_API_KEY")
if not API_KEY:
    raise RuntimeError("Please set GROQ_API_KEY")

client = groq.Client(api_key=API_KEY)
MODEL_NAME = "llama3-70b-8192"

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
    "- Use exactly 4 spaces per indent level—never tabs\n"
    "- Leave a single blank line between major blocks (imports, class, method)\n"
    "- Ensure all parentheses, brackets, and braces are properly closed\n"

    "2. ### OBJECTS & POSITIONING\n"
    "- Use only 2D primitives: `Circle()`, `Square()`, `Triangle()`, `Line()`, `Dot()`, `Rectangle()`\n"
    "- Construct all shapes using zero-argument constructors or with basic parameters\n"
    "- Position using only `.shift()`, `.move_to()`, `.next_to()`\n"
    "- For random positions, use `np.array([x, y, 0])` for points (always include z=0)\n"
    "- Use coordinate bounds: x in [-6, 6], y in [-4, 4]\n"
    "- Label objects with `Text(...)` if needed\n"
    "- Style using `.set_color(COLOR)` or `.animate.set_color(COLOR)`\n"
    "- Use method chaining on separate lines for readability\n"

    "3. ### ANIMATIONS\n"
    "- Use only `Create`, `Transform`, `ReplacementTransform`, `FadeIn`, `FadeOut`\n"
    "- Animate property changes with `.animate`\n"
    "- Group animations in `self.play(...)`, each on a new line\n"
    "- Set `run_time` for each animation (0.5 to 2.0 seconds)\n"
    "- Always end with `self.wait(1)` for proper timing\n"

    "4. ### CONSTRAINTS\n"
    "- Max 8 visible objects total\n"
    "- Max 6 animations per scene\n"
    "- Max 3 color changes\n"
    "- Max total runtime: 5–8 seconds\n"
    "- Use only standard Manim colors: RED, BLUE, GREEN, YELLOW, PURPLE, ORANGE, WHITE\n"
    "- Ensure proper spacing between objects\n"

    "5. ### CODE QUALITY & ERROR PREVENTION\n"
    "- Always prefix method calls with `self.` inside `construct`\n"
    "- Initialize all variables before use\n"
    "- Use try-except blocks for potentially failing operations\n"
    "- Validate coordinates are within bounds\n"
    "- Check for object existence before operations\n"
    "- Use meaningful variable names\n"

    "6. ### ENHANCED EXAMPLE\n"
    "```python\n"
    "from manim import *\n"
    "import random\n"
    "import numpy as np\n\n"
    "class AnimatedShapes(Scene):\n"
    "    def construct(self):\n"
    "        # Create objects with validation\n"
    "        circle = Circle().set_color(BLUE).move_to(LEFT * 2)\n"
    "        square = Square().set_color(RED).move_to(RIGHT * 2)\n"
    "        \n"
    "        # Animate creation\n"
    "        self.play(\n"
    "            Create(circle),\n"
    "            Create(square),\n"
    "            run_time=1.5\n"
    "        )\n"
    "        \n"
    "        # Transform and move\n"
    "        self.play(\n"
    "            circle.animate.move_to(ORIGIN),\n"
    "            square.animate.set_color(GREEN),\n"
    "            run_time=2.0\n"
    "        )\n"
    "        \n"
    "        self.wait(1)\n"
    "```\n\n"
    "Strictly follow this format and logic. Code must be production-ready and error-free."
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
            
            response = client.chat.completions.create(
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
        
        # Simple fallback code
        fallback_code = """from manim import *
import random
import numpy as np

class FallbackScene(Scene):
    def construct(self):
        # Simple fallback animation
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