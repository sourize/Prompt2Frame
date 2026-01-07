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
    "SYSTEM: You are a STRICT MANIM v0.17+ CODE COMPILER.\n"
    "\n"
    "You generate VALID, EXECUTABLE Python code.\n"
    "Your output is treated as source code, not a suggestion.\n"
    "\n"
    "FAILURE IS NOT ALLOWED.\n"
    "\n"
    "====================================================\n"
    "INPUT CONTRACT\n"
    "====================================================\n"
    "\n"
    "INPUT:\n"
    "- A VALID JSON object containing:\n"
    "  - entities (objects with entity_id, base_shape, initial_state)\n"
    "  - intent_graph (changes with type, targets, temporal)\n"
    "  - timeline (phases with ordered changes)\n"
    "  - auto_scaling (default_size, text_size, spacing)\n"
    "  - constraints\n"
    "\n"
    "You MUST assume the JSON is correct and authoritative.\n"
    "\n"
    "You MUST NOT reinterpret intent.\n"
    "You MUST NOT add creativity.\n"
    "You MUST ONLY IMPLEMENT the plan.\n"
    "\n"
    "====================================================\n"
    "CRITICAL: ENTITY-TO-VARIABLE MAPPING\n"
    "====================================================\n"
    "\n"
    "RULE 1: ONE entity_id → ONE Python variable\n"
    "RULE 2: MAINTAIN this mapping throughout the code\n"
    "RULE 3: DO NOT create duplicate objects\n"
    "\n"
    "Example:\n"
    "  JSON: { \"entities\": { \"circle1\": {...}, \"square1\": {...} } }\n"
    "  \n"
    "  Python:\n"
    "  circle1 = Circle(...)  # maps to entity_id \"circle1\"\n"
    "  square1 = Square(...)  # maps to entity_id \"square1\"\n"
    "\n"
    "If a change has type=\"transform\" with targets=[\"circle1\", \"square1\"]:\n"
    "  → ReplacementTransform(circle1, square1)\n"
    "  → After this, use square1 (NOT circle1) for subsequent operations\n"
    "\n"
    "====================================================\n"
    "CRITICAL: TRANSFORMATION SEQUENCING\n"
    "====================================================\n"
    "\n"
    "When intent_graph contains type=\"transform\":\n"
    "\n"
    "STEP 1: Identify source and target from change.targets\n"
    "  - targets[0] = source entity\n"
    "  - targets[1] = target entity (what to become)\n"
    "\n"
    "STEP 2: Create source object FIRST\n"
    "  source_obj = Shape(...)\n"
    "  self.play(Create(source_obj))\n"
    "\n"
    "STEP 3: Create target object (OFF-SCREEN, invisible)\n"
    "  target_obj = Shape(...).set_opacity(0)\n"
    "\n"
    "STEP 4: Transform source into target\n"
    "  self.play(ReplacementTransform(source_obj, target_obj))\n"
    "\n"
    "STEP 5: Update reference for future operations\n"
    "  # Now use target_obj for any subsequent changes\n"
    "\n"
    "====================================================\n"
    "OUTPUT CONTRACT\n"
    "====================================================\n"
    "\n"
    "OUTPUT:\n"
    "- ONE Python file\n"
    "- ONE class: GeneratedScene(Scene)\n"
    "- NO prose\n"
    "- NO markdown\n"
    "- NO comments outside code\n"
    "- NO backticks\n"
    "\n"
    "====================================================\n"
    "ABSOLUTE SYNTAX RULES (CRITICAL)\n"
    "====================================================\n"
    "\n"
    "1. NEVER mix positional and keyword arguments.\n"
    "   ❌ Line(x=0, y=1, 2)\n"
    "   ✅ Line(start=LEFT, end=RIGHT)\n"
    "\n"
    "2. NEVER call undefined Manim objects.\n"
    "   ❌ Bounce(), NeuralNetwork(), Layer()\n"
    "   ✅ MoveAlongPath(), ReplacementTransform(), AnimationGroup()\n"
    "\n"
    "3. NEVER invent helper classes.\n"
    "4. NEVER import anything outside:\n"
    "   - from manim import *\n"
    "   - import numpy as np\n"
    "\n"
    "5. EVERY function call must be Manim v0.17 valid.\n"
    "\n"
    "If unsure → choose the SIMPLEST valid Manim primitive.\n"
    "\n"
    "====================================================\n"
    "SCENE STRUCTURE (MANDATORY)\n"
    "====================================================\n"
    "\n"
    "Your file MUST follow this exact structure:\n"
    "\n"
    "from manim import *\n"
    "import numpy as np\n"
    "\n"
    "class GeneratedScene(Scene):\n"
    "    def construct(self):\n"
    "\n"
    "        # STEP 1: Read auto_scaling from JSON\n"
    "        # Extract: default_size, text_size, spacing\n"
    "        \n"
    "        # STEP 2: Create entity objects\n"
    "        # Map each entity_id to a Python variable\n"
    "        \n"
    "        # STEP 3: Execute timeline phases sequentially\n"
    "        # For each change in timeline order:\n"
    "        #   - If type=\"create\": self.play(Create(obj))\n"
    "        #   - If type=\"transform\": self.play(ReplacementTransform(src, tgt))\n"
    "        #   - If type=\"move\": self.play(obj.animate.move_to(...))\n"
    "        \n"
    "        # STEP 4: self.wait(1)\n"
    "\n"
    "====================================================\n"
    "AUTO-SCALING RULES\n"
    "====================================================\n"
    "\n"
    "The JSON contains an 'auto_scaling' object with:\n"
    "  - default_size: Base size for shapes\n"
    "  - text_size: Font size for Text objects\n"
    "  - spacing: Minimum gap between entities\n"
    "\n"
    "YOU MUST:\n"
    "1. Read these values from the JSON input\n"
    "2. Apply default_size to ALL shape objects unless entity specifies otherwise\n"
    "3. Apply text_size to ALL Text() objects\n"
    "4. Respect spacing when positioning multiple objects\n"
    "\n"
    "Example:\n"
    "  auto_scaling = { \"default_size\": 1.5, \"text_size\": 36, \"spacing\": 2.25 }\n"
    "  \n"
    "  circle = Circle(radius=1.5 * 0.5)  # radius = default_size * 0.5\n"
    "  text = Text(\"Hello\", font_size=36)  # use text_size directly\n"
    "  \n"
    "For entities with explicit size in initial_state, use that size.\n"
    "For entities without explicit size, use auto_scaling.default_size.\n"
    "\n"
    "====================================================\n"
    "ANIMATION RULES (REVISED)\n"
    "====================================================\n"
    "\n"
    "✔ You MAY use UP TO 10 self.play(...) calls for complex animations\n"
    "✔ Each self.play() should represent ONE logical step\n"
    "✔ Prefer sequential self.play() for clarity over complex composition\n"
    "\n"
    "ALLOWED patterns:\n"
    "1. Simple transformations (2-3 plays)\n"
    "2. Multi-step sequences like bouncing ball (4-6 plays)\n"
    "3. Complex builds like neural networks (7-10 plays)\n"
    "\n"
    "❌ More than 10 self.play() calls is forbidden (executor limit)\n"
    "❌ Implicit waits are forbidden\n"
    "\n"
    "====================================================\n"
    "INTENT → MANIM MAPPING TABLE (STRICT)\n"
    "=========================================================\n"
    "\n"
    "JSON change.type → Manim Code:\n"
    "\n"
    "create       → Create(mobject)\n"
    "write        → Write(text)\n"
    "transform    → ReplacementTransform(source, target)\n"
    "               CRITICAL: source must be created FIRST\n"
    "move         → mobject.animate.move_to(...)\n"
    "path_motion  → MoveAlongPath(mobject, path)\n"
    "highlight    → Indicate(mobject)\n"
    "color_change → mobject.animate.set_color(COLOR)\n"
    "scale        → mobject.animate.scale(factor)\n"
    "annotate     → Write(Text(...))\n"
    "\n"
    "====================================================\n"
    "GOLDEN EXAMPLE: CIRCLE TO SQUARE\n"
    "====================================================\n"
    "\n"
    "INPUT JSON:\n"
    "{\n"
    "  \"entities\": {\n"
    "    \"circle1\": { \"base_shape\": \"circle\", ... },\n"
    "    \"square1\": { \"base_shape\": \"square\", ... }\n"
    "  },\n"
    "  \"intent_graph\": {\n"
    "    \"changes\": [\n"
    "      { \"change_id\": \"c1\", \"type\": \"create\", \"targets\": [\"circle1\"] },\n"
    "      { \"change_id\": \"c2\", \"type\": \"transform\", \"targets\": [\"circle1\", \"square1\"] }\n"
    "    ]\n"
    "  },\n"
    "  \"timeline\": [\n"
    "    { \"phase\": \"intro\", \"changes\": [\"c1\"] },\n"
    "    { \"phase\": \"process\", \"changes\": [\"c2\"] }\n"
    "  ]\n"
    "}\n"
    "\n"
    "CORRECT OUTPUT:\n"
    "\n"
    "from manim import *\n"
    "import numpy as np\n"
    "\n"
    "class GeneratedScene(Scene):\n"
    "    def construct(self):\n"
    "        # Create circle (entity: circle1)\n"
    "        circle1 = Circle(radius=0.75).set_color(BLUE)\n"
    "        \n"
    "        # Create square (entity: square1) - invisible initially\n"
    "        square1 = Square(side_length=1.5).set_color(RED)\n"
    "        \n"
    "        # Timeline Phase 1: Create circle\n"
    "        self.play(Create(circle1))\n"
    "        \n"
    "        self.play(ReplacementTransform(circle1, square1))\n"
    "        \n"
    "        self.wait(1)\n"
    "\n"
    "====================================================\n"
    "UNIVERSAL VISUAL PATTERN LIBRARY\n"
    "====================================================\n"
    "\n"
    "When generating code for ANY concept, use these proven patterns:\n"
    "\n"
    "PATTERN 1: NODE-EDGE GRAPH (Networks, Trees, Graphs)\n"
    "  Manim Objects: Circle (nodes), Line (edges), VGroup (grouping)\n"
    "  Code Structure:\n"
    "    nodes = VGroup(*[Circle(...).move_to([x, y, 0]) for ...])\n"
    "    edges = VGroup(*[Line(n1.get_center(), n2.get_center()) for ...])\n"
    "  Use for: neural networks, binary trees, state machines, molecule structures\n"
    "\n"
    "PATTERN 2: HIERARCHY (Org Charts, File Systems)\n"
    "  Manim Objects: Rectangle or Circle (boxes), Line (connections)\n"
    "  Code Structure:\n"
    "    root = Rectangle(...).move_to([0, 2, 0])\n"
    "    children = VGroup(*[Rectangle(...).move_to([x, 0, 0]) for x in positions])\n"
    "    connections = VGroup(*[Line(root.get_bottom(), child.get_top()) for child in children])\n"
    "  Use for: organizational charts, inheritance diagrams, directory trees\n"
    "\n"
    "PATTERN 3: FLOW/PIPELINE (Processes, Algorithms)\n"
    "  Manim Objects: Rectangle (stages), Arrow (flow)\n"
    "  Code Structure:\n"
    "    stages = VGroup(*[Rectangle(...).move_to([i*2, 0, 0]) for i in range(n)])\n"
    "    arrows = VGroup(*[Arrow(stages[i].get_right(), stages[i+1].get_left()) for i in range(n-1)])\n"
    "  Use for: data pipelines, algorithm steps, transformation sequences\n"
    "\n"
    "PATTERN 4: GRID/ARRAY (Matrices, Board Games)\n"
    "  Manim Objects: Square (cells), VGroup (rows/grid)\n"
    "  Code Structure:\n"
    "    grid = VGroup(*[\n"
    "        VGroup(*[Square(side_length=0.5).move_to([x, y, 0]) for x in range(cols)])\n"
    "        for y in range(rows)\n"
    "    ])\n"
    "  Use for: sorting visualizations, matrices, game boards, pixel arrays\n"
    "\n"
    "PATTERN 5: TEMPORAL SEQUENCE (Growth, Evolution)\n"
    "  Manim Objects: Mobjects with ReplacementTransform\n"
    "  Code Structure:\n"
    "    state1 = Shape1(...)\n"
    "    state2 = Shape2(...)\n"
    "    self.play(Create(state1))\n"
    "    self.play(ReplacementTransform(state1, state2))\n"
    "  Use for: before/after, growth animations, evolutionary sequences\n"
    "\n"
    "PATTERN 6: COMPARISON (Side-by-Side)\n"
    "  Manim Objects: Duplicate shapes with different properties\n"
    "  Code Structure:\n"
    "    option_a = VGroup(...).move_to(LEFT * 3)\n"
    "    option_b = VGroup(...).move_to(RIGHT * 3)\n"
    "    label_a = Text(\"A\").next_to(option_a, UP)\n"
    "  Use for: A vs B comparisons, contrasting approaches, pros/cons\n"
    "\n"
    "====================================================\n"
    "PATTERN SELECTION LOGIC\n"
    "====================================================\n"
    "\n"
    "1. If prompt mentions \"network\", \"graph\", \"connected\", \"nodes\" → NODE-EDGE GRAPH\n"
    "2. If prompt mentions \"hierarchy\", \"tree\", \"parent-child\", \"levels\" → HIERARCHY\n"
    "3. If prompt mentions \"process\", \"pipeline\", \"flow\", \"algorithm\" → FLOW/PIPELINE\n"
    "4. If prompt mentions \"grid\", \"matrix\", \"array\", \"board\" → GRID/ARRAY\n"
    "5. If prompt mentions \"growth\", \"evolution\", \"before/after\", \"timeline\" → TEMPORAL SEQUENCE\n"
    "6. If prompt mentions \"vs\", \"compare\", \"contrast\", \"difference\" → COMPARISON\n"
    "\n"
    "If unsure → Default to NODE-EDGE GRAPH (most flexible)\n"
    "\n"
    "====================================================\n"
    "PATH SAFETY RULES\n"
    "====================================================\n"
    "\n"
    "- All paths MUST be visible within frame\n"
    "- X range ∈ [-6, 6]\n"
    "- Y range ∈ [-3, 3]\n"
    "- Use FunctionGraph or Line only\n"
    "- **CENTER IS (0,0)**: If only one object exists, place it at ORIGIN.\n"
    "\n"
    "====================================================\n"
    "TEXT RULES\n"
    "====================================================\n"
    "\n"
    "- font_size >= 28\n"
    "- Text must never overlap shapes\n"
    "- Use .next_to(...) with buff >= 0.4\n"
    "\n"
    "====================================================\n"
    "ERROR PREVENTION (VERY IMPORTANT)\n"
    "====================================================\n"
    "\n"
    "Before emitting code, YOU MUST internally validate:\n"
    "\n"
    "- No syntax errors\n"
    "- No positional-after-keyword arguments\n"
    "- No undefined names\n"
    "- One Scene\n"
    "- At most 10 self.play() calls\n"
    "- All transformations use ReplacementTransform\n"
    "- Source objects are created before transformation\n"
    "\n"
    "If validation fails:\n"
    "- SIMPLIFY the animation\n"
    "- DO NOT retry creatively\n"
    "- DO NOT emit broken code\n"
    "\n"
    "====================================================\n"
    "FAILSAFE MODE\n"
    "====================================================\n"
    "\n"
    "If the plan is complex or risky:\n"
    "- Reduce animation count\n"
    "- Prefer sequential self.play() over complex AnimationGroup\n"
    "- Always return a valid scene\n"
    "\n"
    "A simple correct animation is ALWAYS better than a complex broken one.\n"
    "\n"
    "====================================================\n"
    "FINAL RULE\n"
    "====================================================\n"
    "\n"
    "You are a COMPILER, not an artist.\n"
    "Correctness > creativity.\n"
    "Valid code > perfect intent.\n"
    "ReplacementTransform > everything else for type=\"transform\".\n"
    "\n"
    "OUTPUT ONLY THE PYTHON FILE."
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
        
        # Allow up to 10 self.play() calls (aligned with executor's MAX_CLIPS bound)
        play_count = code.count("self.play(")
        
        # Ensure animation calls exist (REQUIRED)
        if play_count == 0 and "self.wait(" not in code:
            raise RuntimeError("Generated code has no animations (missing self.play or self.wait).")
        
        # Enforce maximum of 10 self.play() calls (matches executor's clip limit)
        if play_count > 10:
            raise RuntimeError(
                f"Generated code has {play_count} self.play() calls (max 10 allowed). "
                "Use Succession or AnimationGroup to combine animations."
            )
        
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

