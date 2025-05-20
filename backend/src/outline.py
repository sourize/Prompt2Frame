import re
import os
from .generator import client, SYSTEM_PROMPT

def generate_outline(prompt: str) -> list[str]:
    """
    Generate a numbered storyboard outline from the user's prompt.
    """
    outline_prompt = (
        f"You are a video storyboard generator. Given the request:\n"  # noqa: E501
        f"\"{prompt}\"\nProduce a concise, numbered outline (3-6 items)."
    )
    completion = client.chat.completions.create(
        model=os.getenv("LLM_MODEL", "llama3-70b-8192"),
        messages=[
            {"role": "system", "content": "You create outlines."},
            {"role": "user", "content": outline_prompt},
        ],
        temperature=0.2,
        max_tokens=500,
    )
    text = completion.choices[0].message.content.strip()
    scenes = []
    for line in text.splitlines():
        if match := re.match(r"^\d+\.\s*(.*)", line):
            scenes.append(match.group(1).strip())
    return scenes