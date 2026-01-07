"""
Simplified Generator - Converts technical specifications to Manim code.

Uses template-first approach: tries to match keywords to proven templates,
falls back to AI generation if no match, and has a guaranteed fallback.
"""

import os
import logging
import re
from typing import Optional
from groq import Groq

from .templates import match_template, TEMPLATE_FALLBACK

logger = logging.getLogger(__name__)

# Initialize Groq client
MODEL_NAME = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Enhanced AI generation prompt with template awareness
AI_SYSTEM_PROMPT = """You are a Manim code expert. Generate VALID Manim v0.17+ Python code based on technical specifications.

You will receive a detailed technical specification describing an animation. Your job is to write working Python code using the Manim library that matches this specification as closely as possible.

TEMPLATE PATTERNS YOU SHOULD KNOW:
Our system has proven templates for common patterns. When the spec matches these, you can adapt the pattern:

1. **Point Plotting**: For coordinates like (0,2), (2,0), (4,2)
   - Extract the coordinate pairs
   - Calculate appropriate axis ranges to fit all points
   - Use `axes.c2p(x, y)` to convert coordinates to scene positions
   - Create Dot objects at each coordinate
   - Add labels showing the coordinates

2. **Transformations**: For "X to Y" patterns
   - Create both source and target shapes
   - Use Create() for source
   - Use ReplacementTransform(source, target) for morphing

3. **Networks/Graphs**: For multi-node structures
   - Use VGroup with list comprehensions: `VGroup(*[Circle(...) for ...])`
   - Position nodes at specific coordinates
   - Connect with Lines using nested loops: `for n1 in layer1 for n2 in layer2`

4. **Motion**: For bouncing, moving, sliding
   - Create path with ArcBetweenPoints or Line
   - Use MoveAlongPath(object, path)

CRITICAL RULES:
1. Output ONLY Python code (no markdown, no explanations)
2. Use class name: GeneratedScene(Scene) or GeneratedScene(ThreeDScene) for 3D
3. Import: from manim import *
4. Use standard Manim objects: Circle, Square, Line, Text, Dot, Arrow, Axes, etc.
5. Common animations: Create(), Write(), ReplacementTransform(), FadeIn(), FadeOut()
6. For motion: obj.animate.move_to(), MoveAlongPath()
7. For rotation: Rotate(obj, angle=..., about_point=...)
8. Use UP TO 6 self.play() calls
9. Always end with self.wait(1)
10. Ensure objects are VISIBLE (use colors like BLUE, RED, YELLOW, GREEN, not BLACK)
11. Position objects within range: x=[-6,6], y=[-3,3]
12. Extract specific parameters from the technical spec (coordinates, colors, sizes, counts)

CUSTOMIZATION INSTRUCTIONS:
- If the spec mentions specific coordinates, USE THEM EXACTLY
- If the spec mentions specific colors, USE THEM
- If the spec mentions specific sizes/radii, USE THEM
- If the spec mentions counts (e.g., "3 circles"), CREATE THAT MANY
- Adapt the closest template pattern to match the specific requirements

DO NOT use undefined objects or custom classes.
DO NOT mix positional and keyword arguments.
Output pure Python code only."""


def extract_code_from_response(text: str) -> str:
    """Extract Python code from LLM response, handling markdown code blocks."""
    if not text:
        return ""
    
    # Try to extract from markdown code block
    pattern = r"```(?:python)?\n([\s\S]*?)```"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    # Return as-is if no code block found
    return text.strip()


