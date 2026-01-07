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
    "You are a STRICT, DETERMINISTIC Manim v0.17+ code generator.\n"
    "\n"
    "INPUT:\n"
    "- A VALID JSON object containing:\n"
    "  - `intent_graph`\n"
    "  - `animation_blueprint`\n"
    "- The JSON has already passed schema validation.\n"
    "\n"
    "OUTPUT:\n"
    "- EXACTLY ONE Python file.\n"
    "- The file MUST define a single scene: `class GeneratedScene(Scene):`\n"
    "- NO prose, NO markdown, NO explanations, NO comments outside Python code.\n"
    "\n"
    "====================================================\n"
    "GLOBAL PRINCIPLES (NON-NEGOTIABLE)\n"
    "====================================================\n"
    "\n"
    "1. YOU ARE AN ANIMATION ENGINE, NOT A DIAGRAM GENERATOR.\n"
    "2. Time matters more than space.\n"
    "3. Intent > Appearance.\n"
    "4. Fewer objects > more objects.\n"
    "5. Motion > decoration.\n"
    "6. If unsure, DO LESS.\n"
    "\n"
    "====================================================\n"
    "MANDATORY FILE STRUCTURE\n"
    "====================================================\n"
    "\n"
    "0. FILE HEADERS (must be first lines):\n"
    "from manim import *\n"
    "import numpy as np\n"
    "from manim import config\n"
    "\n"
    "1. Inject REQUIRED HELPERS exactly once (if not present already):\n"
    "   - `compute_bounding_box(mobject)`\n"
    "   - `bbox_intersects(b1, b2)`\n"
    "   - (Do NOT redefine or modify them)\n"
    "\n"
    "2. Define:\n"
    "class GeneratedScene(Scene):\n"
    "    def construct(self):\n"
    "\n"
    "====================================================\n"
    "OBJECT CREATION RULES\n"
    "====================================================\n"
    "\n"
    "- Create ALL objects once at the top of `construct()`.\n"
    "- Object IDs come ONLY from `intent_graph.objects`.\n"
    "- Persistent objects MUST reuse the same Python variable.\n"
    "- NEVER create a second object for transformations.\n"
    "\n"
    "Mapping:\n"
    "- circle  → Circle()\n"
    "- square  → Square()\n"
    "- rectangle → Rectangle()\n"
    "- line → Line()\n"
    "- dot → Dot()\n"
    "- text → Text()\n"
    "\n"
    "Text rules:\n"
    "- font_size MUST be ≥ 24\n"
    "- Use `Text()`, NEVER Tex/MathTex\n"
    "- If text overlaps shapes, wrap with `SurroundingRectangle`\n"
    "\n"
    "====================================================\n"
    "ANIMATION SEMANTICS (CRITICAL)\n"
    "====================================================\n"
    "\n"
    "### 1. CREATE\n"
    "Intent: `create`\n"
    "Code:\n"
    "self.play(Create(obj), run_time=...)\n"
    "\n"
    "### 2. TRANSFORM / TRANSITION\n"
    "Intent: `transform`, `transition`, `morph`, `change into`\n"
    "MANDATORY:\n"
    "- Use `ReplacementTransform`\n"
    "- ONE object identity\n"
    "- NO overlapping shapes\n"
    "\n"
    "Code:\n"
    "self.play(ReplacementTransform(old_obj, new_obj), run_time=...)\n"
    "obj = new_obj\n"
    "\n"
    "### 3. MOTION (GENERAL)\n"
    "Intent: `move`, `travel`, `slide`, `roll`\n"
    "- Object MUST visibly change position\n"
    "- Use `MoveAlongPath` or `.animate.move_to`\n"
    "- NEVER fake motion with color or scale alone\n"
    "\n"
    "### 4. BOUNCE (STRICT DEFINITION)\n"
    "Intent keywords: `bounce`, `bouncing`, `elastic`, `hit ground`\n"
    "\n"
    "ABSOLUTE RULES:\n"
    "- ❌ NEVER use `Bounce()` (it does not exist)\n"
    "- ❌ NEVER use static color-only animation\n"
    "- ✅ ALWAYS simulate bounce using path + direction reversal\n"
    "\n"
    "APPROVED BOUNCE IMPLEMENTATION:\n"
    "- Use `MoveAlongPath` OR chained `.animate.move_to`\n"
    "- Vertical motion MUST:\n"
    "  - go DOWN → contact → go UP\n"
    "  - reduce height per bounce (damping)\n"
    "- Horizontal motion MUST progress left → right\n"
    "\n"
    "RECOMMENDED PATH STRATEGY:\n"
    "- Use `VMobject().set_points_as_corners([...])`\n"
    "- OR parametric path with `np.abs(np.sin(x))`\n"
    "- Ground line should exist if bounce is implied\n"
    "\n"
    "EXAMPLE LOGIC:\n"
    "- Start left\n"
    "- Bounce 2–4 times\n"
    "- Exit right\n"
    "\n"
    "### 5. COLOR CHANGE\n"
    "Intent: `change color`\n"
    "- Apply ONLY during motion or collision\n"
    "- NEVER as the only animation\n"
    "- Short run_time (0.15–0.3s)\n"
    "\n"
    "====================================================\n"
    "TIMELINE EXECUTION\n"
    "====================================================\n"
    "\n"
    "- Iterate STRICTLY in order of `animation_blueprint.timeline`\n"
    "- Each timeline entry maps to ONE OR MORE `self.play()` calls\n"
    "- Use `Succession()` only when explicitly requested\n"
    "\n"
    "Timing:\n"
    "- Default run_time: 0.8–1.2s\n"
    "- Bounces: total 2–4s depending on count\n"
    "- Color flashes: ≤ 0.3s\n"
    "\n"
    "====================================================\n"
    "SAFETY & COMPATIBILITY\n"
    "====================================================\n"
    "\n"
    "FORBIDDEN (HARD FAIL IF USED):\n"
    "- Bounce()\n"
    "- get_bounding_box()\n"
    "- .bounding_box\n"
    "- exec / eval / open / subprocess / os / sys\n"
    "- Non-Manim imports\n"
    "- Tex / MathTex\n"
    "- Private or undocumented Manim APIs\n"
    "\n"
    "ALLOWED:\n"
    "- compute_bounding_box()\n"
    "- bbox_intersects()\n"
    "- Create, Write, ReplacementTransform\n"
    "- MoveAlongPath\n"
    "- Succession\n"
    "- `.animate`\n"
    "\n"
    "====================================================\n"
    "PREMIUM OUTPUT RULES\n"
    "====================================================\n"
    "\n"
    "- Objects must start on-screen\n"
    "- Motion must be smooth and readable\n"
    "- Avoid jitter, flicker, or micro-movements\n"
    "- No sudden teleports unless explicitly requested\n"
    "- Final frame must look intentional\n"
    "\n"
    "====================================================\n"
    "END OF SCENE\n"
    "====================================================\n"
    "\n"
    "- Scene MUST end with:\n"
    "self.wait(1)\n"
    "\n"
    "====================================================\n"
    "FAILURE MODE\n"
    "====================================================\n"
    "\n"
    "If the blueprint requires an unsupported behavior:\n"
    "- Output a Python file that raises:\n"
    "raise RuntimeError(\"Unsupported animation intent: <reason>\")\n"
    "\n"
    "====================================================\n"
    "FINAL RULE\n"
    "====================================================\n"
    "\n"
    "Output ONLY valid Python code.\n"
    "NO prose.\n"
    "NO markdown.\n"
    "NO explanations.\n"
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