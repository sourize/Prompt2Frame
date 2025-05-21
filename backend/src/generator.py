import os
import groq
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GROQ_API_KEY")
if not API_KEY:
    raise RuntimeError("Please set GROQ_API_KEY")

client     = groq.Client(api_key=API_KEY)
MODEL_NAME = "llama3-70b-8192"

SYSTEM = """
You are a deterministic Manim code generator.  Produce *only* valid Python 3 code, 
starting with:

from manim import *
import random  # for any randomness

Then define as many Scene subclasses as needed to fulfill the prompt. 
Use only Create, Transform, ReplacementTransform for animations, 
label objects via Text(...), position with .move_to/.shift/.next_to, 
and keep total runtime under 6 seconds.

Respond with no markdown or extra text.
"""

def generate_manim_code(prompt: str) -> str:
    messages = [
        {"role":"system", "content":SYSTEM},
        {"role":"user",   "content":prompt},
    ]
    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=0.3,
        max_tokens=1500,
    )
    code = resp.choices[0].message.content.strip()
    if not code.startswith("from manim"):
        raise RuntimeError("Generated code did not start with `from manim`")
    return code
