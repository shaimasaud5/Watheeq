# generation/services/llm_client.py

import os
from groq import Groq

# ── Groq API ───
MODEL_NAME  = "llama-3.3-70b-versatile"
TEMPERATURE = 0.2

def generate_text(prompt: str) -> str:
    """Sends a prompt to Groq and returns the response as plain text."""
    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY_TASK4"))
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=TEMPERATURE,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        raise RuntimeError(f"خطأ في Groq: {e}")
