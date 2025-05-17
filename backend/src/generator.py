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
    "   - All code must be runnable as-is with Manim v0.17.3+.\n"
    "   - **MUST** use 4 spaces for indentation (no tabs).\n"
    "   - **MUST** close all brackets, parentheses, and braces.\n"
    "   - **MUST** have proper line breaks between methods and classes.\n\n"
    "2. **Code Structure Requirements**\n"
    "   - **MUST** follow this exact structure:\n"
    "     ```python\n"
    "     from manim import *\n"
    "     import random  # For any random operations\n\n"
    "     class MyScene(Scene):\n"
    "         def construct(self):\n"
    "             # Your code here, indented with 4 spaces\n"
    "             pass\n"
    "     ```\n"
    "   - **MUST** have exactly one class definition.\n"
    "   - **MUST** have exactly one `construct` method.\n"
    "   - **MUST** use `self.` prefix for all method calls.\n\n"
    "3. **Memory & Complexity Constraints**\n"
    "   - Max **3–4 transformations** per scene.\n"
    "   - Max total run time **3–4 seconds** (`self.wait()` calls).\n"
    "   - Use only **2D** shapes (Circle, Square, Triangle, Line, Dot, etc.).\n"
    "   - No LaTeX, no complex or custom mobjects.\n"
    "   - Max **5** total objects in the scene.\n\n"
    "4. **Instantiation & Positioning**\n"
    "   - Call constructors with **zero positional args** (e.g. `Circle()`, **not** `Circle(center, radius)`).\n"
    "   - Position via methods: `.shift()`, `.move_to()`, `.next_to()`.\n"
    "   - When needing a \"vertex at origin,\" instantiate at default and then `.move_to(ORIGIN)` or `.shift(...)`.\n"
    "   - **MUST** use proper method chaining with line breaks:\n"
    "     ```python\n"
    "     circle = Circle()\\\n"
    "         .set_color(BLUE)\\\n"
    "         .move_to(ORIGIN)\n"
    "     ```\n\n"
    "5. **Styling & Color**\n"
    "   - Use `.set_color(...)` or `.animate.set_color(...)`.\n"
    "   - Minimize color changes—no more than two color operations.\n"
    "   - **MUST** use proper color constants (RED, BLUE, GREEN, etc.).\n\n"
    "6. **Transformations & Animations**\n"
    "   - Use modern, official transforms: `Create`, `Transform`, `ReplacementTransform`.\n"
    "   - Always use the **`.animate`** syntax for property changes:\n"
    "     ```python\n"
    "     self.play(shape.animate.set_color(BLUE))\n"
    "     ```\n"
    "     **Not** `self.play(shape.set_color, BLUE)`.\n"
    "   - **MUST** use proper animation grouping:\n"
    "     ```python\n"
    "     self.play(\n"
    "         Create(circle),\n"
    "         run_time=0.5\n"
    "     )\n"
    "     ```\n\n"
    "7. **No Deprecated/Invented APIs**\n"
    "   - Do **not** use deprecated classes (`ShowCreation`, `Write`, etc.).\n"
    "   - Do **not** invent or assume any mobjects or helpers outside the official Manim docs.\n"
    "   - **MUST** use only documented Manim methods and properties.\n\n"
    "8. **Error Prevention**\n"
    "   - **MUST** initialize all variables before use.\n"
    "   - **MUST** use proper list/dict comprehensions.\n"
    "   - **MUST** handle all object references.\n"
    "   - **MUST** use proper string literals (single or double quotes).\n\n"
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
    "            t = Triangle()\\\n"
    "                .set_color(BLUE)\\\n"
    "                .shift(d)\n"
    "            tris.append(t)\n"
    "        self.play(\n"
    "            *[Create(t) for t in tris],\n"
    "            run_time=1.5\n"
    "        )\n"
    "        self.wait(2)\n"
    "```\n\n"
    "**Example 2** (for \"simple bouncing circle with color changes\"):\n"
    "```python\n"
    "from manim import *\n"
    "import random  # For any random operations\n\n"
    "class BouncingCircle(Scene):\n"
    "    def construct(self):\n"
    "        circle = Circle()\\\n"
    "            .set_color(BLUE)\\\n"
    "            .move_to(ORIGIN)\n"
    "        \n"
    "        self.play(Create(circle))\n"
    "        \n"
    "        for _ in range(3):\n"
    "            self.play(\n"
    "                circle.animate.move_to(UP),\n"
    "                run_time=0.5\n"
    "            )\n"
    "            self.play(\n"
    "                circle.animate.move_to(ORIGIN),\n"
    "                run_time=0.5\n"
    "            )\n"
    "            self.play(\n"
    "                circle.animate.set_color(\n"
    "                    random.choice([RED, BLUE, GREEN])\n"
    "                )\n"
    "            )\n"
    "        \n"
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