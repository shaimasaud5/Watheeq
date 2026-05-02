# generation/services/llm_client.py

import os
from groq import Groq

# ── Ollama (محلي) ──────────────────────────────────────────────
# import requests
# OLLAMA_URL  = "http://ollama:11434/api/generate"
# MODEL_NAME  = "llama3"
# TEMPERATURE = 0.2
#
# def generate_text(prompt: str) -> str:
#     payload = {
#         "model":   MODEL_NAME,
#         "prompt":  prompt,
#         "stream":  False,
#         "options": {"temperature": TEMPERATURE},
#     }
#     try:
#         response = requests.post(OLLAMA_URL, json=payload, timeout=None)
#         response.raise_for_status()
#         return response.json().get("response", "").strip()
#     except requests.exceptions.ConnectionError:
#         raise RuntimeError("لا يمكن الاتصال بـ Ollama — تأكد إن Docker يعمل.")
#     except Exception as e:
#         raise RuntimeError(f"خطأ في Ollama: {e}")
# ───────────────────────────────────────────────────────────────

# ── Groq API ───────────────────────────────────────────────────
MODEL_NAME  = "llama-3.3-70b-versatile"
TEMPERATURE = 0.2

def generate_text(prompt: str) -> str:
    """يرسل prompt لـ Groq ويرجع الرد كنص."""
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
# ───────────────────────────────────────────────────────────────