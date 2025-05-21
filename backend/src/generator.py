# generator.py
import groq, os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GROQ_API_KEY")
if not API_KEY: raise RuntimeError("Set GROQ_API_KEY")

client = groq.Client(api_key=API_KEY)
MODEL = "llama3-70b-8192"

SYSTEM = """
You are a Manim 2D animation code generator. Your input is a single
descriptive paragraph.  Output **only** valid Python code (no markdown,
no commentary) that begins with:

    from manim import *
    import random  # For any random operations

You may define **multiple** `class Xxx(Scene):` blocks if needed to stage
parts of the animation (e.g. one class draws nodes, another draws edges,
another shows subtitles).  Follow these rules strictly:

• Use only zero-arg constructors (Circle(), Square(), etc.)  
• Style with `.set_color(...)` or `.animate.set_color(...)`  
• Position with `.move_to()`, `.shift()`, `.next_to()`  
• Animate via `self.play(...)`, max 4 animations, total run_time ≤ 4s  
• Camera moves OK via `self.camera.frame.animate.move_to(...)` only  
• Include subtitles via `self.add(Text("...", font_size=24).to_edge(DOWN))`  
• Close all parentheses/brackets, use 4-space indents, single blank lines  
"""

def generate_manim_code(prompt_paragraph: str, temp=0.25, max_tokens=1500) -> str:
    messages = [
        {"role":"system", "content": SYSTEM},
        {"role":"user",   "content": prompt_paragraph},
    ]
    resp = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=temp,
        max_tokens=max_tokens,
    )
    code = resp.choices[0].message.content.strip()
    if not code.startswith("from manim"):
        raise RuntimeError("LLM did not emit Python code starting with 'from manim'")
    return code
