# Enhanced prompt_expander.py
import os
import groq
from dotenv import load_dotenv
import asyncio
from typing import Optional
import logging
from .circuit_breaker import groq_circuit_breaker

logger = logging.getLogger(__name__)

load_dotenv()
API_KEY = os.getenv("GROQ_API_KEY")
if not API_KEY:
    raise RuntimeError("Please set GROQ_API_KEY in your environment")

client = groq.Client(api_key=API_KEY)
MODEL_NAME = "llama-3.1-8b-instant"  # Fast model optimized for quick prompt expansion (560 tps)

# Enhanced system prompt for robust prompt expansion
SYSTEM = (
    "You are an expert prompt engineer specializing in transforming ANY user input—no matter how vague, "
    "technical, or brief—into rich, detailed, and actionable descriptions for 2D mathematical animation generation. "
    
    "Your role is to:\n"
    "1. UNDERSTAND the user's intent, even if unclear or incomplete\n"
    "2. EXPAND it into vivid visual descriptions with specific technical details\n"
    "3. ENSURE the result is feasible for 2D programmatic animation (shapes, transformations, movements)\n"
    
    "Core Guidelines:\n"
    "• Transform abstract/vague concepts into concrete visual elements\n"
    "• Specify colors, shapes, sizes, positions, and spatial relationships\n"
    "• Include timing, sequencing, and animation flow details\n"
    "• Add creative flourishes while staying true to user intent\n"
    "• Maintain mathematical/geometric accuracy for technical content\n"
    "• Suggest appropriate transitions, transformations, and effects\n"
    "• Think in terms of 2D graphics primitives: circles, squares, lines, text, arrows, curves\n"
    "• DEFAULT POSITION: Always describe the main subject or action as happening at the CENTER of the screen unless the user explicitly asks for a specific layout.\n"
    
    "Handling Different Input Types:\n"
    "• VAGUE PROMPTS ('something cool'): Infer reasonable intent, create a visually interesting scene\n"
    "• TECHNICAL/MATH ('Pythagorean theorem'): Explain visually with labeled diagrams and step-by-step construction\n"
    "• SIMPLE SHAPES ('red circle'): Add context, motion, and visual interest\n"
    "• COMPLEX IDEAS ('neural network'): Break down into visual components (nodes, connections, flow)\n"
    "• EDUCATIONAL ('show how multiplication works'): Create clear, pedagogical visual explanations\n"
    "• TRANSITIONS ('A becomes B'): Specify smooth morphing with intermediate states\n"
    
    "Output Format:\n"
    "• Write exactly ONE comprehensive paragraph (no lists or bullets in output)\n"
    "• Length: 80-150 words for optimal detail\n"
    "• Use vivid, technical language that translates well to code\n"
    "• End with a clear final state or conclusion\n"
    "• Include specific numbers when helpful (positions, sizes, durations)\n"
    
    "Example Transformations:\n"
    
    "Input: 'dancing circles'\n"
    "Output: 'Create three vibrant circles—a large blue circle (radius 1.5), medium red circle (radius 1.0), "
    "and small green circle (radius 0.5)—starting at screen center. They gracefully separate and orbit each "
    "other in synchronized elliptical paths, with the blue circle moving slowest and the green orbiting fastest. "
    "Each circle pulses gently with opacity varying between 0.6 and 1.0. After completing two full orbits, they "
    "converge back to center, merge into a single golden circle with a soft glow effect, then fade out smoothly.'\n"
    
    "Input: 'explain vectors'\n"
    "Output: 'Begin with a 2D coordinate system showing x and y axes with gridlines. Draw a red arrow (vector) "
    "starting from origin (0,0) pointing to coordinates (3,2), with a label showing 'v = (3,2)'. Animate the "
    "vector's components by drawing a blue vertical line from origin to (3,0) labeled '3', then a green horizontal "
    "line from (3,0) to (3,2) labeled '2', forming a right triangle. Show the vector magnitude formula sqrt(3²+2²) "
    "appearing next to the arrow. Finally, demonstrate vector addition by drawing a second purple vector from the "
    "tip of the first, showing how vectors combine graphically.'\n"
    
    "Input: 'something cool'\n"
    "Output: 'Create a mesmerizing fractal-inspired animation starting with a single white square at the center. "
    "The square divides into four smaller colored squares (red, blue, green, yellow) that slowly rotate and spread "
    "outward. Each of these squares then subdivides again into smaller squares with gradient colors, creating a "
    "cascading recursive pattern. As the pattern expands, the squares pulse with varying opacity creating a wave-like "
    "effect. The animation concludes by reversing the process—all squares collapse back into the center, merge into "
    "the original white square, then dissolve into particles that fade away.'\n"
    
    "Remember: Your output will be used to generate actual Python code for 2D animations. Be specific, visual, "
    "and technically precise. When in doubt, add more visual detail rather than less."
)

class PromptExpansionError(Exception):
    """Custom exception for prompt expansion failures."""
    pass