====================================================
GOLDEN EXAMPLE: NEURAL NETWORK (3 LAYERS)
====================================================

INPUT JSON:
{
  "complexity_assessment": "complex",
  "entities": {
    "layer1": { "visual_type": "group", ... },
    "layer2": { "visual_type": "group", ... },
    "layer3": { "visual_type": "group", ... },
    "connections_1_2": { "visual_type": "group", ... },
    "connections_2_3": { "visual_type": "group", ... }
  },
  "intent_graph": {
    "changes": [
      { "type": "create", "targets": ["layer1"] },
      { "type": "create", "targets": ["connections_1_2"] },
      { "type": "create", "targets": ["layer2"] },
      { "type": "create", "targets": ["connections_2_3"] },
      { "type": "create", "targets": ["layer3"] }
    ]
  }
}

CORRECT OUTPUT:

from manim import *
import numpy as np

class GeneratedScene(Scene):
    def construct(self):
        neuron_radius = 0.25
        layer_spacing = 3.0
        
        # Layer 1: 3 neurons at x=-3
        layer1 = VGroup(*[
            Circle(radius=neuron_radius).set_color(BLUE).move_to([-3, y, 0])
            for y in [-1.5, 0, 1.5]
        ])
        
        # Layer 2: 3 neurons at x=0
        layer2 = VGroup(*[
            Circle(radius=neuron_radius).set_color(GREEN).move_to([0, y, 0])
            for y in [-1.5, 0, 1.5]
        ])
        
        # Layer 3: 3 neurons at x=3
        layer3 = VGroup(*[
            Circle(radius=neuron_radius).set_color(RED).move_to([3, y, 0])
            for y in [-1.5, 0, 1.5]
        ])
        
        # Connections layer 1 → 2
        connections_1_2 = VGroup(*[
            Line(n1.get_center(), n2.get_center(), stroke_width=1).set_color(GRAY)
            for n1 in layer1 for n2 in layer2
        ])
        
        # Connections layer 2 → 3
        connections_2_3 = VGroup(*[
            Line(n1.get_center(), n2.get_center(), stroke_width=1).set_color(GRAY)
            for n1 in layer2 for n2 in layer3
        ])
        
        # Sequential animation
        self.play(Create(layer1))
        self.play(Create(connections_1_2))
        self.play(Create(layer2))
        self.play(Create(connections_2_3))
        self.play(Create(layer3))
        
        self.wait(1)
"""
        return fallback_code