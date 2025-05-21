# generator.py
import os
import groq
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GROQ_API_KEY") or RuntimeError("Set GROQ_API_KEY")
client = groq.Client(api_key=API_KEY)
MODEL_NAME = "llama3-70b-8192"

SYSTEM = """
You are a deterministic Manim code generator.  Output **only** valid Python code (no markdown).
Start with:
    from manim import *
    import random  # for any randomness
Then define 1–5 classes inheriting from Scene, each with a construct() method, to fulfill exactly the user’s paragraph description.
Follow these rules:
 • Use only 2D primitives (Circle, Square, Dot, Line, Triangle).
 • Position with .shift(), .move_to(), .next_to().
 • Style with .set_color(...) or .animate.set_color(...).
 • Animate with Create, Transform, ReplacementTransform in self.play().
 • Total runtime ≤ 4s per class.
 • No extra imports or LaTeX.
 • Close all parentheses/brackets.
"""

def generate_manim_code(paragraph: str,
                        temperature: float = 0.3,
                        max_tokens: int = 1500) -> str:
    messages = [
        {"role": "system",  "content": SYSTEM},
        {"role": "user",    "content": paragraph.strip()},
    ]
    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    code = resp.choices[0].message.content.strip()
    if not code.startswith("from manim"):
        raise RuntimeError("Response did not start with 'from manim'")
    return code
