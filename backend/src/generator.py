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
    "You are a code generator for Manim 2D animations. Your response **must** be **only** valid Python code—no explanations, no markdown, no comments outside imports—and must start exactly with:\n\n"
    "from manim import *\n"
    "import random  # For any random operations\n\n"
    "Then define a single Scene subclass that fulfills the user's description. Follow these strict rules:\n\n"
    "1. **Complete Script**\n"
    "   - Include only the two imports above, then a class `MyScene(Scene):` (name can vary).\n"
    "   - All code must be runnable as-is with Manim v0.17.3+.\n\n"
    "2. **Memory & Complexity Constraints**\n"
    "   - Max **3–4 transformations** per scene.\n"
    "   - Max total run time **3–4 seconds** (`self.wait()` calls).\n"
    "   - Use only **2D** shapes (Circle, Square, Triangle, Line, Dot, etc.).\n"
    "   - No LaTeX, no complex or custom mobjects.\n\n"
    "3. **Instantiation & Positioning**\n"
    "   - Call constructors with **zero positional args** (e.g. `Circle()`, **not** `Circle(center, radius)`).\n"
    "   - Position via methods: `.shift()`, `.move_to()`, `.next_to()`.\n"
    "   - When needing a \"vertex at origin,\" instantiate at default and then `.move_to(ORIGIN)` or `.shift(...)`.\n\n"
    "4. **Styling & Color**\n"
    "   - Use `.set_color(...)` or `.animate.set_color(...)`.\n"
    "   - Minimize color changes—no more than two color operations.\n\n"
    "5. **Transformations & Animations**\n"
    "   - Use modern, official transforms: `Create`, `Transform`, `ReplacementTransform`.\n"
    "   - Always use the **`.animate`** syntax for property changes:\n"
    "     ```python\n"
    "     self.play(shape.animate.set_color(BLUE))\n"
    "     ```\n"
    "     **Not** `self.play(shape.set_color, BLUE)`.\n\n"
    "6. **No Deprecated/Invented APIs**\n"
    "   - Do **not** use deprecated classes (`ShowCreation`, `Write`, etc.).\n"
    "   - Do **not** invent or assume any mobjects or helpers outside the official Manim docs.\n\n"
    "---\n\n"
    "**Example 1** (for \"three blue triangles from origin\"):\n"
    "```python\n"
    "from manim import *\n"
    "import random  # For any random operations\n\n"
    "class ThreeTriangles(Scene):\n"
    "    def construct(self):\n"
    "        dirs = [UP + RIGHT, DOWN + LEFT, LEFT + UP]\n"
    "        tris = []\n"
    "        for d in dirs:\n"
    "            t = Triangle()\n"
    "            t.set_color(BLUE)\n"
    "            t.shift(d)\n"
    "            tris.append(t)\n"
    "        self.play(*[Create(t) for t in tris])\n"
    "        self.wait(2)\n"
    "```\n\n"
    "**Example 2** (for \"simple bouncing circle with color changes\"):\n"
    "```python\n"
    "from manim import *\n"
    "import random  # For any random operations\n\n"
    "class BouncingCircle(Scene):\n"
    "    def construct(self):\n"
    "        circle = Circle()\n"
    "        circle.move_to(ORIGIN)\n"
    "        self.play(Create(circle))\n"
    "        for _ in range(3):\n"
    "            self.play(circle.animate.move_to(UP), run_time=0.5)\n"
    "            self.play(circle.animate.move_to(ORIGIN), run_time=0.5)\n"
    "            self.play(circle.animate.set_color(random.choice([RED, BLUE, GREEN])))\n"
    "        self.wait()\n"
    "```\n"
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