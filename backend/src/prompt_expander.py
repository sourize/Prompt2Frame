"""
Prompt Expander - Converts user input to plain text technical specifications.
"""

import os
import logging
from groq import Groq

logger = logging.getLogger(__name__)

MODEL_NAME = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = (
    "You are an animation specification expert. Convert user requests into clear, "
    "detailed technical specifications for Manim animations.\n\n"
    "RULE #0 — PRESERVE NARRATIVE ORDER (HIGHEST PRIORITY)\n"
    "The Sequence steps MUST follow the EXACT order described by the user.\n"
    "- If user says 'draw a red circle and transform it into a square':\n"
    "    Step 1: Create the circle\n"
    "    Step 2: Transform circle into square\n"
    "  NEVER reverse these steps.\n"
    "- Objects listed under 'Objects:' are ONLY objects present at the very start.\n"
    "  Objects that appear later in the animation belong in the Sequence, NOT in Objects.\n"
    "- Do NOT group all creations first and all animations second.\n\n"
    "OUTPUT FORMAT:\n"
    "Animation Type: [type]\n\n"
    "Objects:\n"
    "- [ONLY objects present at scene start]\n\n"
    "Positions:\n"
    "- [Where starting objects are placed]\n\n"
    "Sequence:\n"
    "1. [First action — object name, animation type, duration]\n"
    "2. [Second action — if a new object appears here, say so]\n"
    "3. [etc — maintain the user's narrative order exactly]\n\n"
    "Total Duration: [X seconds]\n\n"
    "Technical Notes:\n"
    "- [Specific Manim techniques to use]\n\n"
    "EXAMPLE 1\n"
    "Input: 'draw a red circle and transform it into a blue square'\n"
    "Animation Type: transformation\n\n"
    "Objects:\n"
    "- Red circle with radius 1.5, centered at origin\n"
    "  (The square does NOT go here — it only appears after the transform)\n\n"
    "Positions:\n"
    "- Circle centered at origin (0, 0, 0)\n\n"
    "Sequence:\n"
    "1. Create the red circle with Create animation (1 second)\n"
    "2. Transform the circle into a blue square side 2.5 using ReplacementTransform (2 seconds)\n"
    "3. Hold final state (1 second)\n\n"
    "Total Duration: 4 seconds\n\n"
    "Technical Notes:\n"
    "- Use ReplacementTransform(circle, square)\n"
    "- Instantiate the square before calling play(), but do NOT add it to the scene separately\n"
    "- Square should be BLUE to contrast with the red circle\n\n"
    "EXAMPLE 2\n"
    "Input: 'show the word Hello, move it to the top, then fade it out'\n"
    "Animation Type: text motion\n\n"
    "Objects:\n"
    "- Text 'Hello' in yellow, font size 60, starting at center\n\n"
    "Positions:\n"
    "- Text centered at origin (0, 0, 0)\n\n"
    "Sequence:\n"
    "1. Write the text 'Hello' using Write animation (1 second)\n"
    "2. Move the text upward to (0, 2.5, 0) using animate.shift(UP * 2.5) (1 second)\n"
    "3. Fade out the text using FadeOut (1 second)\n"
    "4. Hold (0.5 seconds)\n\n"
    "Total Duration: 3.5 seconds\n\n"
    "Technical Notes:\n"
    "- Use Write() for text appearance\n"
    "- Use label.animate.shift(UP * 2.5) for smooth upward motion\n\n"
    "EXAMPLE 3\n"
    "Input: 'bouncing ball'\n"
    "Animation Type: motion along path\n\n"
    "Objects:\n"
    "- Yellow circle with radius 0.5, starting at left side of screen\n\n"
    "Positions:\n"
    "- Start at (-4, 0, 0)\n\n"
    "Sequence:\n"
    "1. Ball appears at left side with FadeIn (0.5 seconds)\n"
    "2. Ball moves along downward arc to center, first bounce (1.5 seconds)\n"
    "3. Ball bounces back up and moves to right side along second arc (1.5 seconds)\n"
    "4. Ball comes to rest at right side (0.5 seconds)\n\n"
    "Total Duration: 4 seconds\n\n"
    "Technical Notes:\n"
    "- Use MoveAlongPath with ArcBetweenPoints for parabolic trajectory\n"
    "- Arc should curve downward to simulate gravity\n\n"
    "EXAMPLE 4\n"
    "Input: 'neural network'\n"
    "Animation Type: network structure with sequential growth\n\n"
    "Objects:\n"
    "- (No objects at scene start — all layers built sequentially)\n\n"
    "Positions:\n"
    "- Layer 1 at x=-3, Layer 2 at x=0, Layer 3 at x=3\n"
    "- Three nodes per layer at y: -1.5, 0, 1.5\n\n"
    "Sequence:\n"
    "1. Create 3 blue circles (radius 0.25) at x=-3 for input layer (1 second)\n"
    "2. Draw 9 gray lines connecting input to hidden layer (1 second)\n"
    "3. Create 3 green circles (radius 0.25) at x=0 for hidden layer (1 second)\n"
    "4. Draw 9 gray lines connecting hidden to output layer (1 second)\n"
    "5. Create 3 red circles (radius 0.25) at x=3 for output layer (1 second)\n"
    "6. Hold final network (1 second)\n\n"
    "Total Duration: 6 seconds\n\n"
    "Technical Notes:\n"
    "- Use VGroup with list comprehension for each layer\n"
    "- Use nested loops for connections\n"
    "- Line stroke_width=1 for thin connection lines\n\n"
    "RULES:\n"
    "1. Always preserve the user's narrative order in the Sequence\n"
    "2. Only list in Objects: things present at scene start\n"
    "3. Always provide specific numbers (positions, sizes, durations)\n"
    "4. Be explicit about colors to ensure visibility on dark background\n"
    "5. Keep total duration under 10 seconds\n"
    "6. Ensure objects stay within visible range (x: -6 to 6, y: -3 to 3)\n"
    "7. Never reorder steps for aesthetic or technical reasons\n\n"
    "Output ONLY the plain text specification. No additional commentary."
)


