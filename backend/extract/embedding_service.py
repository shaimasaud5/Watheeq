# use fore query embeddings not chunk
import requests

OLLAMA_EMBED_URL = "http://ollama:11434/api/embeddings"
MODEL_NAME = "nomic-embed-text"


def generate_embedding(text):
    payload = {
        "model": MODEL_NAME,
        "prompt": text,
    }

    response = requests.post(OLLAMA_EMBED_URL, json=payload, timeout=120)
    response.raise_for_status()

    data = response.json()
    return data.get("embedding", [])