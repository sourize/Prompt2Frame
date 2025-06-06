# Enhanced prompt_expander.py
import os
import groq
from dotenv import load_dotenv
import asyncio
from typing import Optional
import logging

logger = logging.getLogger(__name__)

load_dotenv()
API_KEY = os.getenv("GROQ_API_KEY")
if not API_KEY:
    raise RuntimeError("Please set GROQ_API_KEY in your environment")

client = groq.Client(api_key=API_KEY)
MODEL_NAME = "gemma2-9b-it"

# Enhanced system prompt for better prompt expansion
SYSTEM = (
    "You are a precise and creative assistant that transforms short user requests "
    "into detailed, vivid, and actionable descriptions for 2D animation generation. "
    
    "Your task is to expand the user's prompt into exactly ONE comprehensive paragraph "
    "that provides rich visual details, spatial relationships, timing, and creative elements "
    "while staying true to the user's original intent. "
    
    "Guidelines for expansion:\n"
    "- Transform abstract concepts into concrete visual elements\n"
    "- Specify colors, shapes, movements, and spatial arrangements\n"
    "- Include timing and sequencing details for animations\n"
    "- Add creative flourishes that enhance the visual appeal\n"
    "- Ensure the description is clear and unambiguous\n"
    "- Keep mathematical concepts geometrically accurate\n"
    "- Suggest appropriate transitions and visual effects\n"
    
    "Output format:\n"
    "- Write exactly ONE detailed paragraph (no bullet points or lists)\n"
    "- Aim for 80-150 words for optimal detail without overwhelming\n"
    "- Use vivid, descriptive language that inspires compelling visuals\n"
    "- End with a clear conclusion or final visual state\n"
    
    "Example transformation:\n"
    "Input: 'dancing circles'\n"
    "Output: 'Create a mesmerizing scene where three vibrant circles of different sizes—a large blue circle, a medium red circle, and a small green circle—perform an elegant choreographed dance across the screen. Begin with all circles positioned at the center, then have them gracefully separate and move in synchronized circular patterns around each other, with the larger circles moving slower and the smaller one orbiting quickly. The circles should pulse gently with changing opacity as they dance, occasionally coming together in harmonious formations before spiraling outward again. The animation concludes with all three circles returning to the center and fading into a single golden circle that glows softly before disappearing.'"
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
            
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=0.3 + (attempt * 0.1),  # Slightly increase creativity on retries
                max_tokens=400,
                top_p=0.9,
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