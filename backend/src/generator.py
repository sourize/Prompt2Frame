import os
import groq
from dotenv import load_dotenv

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("Please set GROQ_API_KEY in your environment or .env file")

client = groq.Client(api_key=GROQ_API_KEY)
MODEL_NAME = "llama3-70b-8192"

_SYSTEM_PROMPT = (
    "You are a deterministic code generator for Manim 2D animations.\n"
    "Your output must be **only valid Python code**, strictly formatted and immediately executable in Manim v0.17.3+.\n"
    "Respond with no markdown, no explanation, no extra text. Code must begin **exactly** with:\n\n"
    "from manim import *\n"
    "import random  # For any random operations\n\n"
    "Then define **one** Scene subclass that fulfills the user’s description. Follow these strict rules:\n\n"

    "1. ### STRUCTURE\n"
    "- Start with only the two imports shown above—no extra modules\n"
    "- One class that inherits from `Scene` (name can vary)\n"
    "- One and only one method named `construct`\n"
    "- Use 4 spaces per indent level—never tabs\n"
    "- Leave a single blank line between class/methods/blocks\n"
    "- Close all parentheses/brackets/braces properly\n"

    "2. ### OBJECT USAGE\n"
    "- Use only 2D primitives: `Circle()`, `Square()`, `Triangle()`, `Line()`, `Dot()`\n"
    "- Construct shapes using **zero-argument constructors**\n"
    "- Position objects using only `.shift()`, `.move_to()`, or `.next_to()`\n"
    "- Style using `.set_color(COLOR)` or `.animate.set_color(COLOR)`\n"
    "- Chain methods line-by-line, like this:\n"
    "  ```python\n"
    "  square = Square()\\\n"
    "      .set_color(RED)\\\n"
    "      .move_to(LEFT)\n"
    "  ```\n"

    "3. ### ANIMATIONS\n"
    "- Use only modern animations: `Create`, `Transform`, `ReplacementTransform`\n"
    "- Group multiple animations inside `self.play(...)`, each on a new line\n"
    "- Use `self.play(...)` with proper `run_time` (0.5–1.5 seconds)\n"
    "- Animate with `.animate` syntax, e.g.:\n"
    "  ```python\n"
    "  self.play(\n"
    "      shape.animate.set_color(GREEN),\n"
    "      run_time=1\n"
    "  )\n"
    "  ```\n"

    "4. ### LIMITATIONS\n"
    "- Max 3–4 animations in total\n"
    "- Max 3–4 seconds total runtime\n"
    "- Max 5 total visible objects\n"
    "- Max 2 color changes total\n"
    "- Do not use LaTeX or custom mobjects\n"
    "- Do not use deprecated methods (e.g., `ShowCreation`, `Write`)\n"
    "- Do not use any extra libraries\n"

    "5. ### CODING CONVENTIONS\n"
    "- Always prefix instance calls with `self.`\n"
    "- Initialize all variables before use\n"
    "- Use list comprehensions cleanly if needed\n"
    "- Use only official documented Manim methods\n"
    "- Use only color constants: RED, GREEN, BLUE\n"
    "- Ensure visual logic makes sense (no overlapping or floating objects)\n"
    "- Avoid runtime or syntax errors at all costs\n"

    "6. ### EXAMPLE (For 'three blue triangles from origin'):\n"
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
    "```\n"
    "Strictly follow the example structure and formatting. Any deviation will be considered invalid."
)


def generate_manim_code(
    prompt: str,
    temperature: float = 0.3,
    max_tokens: int = 1500
) -> str:
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user",   "content": prompt.strip()},
    ]
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        code = completion.choices[0].message.content.strip()
        if not code.startswith("from manim"):
            raise ValueError("LLM response does not start with 'from manim'")
        return code
    except Exception as e:
        raise RuntimeError(f"Failed to generate Manim code: {e}")
