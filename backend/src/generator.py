### generator.py

import os
import groq
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("Please set GROQ_API_KEY in your environment or .env file")

# Initialize Groq client with minimal configuration
client = groq.Client(
    api_key=GROQ_API_KEY
)
MODEL_NAME = "llama3-70b-8192"

SYSTEM_PROMPT = (
    "You are a code generator for Manim animations. Your task is to generate Python code that creates simple 2D animations using Manim. "
    "IMPORTANT: Your response must be ONLY the Python code, starting with 'from manim import *'. "
    "Do not include any explanations, markdown, or other text. "
    "The code must be a complete, valid Manim Scene class that can be executed directly. "
    "IMPORTANT MEMORY CONSTRAINTS: "
    "1. Keep animations simple and short (max 3-4 transformations) "
    "2. Use 2D shapes instead of 3D when possible "
    "3. Minimize the number of color changes and transformations "
    "4. Use simple shapes like Circle, Square, Triangle instead of complex ones "
    "5. Keep the total animation duration short (max 3-4 seconds) "
    "Use only up-to-date Manim classes and methods. "
    "For example, use 'Create' instead of 'ShowCreation'. "
    "Do not use deprecated classes like 'ShowCreation', 'Write', etc. "
    "Your response must be ONLY the Python code, starting with 'from manim import *'. "
    "The code must be a complete, valid Manim Scene class that can be executed directly. "
    "Use the .animate syntax for property animations. For example, to change color use 'self.play(cube.animate.set_color(BLUE))' "
    "NOT 'self.play(cube.set_color, BLUE)'. "
    "You must only use official Manim classes and methods as per the latest documentation. "
    "Do NOT invent or use any classes or functions that are not in the Manim documentation. "
    "IMPORTANT TRANSFORMATION RULES: "
    "1. Use proper Manim transformations (Transform, ReplacementTransform) instead of direct point manipulation "
    "2. When morphing shapes, use Transform or ReplacementTransform instead of set_points "
    "3. Ensure all points have consistent dimensions (2D or 3D) "
    "4. Use proper shape constructors (Circle(), Square(), etc.) for transformations "
    "Example format:\n"
    "from manim import *\n\n"
    "class SimpleAnimation(Scene):\n"
    "    def construct(self):\n"
    "        circle = Circle()\n"
    "        self.play(Create(circle))\n"
    "        self.play(circle.animate.set_color(BLUE))\n"
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