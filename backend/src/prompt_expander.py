import os
import groq
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GROQ_API_KEY")
if not API_KEY:
    raise RuntimeError("Please set GROQ_API_KEY in your environment")

client = groq.Client(api_key=API_KEY)
MODEL_NAME = "llama3-70b-8192"

SYSTEM = """
You are a helpful assistant that takes a very short, often-technical request 
and turns it into one coherent, richly detailed paragraph, suitable as 
input to a deterministic code generator.  Do NOT output bullet points or outlines—just one paragraph.
"""

def expand_prompt(user_prompt: str) -> str:
    messages = [
        {"role": "system",  "content": SYSTEM},
        {"role": "user",    "content": user_prompt.strip()},
    ]
    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=0.2,
        max_tokens=300,
    )
    text = resp.choices[0].message.content.strip()
    # Quick sanity check: at least 20 words?
    if len(text.split()) < 15:
        raise RuntimeError("Expanded prompt was unexpectedly short")
    return text
