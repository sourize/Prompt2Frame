# ===== prompt_expander.py =====
import os
import groq
import time
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)

load_dotenv()
API_KEY = os.getenv("GROQ_API_KEY")
if not API_KEY:
    raise RuntimeError("Please set GROQ_API_KEY in your environment")

client = groq.Client(api_key=API_KEY)
MODEL_NAME = "qwen-qwq-32b"

SYSTEM = (
    "You are an expert 2D animation prompt enhancer. "
    "Transform any user prompt into one richly detailed, vividly descriptive paragraph optimized for Manim code generation. "
    "Incorporate specific shapes, colors, camera movements, screen transitions, timings (in seconds), easing functions, and clear visual cues. "
    "Use natural language—no bullet points or lists—so that the resulting prompt has at least 40 words and no more than 150 words, all in one cohesive paragraph."
)

class PromptExpansionError(Exception):
    pass

def validate_expanded_prompt(text: str) -> None:
    if not text.strip():
        raise PromptExpansionError("Expanded prompt is empty")
    wc = len(text.split())
    if wc < 20 or wc > 200:
        raise PromptExpansionError(f"Expanded prompt length invalid ({wc} words)")
    if text.count("\n\n") > 0:
        raise PromptExpansionError("Should be a single paragraph")

def expand_prompt(user_prompt: str, max_retries: int = 3) -> str:
    if not user_prompt.strip():
        raise PromptExpansionError("Input prompt cannot be empty")
    prompt = user_prompt.strip()[:500]
    for i in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
                temperature=0.3 + i*0.1,
                max_tokens=400,
                top_p=0.9,
            )
            expanded = resp.choices[0].message.content.strip()
            validate_expanded_prompt(expanded)
            return expanded
        except Exception as e:
            logger.warning(f"Expansion attempt {i+1} failed: {e}")
            if i == max_retries - 1:
                raise PromptExpansionError(f"Failed after {max_retries}: {e}")
            time.sleep(1)
    raise PromptExpansionError("Unexpected expansion error")

def expand_prompt_with_fallback(user_prompt: str) -> str:
    try:
        return expand_prompt(user_prompt)
    except Exception:
        logger.error("Using fallback expansion")
        return (
            f"Create a simple 2D animation with shapes representing '{user_prompt}', animating with smooth movements, color transitions, and concluding harmoniously."
        )
