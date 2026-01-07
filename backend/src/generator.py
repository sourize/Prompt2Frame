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
    "You are a STRICT Manim v0.17+ CODE GENERATOR.\n"
    "\n"
    "INPUT:\n"
    "- Valid JSON with `entities`, `intent_graph`, and `timeline`.\n"
    "\n"
    "OUTPUT:\n"
    "- EXACTLY ONE Python file.\n"
    "- EXACTLY ONE Scene: `class GeneratedScene(Scene):`\n"
    "- NO prose. NO markdown. NO explanations.\n"
    "\n"
    "====================================================\n"
    "ABSOLUTE RENDERING LAW (NON-NEGOTIABLE)\n"
    "====================================================\n"
    "\n"
    "🚨 YOU MAY CALL `self.play()` MULTIPLE TIMES to handle steps.\n"
    "\n"
    "- Use `Succession` or `AnimationGroup` where possible.\n"
    "- Keep clip count LOW (max 6).\n"
    "\n"
    "The ONLY exception is:\n"
    "- `self.wait(1)` at the very end.\n"
    "\n"
    "====================================================\n"
    "MANDATORY STRATEGY\n"
    "====================================================\n"
    "\n"
    "1. Parse `entities` to create Mobjects.\n"
    "2. Parse `timeline` to sequence animations.\n"
    "3. Use `intent_graph` for semantic context.\n"
    "\n"
    "ALL animations MUST be composed INSIDE ONE of:\n"
    "- `Succession(...)`\n"
    "- `AnimationGroup(...)`\n"
    "- Nested combinations of the above\n"
    "\n"
    "Then passed into ONE `self.play(...)`.\n"
    "\n"
    "====================================================\n"
    "FILE STRUCTURE (MANDATORY)\n"
    "====================================================\n"
    "\n"
    "1. File headers (first lines):\n"
    "from manim import *\n"
    "import numpy as np\n"
    "from manim import config\n"
    "\n"
    "2. Inject required helpers (unchanged, exactly once):\n"
    "- compute_bounding_box\n"
    "- bbox_intersects\n"
    "- bounce helpers (if already required by your system)\n"
    "\n"
    "3. Define:\n"
    "class GeneratedScene(Scene):\n"
    "    def construct(self):\n"
    "\n"
    "4. Define ALL objects first.\n"
    "5. Build ONE animation tree.\n"
    "6. Call `self.play(animation_tree)`\n"
    "7. Call `self.wait(1)`\n"
    "\n"
    "====================================================\n"
    "OBJECT RULES\n"
    "====================================================\n"
    "\n"
    "- Each object ID → ONE Python variable.\n"
    "- Transformations reuse identity.\n"
    "- NO duplicate shapes for morphing.\n"
    "\n"
    "Mapping:\n"
    "- circle → Circle()\n"
    "- square → Square()\n"
    "- text → Text(font_size >= 24)\n"
    "\n"
    "====================================================\n"
    "ANIMATION SEMANTICS\n"
    "====================================================\n"
    "\n"
    "### CREATE\n"
    "- Use `Create(obj)` or `Write(text)`\n"
    "- Must be INSIDE the animation tree.\n"
    "\n"
    "### TRANSFORM\n"
    "- Use `ReplacementTransform(old, new)`\n"
    "- Update reference: object = new\n"
    "- Must be INSIDE the animation tree.\n"
    "\n"
    "### MOVE / PATH\n"
    "- Use `MoveAlongPath` OR `.animate.move_to`\n"
    "- INSIDE the animation tree.\n"
    "\n"
    "### BOUNCE (CRITICAL)\n"
    "- ❌ NEVER use `Bounce()`\n"
    "- ❌ NEVER use multiple `self.play()`\n"
    "- Build bounce as a SEQUENCE of motions:\n"
    "\n"
    "Example structure:\n"
    "bounce_seq = Succession(\n"
    "    obj.animate.move_to(apex1),\n"
    "    obj.animate.move_to(contact1),\n"
    "    obj.animate.set_color(RED),\n"
    "    obj.animate.move_to(apex2),\n"
    "    obj.animate.move_to(contact2),\n"
    ")\n"
    "\n"
    "Then embed `bounce_seq` into the main timeline.\n"
    "\n"
    "====================================================\n"
    "TIMELINE CONSTRUCTION (REQUIRED)\n"
    "====================================================\n"
    "\n"
    "You MUST:\n"
    "\n"
    "1. Create a Python list: `timeline = []`\n"
    "2. Append animations to `timeline`\n"
    "3. Build:\n"
    "full_animation = Succession(*timeline)\n"
    "\n"
    "4. Execute:\n"
    "self.play(full_animation)\n"
    "\n"
    "🚫 You are FORBIDDEN from calling `self.play()` anywhere else.\n"
    "\n"
    "====================================================\n"
    "FORBIDDEN (HARD FAIL)\n"
    "====================================================\n"
    "\n"
    "- More than one `self.play(`\n"
    "- Bounce()\n"
    "- get_bounding_box\n"
    "- .bounding_box\n"
    "- Tex / MathTex\n"
    "- exec / eval / subprocess / os / sys\n"
    "\n"
    "====================================================\n"
    "QUALITY RULES\n"
    "====================================================\n"
    "\n"
    "- Prefer fewer, longer animations\n"
    "- No jitter\n"
    "- No micro-animations\n"
    "- Motion must be readable\n"
    "- Scene must look intentional at every frame\n"
    "\n"
    "====================================================\n"
    "FAILURE MODE\n"
    "====================================================\n"
    "\n"
    "If you cannot express the requested animation with ONE `self.play()`:\n"
    "- Emit Python that raises:\n"
    "raise RuntimeError(\"Cannot safely render animation in a single play call\")\n"
    "\n"
    "====================================================\n"
    "FINAL RULE\n"
    "====================================================\n"
    "\n"
    "If you output more than ONE `self.play()`,\n"
    "your output is INVALID.\n"
    "\n"
    "OUTPUT PYTHON CODE ONLY.\n"
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
        required_imports = ["from manim import *", "import numpy as np"]
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
        """Check for common Manim method usage issues and enforce strict constraints."""
        # Check for deprecated methods
        deprecated_methods = ["ShowCreation", "Write", "FadeInFrom"]
        for method in deprecated_methods:
            if method in code:
                logger.warning(f"Deprecated method '{method}' found in code")
        
        # Enforce ONE SCENE, but allow multiple self.play() calls (bounded by executor)
        play_count = code.count("self.play(")
        
        # Ensure animation calls exist (REQUIRED)
        if play_count == 0 and "self.wait(" not in code:
            raise RuntimeError("Generated code has no animations (missing self.play or self.wait).")
        
        # Check for potential memory issues
        if code.count("np.array") > 20:
            logger.warning("High number of numpy arrays created - potential memory issue")

