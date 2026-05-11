# extract/retrieval_service.py
# ─────────────────────────────
# Computes similarity between the section embedding and all stored chunk embeddings 
# then retrieves the top_k most similar chunks.

import math


def cosine_similarity(vec1: list, vec2: list) -> float:
    """
    Compute cosine similarity between two vectors.

    Returns a value between:
    0 -> no similarity
    1 -> identical vectors
    """
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0

    dot   = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot / (norm1 * norm2)


def retrieve_top_chunks(section_embedding: list, chunks: list, top_k: int = 3) -> list:
    """
    Compare the section embedding with all chunk embeddings generated during the Processing stage.
    Returns the top_k most similar chunks as a list of texts.

    chunks: list of dictionaries in the format:
            {"semantic_english_text": str, "embedding": list}
    """
    scored = []
    for chunk in chunks:
        score = cosine_similarity(section_embedding, chunk["embedding"])
        scored.append((score, chunk["semantic_english_text"]))

    # Sort chunks from highest similarity to lowest
    scored.sort(key=lambda x: x[0], reverse=True)

    return [text for _, text in scored[:top_k]]
