# outline.py
import re
from .generator import client, SYSTEM_PROMPT  # reuse your Groq client

OUTLINE_PROMPT = """
You are a video storyboard generator. Given the user's request:
"{user_prompt}"

Produce a concise, numbered outline (3–6 items), each describing one scene in plain English.
Your output must be exactly:

1. First scene description…
2. Second scene description…
…
"""

def generate_outline(user_prompt: str) -> list[str]:
    prompt = OUTLINE_PROMPT.format(user_prompt=user_prompt.strip())
    completion = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role":"system","content":"You create outlines."},
                  {"role":"user", "content":prompt}],
        temperature=0.2,
        max_tokens=500,
    )
    text = completion.choices[0].message.content.strip()
    # parse lines "1. …", "2. …"
    scenes = []
    for line in text.splitlines():
        if line.strip() and re.match(r"^\d+\.", line):
            scenes.append(line.split(".",1)[1].strip())
    return scenes
