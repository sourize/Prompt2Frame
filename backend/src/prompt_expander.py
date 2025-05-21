from dotenv import load_dotenv
import os, re
import groq

load_dotenv()
API_KEY = os.getenv("GROQ_API_KEY")
if not API_KEY:
    raise RuntimeError("Please set GROQ_API_KEY")

client = groq.Client(api_key=API_KEY)
MODEL_NAME = "llama3-70b-8192"

SYSTEM = (
    "You are a prompt expansion assistant.  "
    "Your job is to turn a short instruction into a single, richly descriptive paragraph "
    "that fully specifies how to animate that idea in Manim, "
    "including which objects to use, how they should move, any labels or colors, and timing."
)

def expand_prompt(user_prompt: str) -> str:
    messages = [
        {"role":"system", "content":SYSTEM},
        {"role":"user",   "content":user_prompt},
    ]
    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=0.2,
        max_tokens=300,
    )
    return resp.choices[0].message.content.strip()