def generate_with_ai(technical_spec: str, max_retries: int = 2) -> Optional[str]:
    """
    Generate Manim code using AI based on technical specification.
    
    Args:
        technical_spec: Plain text technical specification
        max_retries: Maximum retry attempts
        
    Returns:
        Generated Manim code or None if generation fails
    """
    logger.info("Attempting AI code generation")
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"AI generation attempt {attempt}/{max_retries}")
            
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": AI_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Technical Specification:\n\n{technical_spec}\n\nGenerate Manim code:"}
                ],
                temperature=0.2,  # Low temperature for consistent code
                max_tokens=1500,
            )
            
            if not response or not response.choices:
                logger.warning(f"AI attempt {attempt}: Empty response")
                continue
            
            code = extract_code_from_response(response.choices[0].message.content)
            
            if not code or len(code) < 50:  # Basic sanity check
                logger.warning(f"AI attempt {attempt}: Code too short or empty")
                continue
            
            # Basic validation: check for required elements
            if "class GeneratedScene" in code and "def construct" in code:
                logger.info(f"AI code generation successful ({len(code)} characters)")
                return code
            else:
                logger.warning(f"AI attempt {attempt}: Missing required class or method")
                continue
                
        except Exception as e:
            logger.error(f"AI attempt {attempt} failed: {e}")
            if attempt == max_retries:
                return None
            continue
    
    return None


def validate_code_basic(code: str) -> bool:
    """
    Basic validation of generated code.
    
    Args:
        code: Generated Manim code
        
    Returns:
        True if code passes basic validation
    """
    if not code or len(code) < 50:
        return False
    
    # Check for required elements
    required = [
        "from manim import",
        "class GeneratedScene",
        "def construct",
        "self.play",
        "self.wait"
    ]
    
    return all(req in code for req in required)


def generate_code(technical_spec: str) -> str:
    """
    Generate Manim code from technical specification.
    
    Uses three-tier approach:
    1. Template matching (fastest, most reliable)
    2. AI generation (flexible, for novel requests)
    3. Fallback template (guaranteed to work)
    
    Args:
        technical_spec: Plain text technical specification from prompt_expander
        
    Returns:
        Working Manim Python code
    """
    logger.info("Starting code generation")
    
    # Check if request has enhanced requirements that templates can't handle
    spec_lower = technical_spec.lower()
    enhanced_keywords = [
        'line through', 'connect', 'draw a line', 'add a line',
        'show trajectory', 'fit a curve', 'regression',
        'and also', 'as well as', 'additionally', 'plus'
    ]
    
    has_enhanced_requirements = any(keyword in spec_lower for keyword in enhanced_keywords)
    
    # Tier 1: Try template matching (only if no enhanced requirements)
    if not has_enhanced_requirements:
        logger.info("Attempting template matching")
        template_code = match_template(technical_spec)
        
        # If matched a template (not fallback), return it
        if template_code != TEMPLATE_FALLBACK:
            logger.info("Template match found, using proven code")
            return template_code
    else:
        logger.info("Enhanced requirements detected, skipping templates and using AI")
    
    # Tier 2: Try AI generation for novel/enhanced requests
    logger.info("No template match or enhanced request, trying AI generation")
    ai_code = generate_with_ai(technical_spec)
    
    if ai_code and validate_code_basic(ai_code):
        logger.info("AI generation successful")
        return ai_code
    
    # Tier 3: Use fallback template (guaranteed to work)
    logger.warning("AI generation failed, using fallback template")
    return TEMPLATE_FALLBACK


def generate_code_with_retries(technical_spec: str, max_attempts: int = 2) -> str:
    """
    Generate code with retry logic.
    
    Args:
        technical_spec: Technical specification
        max_attempts: Maximum generation attempts
        
    Returns:
        Generated Manim code
    """
    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(f"Code generation attempt {attempt}/{max_attempts}")
            code = generate_code(technical_spec)
            
            if validate_code_basic(code):
                return code
            else:
                logger.warning(f"Attempt {attempt}: Validation failed")
                continue
                
        except Exception as e:
            logger.error(f"Attempt {attempt} error: {e}")
            if attempt == max_attempts:
                logger.error("All attempts failed, returning fallback")
                return TEMPLATE_FALLBACK
            continue
    
    return TEMPLATE_FALLBACK