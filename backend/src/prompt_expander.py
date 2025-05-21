# prompt_expander.py
import groq
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GROQ_API_KEY")
if not API_KEY:
    raise RuntimeError("Please set GROQ_API_KEY in your environment")

client = groq.Client(api_key=API_KEY)
MODEL = "llama3-70b-8192"

SYSTEM = (
    "You are a single-paragraph prompt generator for Manim animations. "
    "Given a user request, produce one self-contained descriptive paragraph that "
    "the next model can turn directly into Python/Manim code. "
    "- If the request is very simple (draw a circle), keep the paragraph concise. "
    "- If it’s complex (explain a neural network), include what to label, "
    "camera movements, subtitles, color choices, and staging details. "
    "Do not output lists or bullet points—only one coherent paragraph."
)

def expand_prompt(user_prompt: str, temperature: float = 0.3, max_tokens: int = 300) -> str:
    msg = [
        {"role":"system", "content": SYSTEM},
        {"role":"user",   "content": user_prompt.strip()},
    ]
    resp = client.chat.completions.create(
        model=MODEL,
        messages=msg,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    para = resp.choices[0].message.content.strip()
    if "\n" in para or len(para.split()) < 5:
        raise RuntimeError("Prompt expander must return a single paragraph")
    return para