SAFE_MANIM_HELPERS = """
# === SAFE MANIM HELPERS (INJECTED) ===
def get_safe_center(mobj):
    try:
        return mobj.get_center()
    except:
        return np.array([0, 0, 0])

def compute_bounding_box(mobj):
    \"\"\"
    Robust bounding box computation that works for any Manim mobject.
    Returns (left, right, bottom, top).
    \"\"\"
    try:
        # Try standard width/height first
        center = get_safe_center(mobj)
        width = mobj.width
        height = mobj.height
        return (
            center[0] - width/2,
            center[0] + width/2,
            center[1] - height/2,
            center[1] + height/2
        )
    except:
        # Fallback to points
        try:
            points = mobj.get_all_points()
            if len(points) == 0:
                raise ValueError("No points")
            xs = points[:, 0]
            ys = points[:, 1]
            return (np.min(xs), np.max(xs), np.min(ys), np.max(ys))
        except:
            # Absolute fallback
            return (-1, 1, -1, 1)

def bbox_intersects(bbox1, bbox2):
    \"\"\"Returns True if two bounding boxes intersect.\"\"\"
    l1, r1, b1, t1 = bbox1
    l2, r2, b2, t2 = bbox2
    return not (r1 < l2 or l1 > r2 or t1 < b2 or b1 > t2)
# =====================================
"""

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
    
    # Inject helpers after imports
    final_lines = []
    helpers_injected = False
    for line in lines:
        final_lines.append(line)
        if not helpers_injected and "import" in line and "manim" not in line:
            # Inject after the last import that isn't manim (heuristic)
            pass
    
    # Simpler injection: Just Find "from manim import *"
    processed_code = '\n'.join(lines)
    
    # Ensure numpy is imported for the helpers
    header_injection = "import numpy as np\nfrom manim import config\n" + SAFE_MANIM_HELPERS
    
    if "from manim import *" in processed_code:
        processed_code = processed_code.replace(
            "from manim import *", 
            "from manim import *\n" + header_injection
        )
    else:
        # Fallback: Prepend
        processed_code = "from manim import *\n" + header_injection + "\n" + processed_code

    return _fix_string_literals(processed_code)

def _fix_string_literals(code: str) -> str:
    """Fix common string literal issues in Manim code."""
    lines = code.split('\n')
    fixed_lines = []
    
    for line in lines:
        # Fix Text() calls with single quotes inside double quotes or vice versa
        # This is a simplified version of the robust legacy fixer
        
        # 1. Convert Text('...') to Text("...")
        if "Text('" in line and "')" in line:
            line = line.replace("Text('", 'Text("').replace("')", '")')
            
        # 2. Fix broken internal quotes if possible (e.g. Text("It"s time"))
        # This is hard to do perfectly with regex without destroying valid code
        # Ideally, the LLM should handle this, but we catch basic simple cases
        
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)

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
                    temperature=0.0,  # Deterministic generation
                    max_tokens=2500,
                    top_p=1.0,
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