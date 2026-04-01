"""
Prompt Expander - Enriches user prompts with spatial/timing context.

Role in the new pipeline:
  User prompt → [Expander adds detail] → Generator produces Manim code

The expander no longer tries to structure output or route to templates.
It simply returns a richer version of the user's request that the generator
can use to make better, more detailed animations.
"""

import os
import logging
from groq import Groq

logger = logging.getLogger(__name__)

MODEL_NAME = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

EXPANDER_SYSTEM_PROMPT = (
    "You are an animation director. Your job is to take a user's animation request "
    "and expand it into a richer description that preserves EXACTLY what the user "
    "asked for, but adds helpful detail about colors, sizes, positions, and timing.\n\n"
    "CRITICAL RULES:\n"
    "1. NEVER change the order of steps the user described\n"
    "2. NEVER add steps the user did not ask for\n"
    "3. NEVER remove steps the user asked for\n"
    "4. Keep the output as plain English — not code, not JSON, not bullet points\n"
    "5. Keep it concise — 3 to 8 sentences maximum\n"
    "6. If the user prompt is already detailed, return it almost unchanged\n"
    "7. ALWAYS mention that objects should be centered or positioned to be visible\n\n"
    "CAMERA FRAMING RULES (MUST FOLLOW):\n"
    "- All objects should be positioned to be visible on screen\n"
    "- Center small objects at ORIGIN (x=0, y=0)\n"
    "- For wide layouts (neural networks, multiple shapes), mention zoom out\n"
    "- Single objects should always be centered\n"
    "- Multiple objects spread across screen need camera framing\n\n"
    "POSITIONING GUIDANCE:\n"
    "- Small objects (radius < 1): center at ORIGIN\n"
    "- Medium objects (1-2 units): center at ORIGIN, good size\n"
    "- Large objects or groups: fit camera to show all\n"
    "- Connected components: fit all in frame, center on middle\n\n"
    "EXAMPLES:\n\n"
    "Input: 'draw a red circle and transform it into a square'\n"
    "Output: Draw a red circle with radius 1.5 at the CENTER of the screen (origin). "
    "Then transform it into a blue square with side length 2.5 using a smooth morph animation. "
    "The circle appears first and becomes the square. The camera stays centered on the object throughout.\n\n"
    "Input: 'bouncing ball'\n"
    "Output: Animate a yellow filled circle (radius 0.4) starting at the left side of the screen. "
    "Move it along a downward parabolic arc to the center (first bounce), "
    "then along another arc to the right side (second bounce). "
    "The camera should be centered on the screen to capture the full bounce path.\n\n"
    "Input: 'show a sine wave'\n"
    "Output: Draw a coordinate axes system centered on screen. "
    "Then plot the curve y = sin(x) in blue over the range x = -4 to 4. "
    "The camera should be centered to show the entire graph. The axes appear first, then the curve is drawn.\n\n"
    "Input: 'neural network with 3 layers'\n"
    "Output: Create a 3-layer neural network visualization. "
    "IMPORTANT: Position layers within a visible area (x from -3 to 3) so the entire network fits on screen. "
    "Layer 1 (input, 3 blue nodes) at x=-2, then gray connection lines draw to layer 2 positions, "
    "then layer 2 (hidden, 3 green nodes) at x=0 appears, then connections to layer 3, "
    "then layer 3 (output, 3 red nodes) at x=2. The camera should zoom out or set width to fit all layers. "
    "Each layer and its connections animate sequentially.\n\n"
    "Input: 'draw a triangle and rotate it'\n"
    "Output: Draw a yellow triangle centered on the screen. "
    "Then rotate it smoothly 360 degrees. "
    "The camera stays centered on the triangle throughout the rotation.\n\n"
    "Input: 'show a heart shape that pulses'\n"
    "Output: Draw a red heart shape centered on screen using parametric equations. "
    "The heart should be a good size (not too small). "
    "Then animate it pulsing (scaling up and down). "
    "The camera stays centered on the heart throughout.\n\n"
    "Now expand the following request. Return ONLY the expanded description, nothing else."
)


def expand_prompt(user_prompt: str, max_retries: int = 2) -> str:
    """
    Expand a user's animation request into a richer description.

    Returns the expanded prompt on success, or the original prompt on failure
    so the generator always has something useful to work with.
    """
    if not user_prompt or not user_prompt.strip():
        raise ValueError("User prompt cannot be empty")

    user_prompt = user_prompt.strip()

    # Very short prompts (< 15 chars) benefit most from expansion
    # Detailed prompts (> 200 chars) can go straight through
    if len(user_prompt) > 200:
        logger.info("Prompt already detailed, skipping expansion")
        return user_prompt

    logger.info(f"Expanding prompt: {user_prompt[:80]}")

    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": EXPANDER_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Request: {user_prompt}"},
                ],
                temperature=0.15,
                max_tokens=300,  # Short — just a few sentences of context
            )

            if not response or not response.choices:
                logger.warning(f"Expander attempt {attempt}: empty response")
                continue

            expanded = response.choices[0].message.content.strip()
            if expanded and len(expanded) > len(user_prompt):
                logger.info(f"Expansion successful ({len(expanded)} chars)")
                return expanded

        except Exception as e:
            logger.error(f"Expander attempt {attempt} failed: {str(e)[:100]}")

    logger.warning("Expansion failed, returning original prompt")
    return user_prompt


def expand_prompt_with_fallback(user_prompt: str) -> str:
    """
    Entry point called by app.py.
    Always returns something useful — falls back to original prompt on error.
    """
    try:
        return expand_prompt(user_prompt)
    except Exception as e:
        logger.error(f"expand_prompt_with_fallback error: {e}")
        return user_prompt
