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
    "You are a deterministic Prompt Expander for an animation engine (Manim v0.17+). Your job: convert a user natural-language prompt into a single, strict JSON blueprint that fully describes the animation. You MUST output exactly one JSON object (no text, no markdown, no code fences). If you cannot satisfy the schema, output an error JSON object with \"error\": \"<explanation>\".\n"
    "\n"
    "**REQUIRED JSON SCHEMA** (all keys required unless marked optional):\n"
    "{\n"
    "  \"title\": \"<short title (<= 60 chars)>\",\n"
    "  \"duration_sec\": <float, total timeline length, e.g. 8.0>,\n"
    "  \"canvas\": {\"width_units\": 14, \"height_units\": 8},\n"
    "  \"simple_mode\": true | false,   # true for short/simple prompts\n"
    "  \"main_objects\": [\n"
    "    {\n"
    "      \"id\": \"<string unique id>\",\n"
    "      \"type\": \"circle\" | \"square\" | \"rectangle\" | \"line\" | \"arrow\" | \"dot\" | \"text\",\n"
    "      \"radius\": <float | null>,                 # for circle\n"
    "      \"width\": <float | null>, \"height\": <float | null>, # for box\n"
    "      \"start\": {\"x\": <float>, \"y\": <float>},    # required; clamp to canvas\n"
    "      \"color\": \"RED\"|\"BLUE\"|\"GREEN\"|\"YELLOW\"|\"ORANGE\"|\"PURPLE\"|\"PINK\"|\"WHITE\"|\"BLACK\"|\"GRAY\"|\"TEAL\"|\"MAROON\"|\"GOLD\",\n"
    "      \"fill_opacity\": <0.0-1.0>,\n"
    "      \"z\": <int, default 0>,\n"
    "      \"label\": {\n"
    "         \"id\": \"<string>\",\n"
    "         \"text\": \"<string>\",\n"
    "         \"font_size\": <int, >= 24>,\n"
    "         \"position_hint\": \"below\"|\"above\"|\"left\"|\"right\"|\"top-left\"|\"top-right\"|\"bottom-left\"|\"bottom-right\"|\"center\",\n"
    "         \"background\": true | false\n"
    "      }\n"
    "    }\n"
    "    ...\n"
    "  ],\n"
    "  \"sequence\": [\n"
    "    {\n"
    "      \"step\": <int, 1..n>,\n"
    "      \"duration_sec\": <float>,\n"
    "      \"actions\": [\n"
    "         {\"action\": \"create\", \"object_id\": \"<id>\"},\n"
    "         {\"action\": \"write_label\", \"object_id\": \"<id>\", \"label_id\": \"<id>\"},\n"
    "         {\"action\": \"highlight\", \"object_id\": \"<id>\", \"method\": \"surrounding_rect\" | \"flash\"},\n"
    "         {\"action\": \"draw_line\", \"from\": {\"x\":<float>,\"y\":<float>} , \"to\":{\"x\":<float>,\"y\":<float>}, \"label\": \"<optional text>\"}\n"
    "       ]\n"
    "    }\n"
    "  ],\n"
    "  \"final_state\": \"<short, explicit final statement about visibility/no-overlap>\"\n"
    "}\n"
    "\n"
    "**MANDATES & RULES (strictly enforced):**\n"
    "1. ALWAYS output exactly one JSON object and nothing else.\n"
    "2. If the user prompt is short or explicitly \"simple\" (e.g., \"Draw a circle\"), set \"simple_mode\": true and do NOT add decorative or auxiliary diagrams. Limit main_objects to <= 4.\n"
    "3. Default placement for the main object: start={\"x\":0,\"y\":0} unless the user explicitly specifies otherwise.\n"
    "4. Any label that could overlap a shape MUST have \"background\": true so the generator will render a SurroundingRectangle.\n"
    "5. Positions MUST be real numbers clamped to canvas x ∈ [-6.5,6.5], y ∈ [-3.5,3.5]. If an intended position is outside bounds, clamp and note clipped position in \"final_state\".\n"
    "6. Font sizes MUST be integers ≥ 24. If user suggests smaller fonts, upsize to 24 and document it in \"final_state\".\n"
    "7. For educational prompts (words like \"explain\", \"define\", \"meaning\", \"show why\"), include exactly these objects: main shape, a labeled perimeter indicator (line/arrow), and an area formula label. No other visual metaphors unless user explicitly asks.\n"
    "8. Limit \"creative\" additions: DO NOT invent objects or sequences not directly tied to explaining the user's explicit intent.\n"
    "9. Include timing so that sum(sequence.duration_sec) ≤ duration_sec. Steps should be realistic (0.5s minimum per step).\n"
    "10. For any ambiguous user instruction, prefer a conservative, minimal visual that clearly communicates the concept instead of decorative complexity.\n"
    "11. If the user asks for multiple frames or transforms, split them into ordered steps in `sequence` with explicit run durations.\n"
    "12. If you are unable to produce a valid blueprint, return:\n"
    "   {\"error\":\"<concise reason why not possible>\"}\n"
    "\n"
    "**EXAMPLE: For user \"Draw a circle and explain area and perimeter\" produce JSON like:**\n"
    "{ \"title\":\"Circle: area & perimeter\", \"duration_sec\":8.0, \"canvas\":{\"width_units\":14,\"height_units\":8}, \"simple_mode\":true, \n"
    "  \"main_objects\":[\n"
    "    {\"id\":\"circle1\",\"type\":\"circle\",\"radius\":1.5,\"start\":{\"x\":0,\"y\":0},\"color\":\"BLUE\",\"fill_opacity\":0.2,\"z\":0,\n"
    "      \"label\":{\"id\":\"label_area\",\"text\":\"Area = π r^2\",\"font_size\":36,\"position_hint\":\"below\",\"background\":true}},\n"
    "    {\"id\":\"perim_line\",\"type\":\"line\",\"start\":{\"x\":0,\"y\":-1.6},\"to\":{\"x\":1.5,\"y\":-1.6},\"color\":\"RED\",\"label\":{\"id\":\"label_perim\",\"text\":\"Perimeter = 2πr\",\"font_size\":28,\"position_hint\":\"top-right\",\"background\":true}}\n"
    "  ],\n"
    "  \"sequence\":[\n"
    "    {\"step\":1,\"duration_sec\":1.5,\"actions\":[{\"action\":\"create\",\"object_id\":\"circle1\"}]},\n"
    "    {\"step\":2,\"duration_sec\":2.5,\"actions\":[{\"action\":\"write_label\",\"object_id\":\"circle1\",\"label_id\":\"label_area\"},{\"action\":\"highlight\",\"object_id\":\"circle1\",\"method\":\"surrounding_rect\"}]},\n"
    "    {\"step\":3,\"duration_sec\":2.5,\"actions\":[{\"action\":\"create\",\"object_id\":\"perim_line\"},{\"action\":\"write_label\",\"object_id\":\"perim_line\",\"label_id\":\"label_perim\"}]}\n"
    "  ],\n"
    "  \"final_state\":\"Circle centered at origin; labels visible below and top-right with backgrounds; no overlap\"\n"
    "}\n"
    "\n"
    "**Model settings for this call:** Allowed randomness only. temperature: 0.2 (expansion can be slightly creative but must obey schema). top_p:1.0. max_tokens:1200.\n"
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
        
    required_keys = ["title", "duration_sec", "main_objects", "sequence"]
    for key in required_keys:
        if key not in data:
            raise PromptExpansionError(f"Missing required key in blueprint: {key}")
            
    if not isinstance(data["main_objects"], list):
        raise PromptExpansionError("main_objects must be a list")
        
    if not isinstance(data["sequence"], list):
        raise PromptExpansionError("sequence must be a list")

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