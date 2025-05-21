# outline.py
import re
import groq
from .generator import client

MODEL_NAME = "llama3-70b-8192"

SYSTEM = (
    "You are an assistant that, given a user’s animation request, "
    "returns 1–6 descriptive paragraphs explaining **exactly** what scenes or components "
    "should be animated.  For simple requests (e.g. “draw a circle”) output one short paragraph.  "
    "For complex/explanatory requests (e.g. “explain neural network”), output multiple paragraphs, "
    "each describing a logical sub-animation.  **Do not** output bullet lists—only plain paragraphs."
)

PROMPT = """
User request:
\"{user_prompt}\"

Produce 1 to 6 numbered paragraphs.  Each paragraph should be 1–3 sentences, "
explaining what to animate in that “scene” and how (colors, motions, relationships).
Format strictly as:

1. First paragraph…
2. Second paragraph…
…

No extra text.
"""

def generate_outline(user_prompt: str,
                     temperature: float = 0.2,
                     max_tokens: int = 400) -> list[str]:
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user",   "content": PROMPT.format(user_prompt=user_prompt.strip())},
    ]
    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    text = resp.choices[0].message.content.strip()
    paras = []
    for line in text.splitlines():
        m = re.match(r"^\s*\d+\.\s*(.+)", line)
        if m:
            paras.append(m.group(1).strip())
    if not paras:
        raise RuntimeError("Outline parser found no paragraphs")
    return paras
