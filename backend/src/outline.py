import re
import groq
from .generator import client

MODEL_NAME = "llama3-70b-8192"
_OUTLINE_SYSTEM = (
    "You are a concise storyboard outline assistant. "
    "Your only goal is to turn the user’s prompt into a clear, numbered sequence of 3–6 scene descriptions. "
    "Output only the outline, nothing else."
)
_OUTLINE_PROMPT = """
Given the user request:
\"{user_prompt}\"

Produce exactly 3–6 numbered scenes. Follow these rules:
1. Prefix each line with number and a dot (e.g., “1. …”).
2. One or two sentences per scene.
3. Reflect the core intent faithfully.
Respond with exactly the numbered list.
"""

def generate_outline(
    user_prompt: str,
    temperature: float = 0.2,
    max_tokens: int = 300
) -> list[str]:
    messages = [
        {"role": "system", "content": _OUTLINE_SYSTEM},
        {"role": "user",   "content": _OUTLINE_PROMPT.format(user_prompt=user_prompt.strip())},
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
