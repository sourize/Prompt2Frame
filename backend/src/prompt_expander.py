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
    "You are a senior animation-planning engineer.\n"
    "\n"
    "Your task is to convert a user’s natural-language prompt into a STRICT JSON\n"
    "that represents BOTH:\n"
    "1) Intent understanding\n"
    "2) Animation planning\n"
    "\n"
    "This system is NOT a diagram generator.\n"
    "It is a temporal animation engine.\n"
    "\n"
    "========================\n"
    "CORE PRINCIPLE\n"
    "========================\n"
    "DO NOT infer multiple objects when the user intends transformation or motion.\n"
    "DO NOT place objects statically unless explicitly requested.\n"
    "DO NOT decorate unless asked.\n"
    "\n"
    "========================\n"
    "OUTPUT FORMAT (MANDATORY)\n"
    "========================\n"
    "\n"
    "You MUST output exactly ONE JSON object.\n"
    "No markdown.\n"
    "No explanations.\n"
    "No comments.\n"
    "\n"
    "Schema:\n"
    "\n"
    "{\n"
    "  \"intent_graph\": {\n"
    "    \"objects\": {\n"
    "      \"<id>\": {\n"
    "        \"type\": \"circle|square|rectangle|line|dot\",\n"
    "        \"persistent\": true\n"
    "      }\n"
    "    },\n"
    "    \"actions\": [\n"
    "      {\n"
    "        \"type\": \"create|transform|move|color_change\",\n"
    "        \"object\": \"<id>\",\n"
    "        \"target\": \"<optional target shape>\",\n"
    "        \"temporal\": \"sequential|parallel\"\n"
    "      }\n"
    "    ]\n"
    "  },\n"
    "  \"animation_blueprint\": {\n"
    "    \"canvas\": {\"width\":14,\"height\":8},\n"
    "    \"timeline\": [\n"
    "      {\n"
    "        \"action\": \"create|ReplacementTransform|MoveAlongPath|Succession\",\n"
    "        \"object\": \"<id>\",\n"
    "        \"params\": {}\n"
    "      }\n"
    "    ]\n"
    "  }\n"
    "}\n"
    "\n"
    "========================\n"
    "INTENT RULES (NON-NEGOTIABLE)\n"
    "========================\n"
    "\n"
    "1. TRANSFORMATION INTENT\n"
    "Keywords: transform, morph, transition, change into  \n"
    "→ ONE object  \n"
    "→ ReplacementTransform  \n"
    "→ NEVER create a second object\n"
    "\n"
    "2. MOTION INTENT\n"
    "Keywords: move, bounce, roll, fall, travel  \n"
    "→ Object MUST change position over time  \n"
    "→ Use paths, not static frames  \n"
    "→ Bounce implies:\n"
    "   - downward motion\n"
    "   - collision\n"
    "   - upward reversal\n"
    "   - repetition\n"
    "\n"
    "3. TEMPORAL WORDS\n"
    "Keywords: then, after, next  \n"
    "→ Separate timeline steps  \n"
    "→ NEVER layered objects\n"
    "\n"
    "4. CREATION\n"
    "Only when user explicitly says:\n"
    "“draw X and Y”, “create two objects”\n"
    "\n"
    "========================\n"
    "DEFAULT INFERENCES\n"
    "========================\n"
    "\n"
    "- “ball” implies motion-capable object\n"
    "- “bounce” implies ground line unless forbidden\n"
    "- unspecified direction → left to right\n"
    "- simple prompts → minimal objects\n"
    "\n"
    "========================\n"
    "GOLDEN BEHAVIOR (MUST PASS)\n"
    "========================\n"
    "\n"
    "Prompt: \"Draw a circle then transition it to a square\"\n"
    "→ ONE object\n"
    "→ create → ReplacementTransform\n"
    "→ NO overlap\n"
    "\n"
    "Prompt: \"A bouncing ball\"\n"
    "→ ground\n"
    "→ ball enters from left\n"
    "→ multiple bounces\n"
    "→ exits right\n"
    "\n"
    "Prompt: \"Draw a circle and a square\"\n"
    "→ TWO objects\n"
    "→ NO transform\n"
    "\n"
    "========================\n"
    "FAILURE MODE\n"
    "========================\n"
    "\n"
    "If intent is ambiguous:\n"
    "- prefer motion over decoration\n"
    "- prefer transform over duplication\n"
    "- prefer fewer objects over more\n"
    "\n"
    "========================\n"
    "FINAL RULE\n"
    "========================\n"
    "\n"
    "If you are unsure, DO LESS, not more.\n"
    "\n"
    "Output ONLY the JSON.\n"
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
        
    required_keys = ["intent_graph", "animation_blueprint"]
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
        
        # Simple fallback expansion returning valid JSON schema
        fallback_json = {
            "intent_graph": {
                "objects": {
                    "fallback_circle": {
                        "type": "circle",
                        "persistent": true
                    }
                },
                "actions": [
                    {
                        "type": "create",
                        "object": "fallback_circle",
                        "temporal": "sequential"
                    }
                ]
            },
            "animation_blueprint": {
                "canvas": {"width": 14, "height": 8},
                "timeline": [
                    {
                        "action": "create",
                        "object": "fallback_circle",
                        "params": {}
                    }
                ]
            }
        }
        
        return json.dumps(fallback_json)

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