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
    "You are an Intent-Aware Animation Architect for Manim v0.17+. Your goal: Decode user intent into a strict JSON Execution Plan.\n"
    "**Step 1: CLASSIFY INTENT.** Is the user asking to CREATE objects, TRANSFORM them, or MOVE them?\n"
    "**Step 2: GENERATE BLUEPRINT.** Output EXACTLY ONE JSON object. NO markdown, NO explanations.\n"
    "\n"
    "**STRICT JSON SCHEMA**:\n"
    "{\n"
    "  \"title\": \"<string>\",\n"
    "  \"duration_sec\": <float>,\n"
    "  \"canvas\": {\"width_units\": 14, \"height_units\": 8},\n"
    "  \"intent_graph\": {\n"
    "    \"objects\": {\n"
    "      \"<id>\": { \n"
    "        \"type\": \"circle\"|\"square\"|\"rectangle\"|\"line\"|\"arrow\"|\"text\",\n"
    "        \"start_props\": { \n"
    "          \"x\": <float>, \"y\": <float>, \n"
    "          \"color\": \"RED\"|\"BLUE\"|\"GREEN\"|\"YELLOW\"|\"ORANGE\"|\"PURPLE\"|\"PINK\"|\"WHITE\"|\"BLACK\"|\"TEAL\"|\"GOLD\",\n"
    "          \"radius\": <float|null>, \"width\": <float|null>, \"height\": <float|null>,\n"
    "          \"text_content\": \"<string|null>\", \"font_size\": <int>=24\n"
    "        },\n"
    "        \"persistent\": true\n"
    "      }\n"
    "    },\n"
    "    \"actions\": [\n"
    "      { \"action\": \"create\", \"object_id\": \"<id>\", \"duration\": <float> },\n"
    "      { \"action\": \"transform_to\", \"target_id\": \"<id>\", \"new_type\": \"<type>\", \"new_props\": { \"x\":<f>, \"y\":<f>, ... }, \"duration\": <float> },\n"
    "      { \"action\": \"move_path\", \"object_id\": \"<id>\", \"path\": [{\"x\":<f>, \"y\":<f>}, ...], \"duration\": <float> },\n"
    "      { \"action\": \"highlight\", \"object_id\": \"<id>\", \"method\": \"surrounding_rect\"|\"flash\", \"duration\": <float> },\n"
    "      { \"action\": \"wait\", \"duration\": <float> }\n"
    "    ]\n"
    "  }\n"
    "}\n"
    "\n"
    "**CRITICAL INTENT RULES (MUST FOLLOW):**\n"
    "1. **TRANSITION/MORPH/CHANGE**: Use `transform_to` on existing Object ID. NEVER create a new object for a transformation. Example: \"Circle to Square\" -> One ID, one transform action.\n"
    "2. **BOUNCE/MOVE**: Use `move_path`. Infer path points (e.g., vertical sine wave for bounce). If \"bounce\", implies a ground line exists (add it to objects).\n"
    "3. **THEN / AFTER**: Maps to sequential order in `actions` list.\n"
    "4. **COORDINATES**: Clamp x[-6.5, 6.5], y[-3.5, 3.5]. Check bounds.\n"
    "5. **TEXT**: `font_size` MUST be >= 24.\n"
    "6. **SIMPLICITY**: If user prompt is < 15 words, use minimal objects (<= 3).\n"
)

class PromptExpansionError(Exception):
    """Custom exception for prompt expansion failures."""
    pass

import json

def validate_expanded_prompt(text: str) -> None:
    """Validate the expanded prompt is valid JSON and follows schema."""
    if not text or not text.strip():
        raise PromptExpansionError("Expanded prompt is empty")
    
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise PromptExpansionError(f"Expanded prompt is not valid JSON: {e}")
        
    if "error" in data:
        raise PromptExpansionError(f"Model returned error: {data['error']}")
        
    required_keys = ["title", "duration_sec", "intent_graph"]
    for key in required_keys:
        if key not in data:
            raise PromptExpansionError(f"Missing required key in blueprint: {key}")
            
    if "objects" not in data["intent_graph"] or "actions" not in data["intent_graph"]:
        raise PromptExpansionError("intent_graph must contain 'objects' and 'actions'")

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
    user_prompt = user_prompt.strip()[:1500]  # Limit length to 1.5k chars
    
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
                    temperature=0.2,  # Strict adherence to schema
                    max_tokens=1200,
                    top_p=1.0,
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