def expand_prompt(user_prompt: str, max_retries: int = 3) -> str:
    """
    Expand a user's simple prompt into a detailed technical specification.

    Args:
        user_prompt: The user's simple request (e.g., "bouncing ball")
        max_retries: Maximum number of retry attempts

    Returns:
        Plain text technical specification for the animation

    Raises:
        RuntimeError: If expansion fails after all retries
    """
    if not user_prompt or not user_prompt.strip():
        raise ValueError("User prompt cannot be empty")

    user_prompt = user_prompt.strip()
    logger.info(f"Expanding prompt: {user_prompt}")

    ordering_reminder = (
        "IMPORTANT: Your Sequence steps MUST follow the EXACT order "
        "described in the request below. Do not reorder steps.\n\n"
        f"User request: {user_prompt}"
    )

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Expansion attempt {attempt}/{max_retries}")

            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": ordering_reminder},
                ],
                temperature=0.15,
                max_tokens=1200,
            )

            if not response or not response.choices:
                logger.warning(f"Attempt {attempt}: Empty response from API")
                continue

            technical_spec = response.choices[0].message.content.strip()

            if not technical_spec:
                logger.warning(f"Attempt {attempt}: Empty content in response")
                continue

            required_sections = ["Animation Type:", "Objects:", "Sequence:"]
            if all(section in technical_spec for section in required_sections):
                logger.info(
                    f"Prompt expansion successful ({len(technical_spec)} characters)"
                )
                return technical_spec
            else:
                logger.warning(
                    f"Attempt {attempt}: Missing required sections in output"
                )
                continue

        except Exception as e:
            logger.error(f"Attempt {attempt} failed: {e}")
            if attempt == max_retries:
                raise RuntimeError(
                    f"Prompt expansion failed after {max_retries} attempts: {e}"
                )
            continue

    raise RuntimeError(f"Prompt expansion failed after {max_retries} attempts")


def expand_prompt_with_fallback(user_prompt: str) -> str:
    """
    Try to expand prompt, with fallback to basic specification on failure.

    Args:
        user_prompt: The user's simple request

    Returns:
        Technical specification (either expanded or fallback)
    """
    try:
        return expand_prompt(user_prompt)
    except Exception as e:
        logger.error(f"Falling back to basic specification due to error: {e}")

        return (
            "Animation Type: basic visualization\n\n"
            "Objects:\n"
            "- Blue circle with radius 1.0, centered at origin\n\n"
            "Positions:\n"
            "- Circle centered at origin (0, 0, 0)\n\n"
            "Sequence:\n"
            "1. Create circle with Create animation (1 second)\n"
            f'2. Write text label "{user_prompt}" above the circle (1 second)\n'
            "3. Scale both objects by 1.2 (1 second)\n"
            "4. Hold (1 second)\n\n"
            "Total Duration: 4 seconds\n\n"
            "Technical Notes:\n"
            "- Basic fallback animation\n"
            f"- Original request: {user_prompt}\n"
        )
