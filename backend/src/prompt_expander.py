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
    "5. Keep it concise — 3 to 6 sentences maximum\n"
    "6. If the user prompt is already detailed, return it almost unchanged\n\n"
    "EXAMPLES:\n\n"
    "Input: 'draw a red circle and transform it into a square'\n"
    "Output: Draw a red circle with radius 1.5 at the center of the screen. "
    "Then transform it into a blue square with side length 2.5 using a smooth morph animation. "
    "The circle appears first and becomes the square — not the other way around.\n\n"
    "Input: 'bouncing ball'\n"
    "Output: Animate a yellow filled circle (radius 0.4) starting at the left edge of the screen. "
    "Move it along a downward parabolic arc to the center (first bounce), "
    "then along another arc to the right edge (second bounce). "
    "The motion should feel gravity-driven and smooth.\n\n"
    "Input: 'show a sine wave'\n"
    "Output: Draw a coordinate axes system. "
    "Then plot the curve y = sin(x) in blue over the range x = -4 to 4. "
    "Label the curve. The axes appear first, then the curve is drawn.\n\n"
    "Input: 'neural network with 3 layers'\n"
    "Output: Create a 3-layer neural network visualization. "
    "Layer 1 (input, 3 blue nodes) appears at x=-3, then gray connection lines draw to layer 2 positions, "
    "then layer 2 (hidden, 3 green nodes) at x=0 appears, then connections to layer 3, "
    "then layer 3 (output, 3 red nodes) at x=3. Each layer and its connections animate sequentially.\n\n"
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
