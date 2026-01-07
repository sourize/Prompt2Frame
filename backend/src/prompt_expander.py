"""
Simplified Prompt Expander - Converts user input to plain text technical specifications.

This module takes vague user prompts and expands them into detailed technical
descriptions that the generator can use to create Manim code.

Output format is plain text with clear sections for objects, positions, motion, etc.
No complex JSON schemas - just natural language that's easy to parse and debug.
"""

import os
import logging
from typing import Optional
from groq import Groq

logger = logging.getLogger(__name__)

# Initialize Groq client
MODEL_NAME = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Simplified system prompt for plain text output
SYSTEM_PROMPT = """You are an animation specification expert. Convert user requests into clear, detailed technical specifications for Manim animations.

OUTPUT FORMAT (Plain Text):
```
Animation Type: [transformation/motion/growth/rotation/network/etc]

Objects:
- [Description of each object with size, color, shape]

Positions:
- [Where each object should be placed]

Motion/Changes:
- [What should move, transform, or change]

Sequence:
1. [First action with duration]
2. [Second action with duration]
3. [etc]

Total Duration: [X seconds]

Technical Notes:
- [Any specific Manim techniques to use]
```

EXAMPLES:

Input: "circle to square"
Output:
```
Animation Type: transformation

Objects:
- Blue circle with radius 1.0
- Red square with side length 2.0

Positions:
- Both objects centered at origin (0, 0, 0)

Motion/Changes:
- Circle morphs into square using ReplacementTransform

Sequence:
1. Create circle with Create animation (1 second)
2. Transform circle to square with ReplacementTransform (2 seconds)
3. Hold final state (1 second)

Total Duration: 4 seconds

Technical Notes:
- Use ReplacementTransform for smooth morphing
- Objects should be clearly visible and centered
```

Input: "bouncing ball"
Output:
```
Animation Type: motion along path

Objects:
- Yellow circle with radius 0.5 (representing a ball)

Positions:
- Start at LEFT side of screen (-4, 0, 0)
- End at RIGHT side of screen (4, 0, 0)

Motion/Changes:
- Ball moves along downward arc path (parabolic trajectory)
- Simulates bouncing motion with 2-3 bounces

Sequence:
1. Ball appears at left (0.5 seconds)
2. Ball moves along arc path with bouncing motion (3 seconds)
3. Ball comes to rest at right (0.5 seconds)

Total Duration: 4 seconds

Technical Notes:
- Use MoveAlongPath with parabolic arc
- Arc should curve downward to simulate gravity
- Smooth continuous motion
```

Input: "simple pendulum"
Output:
```
Animation Type: rotation about pivot

Objects:
- Pivot point: small black dot at (0, 2, 0)
- Rod: thin line from pivot to bob
- Bob: blue circle with radius 0.3 at end of rod

Positions:
- Pivot at top center (0, 2, 0)
- Rod extends downward 2 units
- Bob at bottom of rod (0, 0, 0) initially

Motion/Changes:
- Entire pendulum (rod + bob) rotates about pivot point
- Swings left and right with decreasing amplitude

Sequence:
1. Create pivot, rod, and bob (1 second)
2. Swing right 30 degrees (1 second)
3. Swing left 60 degrees (1.5 seconds)
4. Swing right 30 degrees (1 second)
5. Come to rest at center (0.5 seconds)

Total Duration: 5 seconds

Technical Notes:
- Use Rotate animation with about_point=pivot
- Group rod and bob together with VGroup
- All components must be visible (not black on black)
- Use BLUE or YELLOW for bob color
```

Input: "neural network"
Output:
```
Animation Type: network structure with sequential growth

Objects:
Layer 1 (Input): 3 blue circles, radius 0.25
- Position at x=-3, y positions: [-1.5, 0, 1.5]

Layer 2 (Hidden): 3 green circles, radius 0.25
- Position at x=0, y positions: [-1.5, 0, 1.5]

Layer 3 (Output): 3 red circles, radius 0.25
- Position at x=3, y positions: [-1.5, 0, 1.5]

Connections: Gray lines connecting all neurons between adjacent layers
- 9 lines from layer 1 to layer 2 (all-to-all)
- 9 lines from layer 2 to layer 3 (all-to-all)

Positions:
- Spread horizontally across screen
- Evenly spaced vertically within each layer

Motion/Changes:
- Sequential appearance layer by layer
- Grow from left to right showing network building

Sequence:
1. Create layer 1 neurons simultaneously (1 second)
2. Draw all connections from layer 1 to layer 2 (1 second)
3. Create layer 2 neurons simultaneously (1 second)
4. Draw all connections from layer 2 to layer 3 (1 second)
5. Create layer 3 neurons simultaneously (1 second)
6. Hold final network (1 second)

Total Duration: 6 seconds

Technical Notes:
- Use VGroup with list comprehension for neuron layers
- Use nested loops for connections: for n1 in layer1 for n2 in layer2
- Line thickness: stroke_width=1
- Create animations should be parallel within each layer
```

RULES:
1. Always provide specific numbers (positions, sizes, durations)
2. Be explicit about colors to ensure visibility
3. Describe spatial layout clearly
4. Break complex animations into clear sequences
5. Suggest appropriate Manim techniques
6. For unfamiliar concepts, map to basic geometric patterns
7. Keep total duration under 10 seconds
8. Ensure objects are positioned within visible range (x: -6 to 6, y: -3 to 3)

Output ONLY the plain text specification. No additional commentary.
"""


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
    
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Expansion attempt {attempt}/{max_retries}")
            
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"User request: {user_prompt}"}
                ],
                temperature=0.3,  # Lower for more consistent output
                max_tokens=1000,
            )
            
            if not response or not response.choices:
                logger.warning(f"Attempt {attempt}: Empty response from API")
                continue
            
            technical_spec = response.choices[0].message.content.strip()
            
            if not technical_spec:
                logger.warning(f"Attempt {attempt}: Empty content in response")
                continue
            
            # Basic validation - check if key sections are present
            required_sections = ["Animation Type:", "Objects:", "Sequence:"]
            if all(section in technical_spec for section in required_sections):
                logger.info(f"Prompt expansion successful ({len(technical_spec)} characters)")
                return technical_spec
            else:
                logger.warning(f"Attempt {attempt}: Missing required sections in output")
                continue
                
        except Exception as e:
            logger.error(f"Attempt {attempt} failed: {e}")
            if attempt == max_retries:
                raise RuntimeError(f"Prompt expansion failed after {max_retries} attempts: {e}")
            continue
    
    # If we get here, all retries failed
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
        
        # Fallback: Create a basic specification
        return f"""Animation Type: basic visualization

Objects:
- Blue circle with radius 1.0
- Text label: "{user_prompt}"

Positions:
- Circle centered at origin (0, 0, 0)
- Text above circle

Motion/Changes:
- Circle appears with Create animation
- Text writes in with Write animation
- Both grow slightly with scale animation

Sequence:
1. Create circle (1 second)
2. Write text (1 second)
3. Scale both objects by 1.2 (1 second)
4. Hold (1 second)

Total Duration: 4 seconds

Technical Notes:
- Basic fallback animation
- Original request: {user_prompt}
"""