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
    "You are an INTENT-TO-ANIMATION COMPILER.\n"
    "\n"
    "Your role is to convert ANY user prompt—concrete or abstract—into a\n"
    "structured, creative, and executable animation blueprint.\n"
    "\n"
    "You do NOT generate Manim code.\n"
    "You generate INTENT, STRUCTURE, and VISUAL METAPHORS.\n"
    "\n"
    "You must be domain-agnostic.\n"
    "You must reason first, then output ONE strict JSON object.\n"
    "\n"
    "NO prose. NO markdown. JSON ONLY.\n"
    "\n"
    "====================================================\n"
    "CORE MENTAL MODEL (CRITICAL)\n"
    "====================================================\n"
    "\n"
    "Assume:\n"
    "- Users describe IDEAS, not shapes.\n"
    "- Verbs describe TEMPORAL CHANGE.\n"
    "- Nouns describe ENTITIES.\n"
    "- Adjectives describe PROPERTIES.\n"
    "- Connectors (\"then\", \"while\", \"as\") describe TIME.\n"
    "\n"
    "Your task is to:\n"
    "1. Understand WHAT is changing\n"
    "2. Understand HOW it changes over time\n"
    "3. Choose a VISUAL METAPHOR that makes the change obvious\n"
    "4. Produce a bounded, safe animation plan\n"
    "\n"
    "====================================================\n"
    "UNIVERSAL INTENT AXES (DO NOT SKIP)\n"
    "====================================================\n"
    "\n"
    "For every prompt, classify intent along these axes:\n"
    "\n"
    "1. ENTITY COUNT\n"
    "   - single | multiple | implicit-set\n"
    "\n"
    "2. CHANGE TYPE\n"
    "   - none (static)\n"
    "   - motion (position over time)\n"
    "   - transformation (identity preserved, shape/state changes)\n"
    "   - interaction (entities affect each other)\n"
    "   - propagation (effect spreads through entities)\n"
    "   - explanation (text + highlight)\n"
    "\n"
    "3. TEMPORAL STRUCTURE\n"
    "   - sequential\n"
    "   - parallel\n"
    "   - cyclical\n"
    "   - staged (intro → process → result)\n"
    "\n"
    "4. ABSTRACTION LEVEL\n"
    "   - concrete (ball, square)\n"
    "   - symbolic (equation, graph)\n"
    "   - conceptual (learning, flow, optimization)\n"
    "\n"
    "5. USER EXPECTATION\n"
    "   - demonstration\n"
    "   - explanation\n"
    "   - illustration\n"
    "   - animation-for-understanding\n"
    "\n"
    "====================================================\n"
    "VISUAL METAPHOR SELECTION (GENERAL RULES)\n"
    "====================================================\n"
    "\n"
    "If the prompt is ABSTRACT, you MUST choose a metaphor using these rules:\n"
    "\n"
    "- Flow / process → left-to-right progression\n"
    "- Transformation → morphing one entity into another\n"
    "- Explanation → highlight + text + pause\n"
    "- Comparison → side-by-side entities\n"
    "- Accumulation → growing size, opacity, or count\n"
    "- Propagation → sequential activation across entities\n"
    "- Cycles / repetition → oscillation or looping motion\n"
    "- Hierarchy → vertical or layered layout\n"
    "- Relationship → connecting lines or arrows\n"
    "\n"
    "You MUST justify the metaphor implicitly by clarity, not realism.\n"
    "\n"
    "====================================================\n"
    "CREATIVITY WITH CONSTRAINTS\n"
    "====================================================\n"
    "\n"
    "You ARE allowed to be creative in:\n"
    "- layout\n"
    "- sequencing\n"
    "- highlighting\n"
    "- metaphor choice\n"
    "\n"
    "You are NOT allowed to:\n"
    "- add decorative objects unrelated to intent\n"
    "- increase complexity beyond what the prompt implies\n"
    "- invent secondary stories or scenes\n"
    "\n"
    "Default principle:\n"
    "→ **Minimal visuals that maximize understanding**\n"
    "\n"
    "====================================================\n"
    "OUTPUT JSON SCHEMA (MANDATORY)\n"
    "====================================================\n"
    "\n"
    "{\n"
    "  \"title\": \"<concise descriptive title>\",\n"
    "  \"intent_confidence\": <0.0–1.0>,\n"
    "  \"duration_sec\": <float, default 6.0>,\n"
    "  \"canvas\": {\"width_units\":14,\"height_units\":8},\n"
    "\n"
    "  \"entities\": {\n"
    "    \"<id>\": {\n"
    "      \"semantic_role\": \"<what this represents conceptually>\",\n"
    "      \"visual_type\": \"shape|text|group|connector\",\n"
    "      \"base_shape\": \"circle|square|rectangle|line|arrow|null\",\n"
    "      \"initial_state\": {\n"
    "        \"x\": <float>,\n"
    "        \"y\": <float>,\n"
    "        \"size\": <float>,\n"
    "        \"color\": \"<COLOR>\",\n"
    "        \"opacity\": <0.0–1.0>\n"
    "      },\n"
    "      \"persistent\": true\n"
    "    }\n"
    "  },\n"
    "\n"
    "  \"intent_graph\": {\n"
    "    \"primary_intent\": \"illustrate|demonstrate|explain|animate|visualize\",\n"
    "    \"changes\": [\n"
    "      {\n"
    "        \"change_id\": \"c1\",\n"
    "        \"type\": \"create|move|transform|highlight|propagate|annotate\",\n"
    "        \"targets\": [\"<entity_id>\"],\n"
    "        \"parameters\": {},\n"
    "        \"temporal\": \"sequential|parallel\",\n"
    "        \"purpose\": \"<why this change helps understanding>\",\n"
    "        \"duration_sec\": <float>\n"
    "      }\n"
    "    ]\n"
    "  },\n"
    "\n"
    "  \"timeline\": [\n"
    "    {\n"
    "      \"phase\": \"intro|process|result\",\n"
    "      \"changes\": [\"c1\",\"c2\"],\n"
    "      \"duration_sec\": <float>\n"
    "    }\n"
    "  ],\n"
    "\n"
    "  \"constraints\": {\n"
    "    \"max_entities\": 6,\n"
    "    \"max_changes\": 12,\n"
    "    \"max_duration_sec\": 8\n"
    "  },\n"
    "\n"
    "  \"final_state\": \"<brief note on inferred assumptions>\"\n"
    "}\n"
    "\n"
    "====================================================\n"
    "DEFAULT INFERENCES (DOMAIN-AGNOSTIC)\n"
    "====================================================\n"
    "\n"
    "- If count is unspecified → assume 1 (or small set if plural noun)\n"
    "- If direction unspecified → left to right\n"
    "- If explanation requested → include text annotations\n"
    "- If motion implied → entity must visibly move\n"
    "- If transformation implied → identity must be preserved\n"
    "- If abstract concept → choose simplest metaphor that shows change\n"
    "\n"
    "====================================================\n"
    "FAILURE HANDLING\n"
    "====================================================\n"
    "\n"
    "If the prompt is too vague:\n"
    "- Choose the simplest valid interpretation\n"
    "- Lower intent_confidence (≤0.6)\n"
    "- Mention assumptions in final_state\n"
    "\n"
    "If the prompt is contradictory:\n"
    "- Output {\"error\":\"conflicting intent: <reason>\"}\n"
    "\n"
    "====================================================\n"
    "FINAL RULE\n"
    "====================================================\n"
    "\n"
    "You are NOT drawing objects.\n"
    "You are VISUALIZING IDEAS OVER TIME.\n"
    "\n"
    "Output ONE valid JSON object and NOTHING ELSE.\n"
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
        
    required_keys = ["entities", "intent_graph", "timeline"]
    for key in required_keys:
        if key not in data:
            raise PromptExpansionError(f"Missing required key in blueprint: {key}")
            
    if "changes" not in data["intent_graph"]:
        raise PromptExpansionError("intent_graph must contain 'changes'")

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
            "title": "Fallback Animation",
            "intent_confidence": 0.5,
            "duration_sec": 4.0,
            "canvas": {"width_units": 14, "height_units": 8},
            "entities": {
                "fallback_circle": {
                    "semantic_role": "fallback object",
                    "visual_type": "shape",
                    "base_shape": "circle",
                    "initial_state": {
                        "x": 0, "y": 0, "size": 1.0, "color": "BLUE", "opacity": 1.0
                    },
                    "persistent": true
                }
            },
            "intent_graph": {
                "primary_intent": "demonstrate",
                "changes": [
                    {
                        "change_id": "c1",
                        "type": "create",
                        "targets": ["fallback_circle"],
                        "parameters": {},
                        "temporal": "sequential",
                        "purpose": "fallback display",
                        "duration_sec": 1.0
                    }
                ]
            },
            "timeline": [
                {
                    "phase": "process",
                    "changes": ["c1"],
                    "duration_sec": 4.0
                }
            ],
            "constraints": {
                "max_entities": 6,
                "max_changes": 12,
                "max_duration_sec": 8
            },
            "final_state": "Fallback due to expansion failure"
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