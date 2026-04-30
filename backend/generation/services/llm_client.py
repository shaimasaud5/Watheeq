# generation/services/llm_client.py
# ───────────────────────────────────
# وظيفته الوحيدة: يرسل نصاً (prompt) لنموذج llama3 في Ollama
# ويرجع الرد كنص.
#
# Ollama هو السيرفر اللي يشغّل llama3 داخل Docker.
# عنوانه: http://ollama:11434

import requests

OLLAMA_URL  = "http://ollama:11434/api/generate"
MODEL_NAME  = "llama3"
TEMPERATURE = 0.2  # 0 = ثابت ودقيق، 1 = عشوائي ومبدع


def generate_text(prompt: str) -> str:
    """
    يرسل prompt لـ llama3 ويرجع الرد كنص.
    """

    # البيانات المرسلة لـ Ollama
    payload = {
        "model":   MODEL_NAME,
        "prompt":  prompt,
        "stream":  False,      # نريد الرد كاملاً دفعة واحدة
        "options": {"temperature": TEMPERATURE},
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=None)
        response.raise_for_status()
        return response.json().get("response", "").strip()

    except requests.exceptions.ConnectionError:
        raise RuntimeError("لا يمكن الاتصال بـ Ollama — تأكد إن Docker يعمل.")
    except Exception as e:
        raise RuntimeError(f"خطأ في Ollama: {e}")