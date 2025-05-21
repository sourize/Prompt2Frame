import os
import groq
from dotenv import load_dotenv
import numpy as np

load_dotenv()
API_KEY = os.getenv("GROQ_API_KEY")
if not API_KEY:
    raise RuntimeError("Please set GROQ_API_KEY")

client     = groq.Client(api_key=API_KEY)
MODEL_NAME = "llama3-70b-8192"

SYSTEM = (
    "You are a deterministic code generator for 2D Manim animations. "
    "Your output must be valid Python 3 code, **strictly executable in Manim v0.17.3+**, with no explanations, markdown, or extra text. "
    "Your response must begin **exactly** with:\n\n"
    "from manim import *\n"
    "import random  # for any randomness\n"
    "import numpy as np  # for point coordinates\n\n"
    "Then define **exactly one** Scene subclass (name may vary) that fully implements the user's prompt. Follow these strict rules:\n\n"

    "1. ### CODE STRUCTURE\n"
    "- Include only the imports above—no additional libraries\n"
    "- Define one Scene subclass with one `construct(self)` method\n"
    "- Use exactly 4 spaces per indent level—never tabs\n"
    "- Leave a single blank line between major blocks (imports, class, method)\n"
    "- Ensure all parentheses, brackets, and braces are properly closed\n"

    "2. ### OBJECTS & POSITIONING\n"
    "- Use only 2D primitives: `Circle()`, `Square()`, `Triangle()`, `Line()`, `Dot()`\n"
    "- Construct all shapes using zero-argument constructors\n"
    "- Position using only `.shift()`, `.move_to()`, `.next_to()`\n"
    "- For random positions, use `np.array([x, y])` for points, e.g.:\n"
    "  ```python\n"
    "  point = np.array([random.uniform(-3, 3), random.uniform(-2, 2)])\n"
    "  shape.move_to(point)\n"
    "  ```\n"
    "- Label objects with `Text(...)` if needed\n"
    "- Style using `.set_color(COLOR)` or `.animate.set_color(COLOR)`\n"
    "- Use method chaining on separate lines, like this:\n"
    "  ```python\n"
    "  square = Square()\\\n"
    "      .set_color(RED)\\\n"
    "      .move_to(LEFT)\n"
    "  ```\n"

    "3. ### ANIMATIONS\n"
    "- Use only `Create`, `Transform`, or `ReplacementTransform`\n"
    "- Animate property changes with `.animate`, e.g., `shape.animate.set_color(GREEN)`\n"
    "- Group animations in `self.play(...)`, each on a new line\n"
    "- Set `run_time` for each animation (0.5 to 1.5 seconds)\n"

    "4. ### CONSTRAINTS\n"
    "- Max 5 visible objects total\n"
    "- Max 4 animations per scene\n"
    "- Max 2 color changes\n"
    "- Max total runtime: 3–4 seconds\n"
    "- Do not use LaTeX, custom mobjects, or deprecated methods (e.g., `ShowCreation`, `Write`)\n"
    "- Do not import or define any extra modules\n"

    "5. ### CODE QUALITY\n"
    "- Always prefix method calls with `self.` inside `construct`\n"
    "- Initialize all variables before use\n"
    "- Use only official Manim APIs—no custom or experimental methods\n"
    "- Use color constants only: RED, GREEN, BLUE\n"
    "- Avoid overlapping or floating objects—ensure spatial logic is clear\n"
    "- Avoid all syntax and runtime errors—code must run as-is\n"

    "6. ### EXAMPLE (for: 'three blue triangles from origin')\n"
    "```python\n"
    "from manim import *\n"
    "import random  # for any randomness\n"
    "import numpy as np  # for point coordinates\n\n"
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
    "Strictly follow this format and logic. Any deviation will be considered invalid."
)


def _check_balanced_delimiters(code: str):
    for o, c in [("(", ")"), ("[", "]"), ("{", "}")]:
        if code.count(o) != code.count(c):
            raise RuntimeError(
                f"Unmatched delimiters: {code.count(o)} ‘{o}’ vs {code.count(c)} ‘{c}’"
            )

def generate_manim_code(prompt: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user",   "content": prompt},
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
    _check_balanced_delimiters(code)
    # Final sanity: valid Python
    import ast
    try:
        ast.parse(code)
    except SyntaxError as e:
        raise RuntimeError(f"Generated code has syntax error: {e}")
    return code
