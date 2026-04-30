# extract/embedding_service.py
# ─────────────────────────────
# يولّد embedding لنص معين.
# يستخدم نفس النموذج الذي استخدمته مهمة 2 (mxbai-embed-large)
# لأن embeddings من نماذج مختلفة لا يمكن مقارنتها.

import requests

OLLAMA_EMBED_URL = "http://ollama:11434/api/embeddings"
MODEL_NAME       = "mxbai-embed-large"  # نفس مهمة 2


def generate_embedding(text: str) -> list:
    """
    يولّد embedding لنص معين.
    يُستخدم لتوليد embedding لاسم الفقرة (section_name)
    عشان نقارنه بـ chunk embeddings المحفوظة من مهمة 2.
    """
    payload = {
        "model":  MODEL_NAME,
        "prompt": text,
    }
    response = requests.post(OLLAMA_EMBED_URL, json=payload, timeout=None)
    response.raise_for_status()
    return response.json().get("embedding", [])
