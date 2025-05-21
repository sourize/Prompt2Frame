import os
import groq
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GROQ_API_KEY")
if not API_KEY:
    raise RuntimeError("Please set GROQ_API_KEY in your environment")

client = groq.Client(api_key=API_KEY)
MODEL_NAME = "llama3-70b-8192"

SYSTEM = (
    "You are a precise and helpful assistant that transforms short or technical user requests "
    "into a single, well-structured, richly detailed paragraph. "
    "This paragraph must serve as clear and complete input for a deterministic code generator. "
    "Do not use bullet points, lists, or outlines—only one coherent paragraph is allowed. "
    "Your output should expand on the user’s intent with specific visual, spatial, or logical details where appropriate, "
    "ensuring the resulting paragraph is self-contained and unambiguous."
)


def expand_prompt(user_prompt: str) -> str:
    messages = [
        {"role": "system",  "content": SYSTEM},
        {"role": "user",    "content": user_prompt.strip()},
    ]
    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=0.2,
        max_tokens=300,
    )
    text = resp.choices[0].message.content.strip()
    # Quick sanity check: at least 20 words?
    if len(text.split()) < 15:
        raise RuntimeError("Expanded prompt was unexpectedly short")
    return text
