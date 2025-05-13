### generator.py

import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("Please set GROQ_API_KEY in your environment or .env file")

client = Groq(api_key=GROQ_API_KEY)
MODEL_NAME = "llama3-8b-8192"

SYSTEM_PROMPT = (
    "You are a code generator for Manim animations. Your task is to generate Python code that creates 2D animations using Manim. "
    "IMPORTANT: Your response must be ONLY the Python code, starting with 'from manim import *'. "
    "Do not include any explanations, markdown, or other text. "
    "The code must be a complete, valid Manim Scene class that can be executed directly. "
    "You are a code generator for Manim animations. "
    "Your task is to generate Python code for Manim version 0.17 or later. "
    "Use only up-to-date Manim classes and methods. "
    "For example, use 'Create' instead of 'ShowCreation'. "
    "Do not use deprecated classes like 'ShowCreation', 'Write', etc. "
    "Your response must be ONLY the Python code, starting with 'from manim import *'. "
    "The code must be a complete, valid Manim Scene class that can be executed directly."
    "Use the .animate syntax for property animations. For example, to change color use 'self.play(cube.animate.set_color(BLUE))' "
    "NOT 'self.play(cube.set_color, BLUE)'. "
    "You must only use official Manim classes and methods as per the latest documentation. "
    "Do NOT invent or use any classes or functions that are not in the Manim documentation. "
    "For example, to animate an arrow, use:\n"
    "    arrow = Arrow(start, end)\n"
    "    self.play(Create(arrow))\n"
    "Do NOT use DrawArrow, ShowCreation, or any other deprecated or non-existent functions. "
    "If you want to animate the appearance of any object, always use 'Create' or other official Manim animations. "
    "If you want to add text, use 'Text' or 'Tex' as appropriate, and ensure LaTeX is available if using 'Tex'. "
    "If you want to move objects, use the .animate syntax, e.g., 'self.play(mob.animate.move_to(NEW_POSITION))'. "
    "Example format:\n"
    "from manim import *\n\n"
    "class SimpleAnimation(Scene):\n"
    "    def construct(self):\n"
    "        circle = Circle()\n"
    "        self.play(Create(circle))\n"
    "        self.play(circle.animate.set_color(BLUE))\n"
    "        arrow = Arrow(LEFT, RIGHT)\n"
    "        self.play(Create(arrow))\n"
    "        self.wait()\n"
)

def generate_manim_code(prompt: str) -> str:
    """
    Call the LLM to generate a Manim scene code snippet based on the user's prompt.
    Returns the raw Python code string.
    """
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1500
        )
        
        code = completion.choices[0].message.content.strip()
        print("Generated code:", code)
        
        if not (code.startswith("from manim") or code.startswith("import")):
            raise ValueError(f"Generated code does not look like a Manim Python script. Got: {code[:100]}...")
        return code
        
    except Exception as e:
        print(f"Error generating code: {str(e)}")
        raise