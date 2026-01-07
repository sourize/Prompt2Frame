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

# Simplified AI generation prompt
AI_SYSTEM_PROMPT = """You are a Manim code expert. Generate VALID Manim v0.17+ Python code.

You will receive a technical specification describing an animation. Your job is to write working Python code using the Manim library.

CRITICAL RULES:
1. Output ONLY Python code (no markdown, no explanations)
2. Use class name: GeneratedScene(Scene) or GeneratedScene(ThreeDScene) for 3D
3. Import: from manim import *
4. Use standard Manim objects: Circle, Square, Line, Text, Arrow, etc.
5. Common animations: Create(), Write(), ReplacementTransform(), FadeIn(), FadeOut()
6. For motion: obj.animate.move_to(), MoveAlongPath()
7. For rotation: Rotate(obj, angle=..., about_point=...)
8. Use UP TO 6 self.play() calls
9. Always end with self.wait(1)
10. Ensure objects are VISIBLE (use colors like BLUE, RED, YELLOW, not BLACK)
11. Position objects within range: x=[-6,6], y=[-3,3]

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
    
    # Tier 1: Try template matching
    logger.info("Attempting template matching")
    template_code = match_template(technical_spec)
    
    # If matched a template (not fallback), return it
    if template_code != TEMPLATE_FALLBACK:
        logger.info("Template match found, using proven code")
        return template_code
    
    # Tier 2: Try AI generation for novel requests
    logger.info("No template match, trying AI generation")
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