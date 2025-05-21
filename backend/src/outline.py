import re
import groq
from .generator import client

MODEL_NAME = "llama3-70b-8192"
OUTLINE_SYSTEM = (
    "You are a concise storyboard outline assistant. "
    "Your only goal is to turn the user’s prompt into a clear, numbered sequence of 3–6 scene descriptions. "
    "Do not add any extra text or commentary—output only the outline."
)

OUTLINE_PROMPT = """
Given the user request:
\"{user_prompt}\"

Produce a numbered outline of 3–6 scenes. Follow these rules exactly:
1. Use between 3 and 6 items.
2. Prefix each line with its number and a period (e.g., “1. …”).
3. Keep each scene description to one or two sentences.
4. Reflect the core elements and intent of the user’s request faithfully.
Respond with exactly:
1. First scene description…
2. Second scene description…
3. Third scene description…
…up to 6.
"""


def generate_outline(
    user_prompt: str,
    temperature: float = 0.2,
    max_tokens: int = 300
) -> list[str]:
    """Generate a 3–6 step storyboard outline from the user’s prompt."""
    messages = [
        {"role": "system", "content": OUTLINE_SYSTEM},
        {"role": "user",
         "content": OUTLINE_PROMPT.format(user_prompt=user_prompt.strip())},
    ]
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        text = completion.choices[0].message.content.strip()
        scenes = []
        for line in text.splitlines():
            m = re.match(r"^\s*\d+\.\s*(.+)", line)
            if m:
                scenes.append(m.group(1).strip())
        if not scenes:
            raise ValueError("No outline items parsed from LLM response")
        return scenes
    except Exception as e:
        raise RuntimeError(f"Failed to generate outline: {e}")
