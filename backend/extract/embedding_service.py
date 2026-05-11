# extract/embedding_service.py
# ─────────────────────────────
# Generate embeddings for input text using Ollama.
# Uses the same embedding model from Processing stage
# to ensure embedding consistency across the pipeline.
import requests

OLLAMA_EMBED_URL = "http://ollama:11434/api/embeddings"
MODEL_NAME       = "mxbai-embed-large"    # Same model used in Processing


def generate_embedding(text: str) -> list:
    """
    Generate embedding vector for a given text.

    Used during Extraction stage to generate embeddings
    for section names or queries, then compare them with
    chunk embeddings generated earlier in Processing. 
    """
    payload = {
        "model":  MODEL_NAME,
        "prompt": text,
    }
    response = requests.post(OLLAMA_EMBED_URL, json=payload, timeout=None)
    response.raise_for_status()
    return response.json().get("embedding", [])