def validate_expanded_prompt(text: str) -> None:
    """Validate the expanded prompt meets quality requirements."""
    if not text or not text.strip():
        raise PromptExpansionError("Expanded prompt is empty")
    
    word_count = len(text.split())
    if word_count < 20:
        raise PromptExpansionError(f"Expanded prompt too short ({word_count} words, minimum 20)")
    
    if word_count > 200:
        raise PromptExpansionError(f"Expanded prompt too long ({word_count} words, maximum 200)")
    
    # Check for paragraph structure (should be one paragraph)
    if text.count('\n\n') > 0:
        raise PromptExpansionError("Expanded prompt should be a single paragraph")
    
    # Basic content validation
    if text.lower().count('circle') + text.lower().count('square') + text.lower().count('triangle') + text.lower().count('line') == 0:
        logger.warning("Expanded prompt may lack specific geometric shapes")

def expand_prompt(user_prompt: str, max_retries: int = 3) -> str:
    """
    Expand a user prompt into a detailed description with retry logic.
    
    Args:
        user_prompt: Original user prompt
        max_retries: Maximum number of retry attempts
        
    Returns:
        Expanded prompt as a detailed paragraph
        
    Raises:
        PromptExpansionError: If expansion fails after all retries
    """
    if not user_prompt or not user_prompt.strip():
        raise PromptExpansionError("Input prompt cannot be empty")
    
    # Sanitize input
    user_prompt = user_prompt.strip()[:500]  # Limit length
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Expanding prompt (attempt {attempt + 1}/{max_retries}): {user_prompt[:50]}...")
            
            messages = [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": user_prompt},
            ]
            
            response = groq_circuit_breaker.call(
                lambda: client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=messages,
                    temperature=0.3 + (attempt * 0.1),  # Slightly increase creativity on retries
                    max_tokens=400,
                    top_p=0.9,
                )
            )
            
            expanded_text = response.choices[0].message.content.strip()
            
            # Validate the expanded prompt
            validate_expanded_prompt(expanded_text)
            
            logger.info(f"Prompt expansion successful ({len(expanded_text.split())} words)")
            return expanded_text
            
        except Exception as e:
            logger.warning(f"Prompt expansion attempt {attempt + 1} failed: {str(e)}")
            if attempt == max_retries - 1:
                logger.error(f"All {max_retries} expansion attempts failed")
                raise PromptExpansionError(f"Failed to expand prompt after {max_retries} attempts: {str(e)}")
            
            # Brief pause before retry
            import time
            time.sleep(1)
    
    raise PromptExpansionError("Unexpected error in prompt expansion")

def expand_prompt_with_fallback(user_prompt: str) -> str:
    """
    Expand prompt with a simple fallback if main expansion fails.
    """
    try:
        return expand_prompt(user_prompt)
    except Exception as e:
        logger.error(f"Primary prompt expansion failed: {e}")
        logger.info("Using fallback expansion...")
        
        # Simple fallback expansion
        fallback = (
            f"Create a simple 2D animation featuring basic geometric shapes that represent the concept of '{user_prompt}'. "
            f"Use colorful circles, squares, and triangles arranged in an visually appealing composition. "
            f"Animate the shapes with smooth movements, color transitions, and gentle scaling effects. "
            f"The animation should be engaging and clearly convey the essence of the original request through "
            f"abstract geometric visualization, concluding with all elements harmoniously arranged on screen."
        )
        
        return fallback

# Additional utility functions
def get_prompt_complexity_score(prompt: str) -> dict:
    """
    Analyze prompt complexity to help with resource allocation.
    """
    words = prompt.lower().split()
    word_count = len(words)
    
    # Count animation-related keywords
    animation_keywords = [
        'move', 'rotate', 'scale', 'transform', 'animate', 'dance', 'spin', 'bounce',
        'fade', 'appear', 'disappear', 'grow', 'shrink', 'pulse', 'vibrate'
    ]
    animation_score = sum(1 for word in words if word in animation_keywords)
    
    # Count shape keywords
    shape_keywords = [
        'circle', 'square', 'triangle', 'rectangle', 'line', 'dot', 'polygon'
    ]
    shape_score = sum(1 for word in words if word in shape_keywords)
    
    # Count color keywords
    color_keywords = [
        'red', 'blue', 'green', 'yellow', 'purple', 'orange', 'pink', 'black', 'white'
    ]
    color_score = sum(1 for word in words if word in color_keywords)
    
    # Calculate complexity
    complexity = "simple"
    if animation_score > 2 or shape_score > 3 or word_count > 50:
        complexity = "medium"
    if animation_score > 4 or shape_score > 5 or word_count > 100:
        complexity = "complex"
    
    return {
        "word_count": word_count,
        "animation_keywords": animation_score,
        "shape_keywords": shape_score,
        "color_keywords": color_score,
        "complexity": complexity,
        "estimated_render_time": {
            "simple": "30-60s",
            "medium": "60-120s", 
            "complex": "120-300s"
        }[complexity]
    }